"""
Build ONE Tally Prime XML that contains the ledger masters first and
the voucher after them, so a single import does everything.

Rules this file follows:
  * SVCURRENTCOMPANY is the CLIENT's Tally company, not the CA firm.
  * Debit entry  -> ISDEEMEDPOSITIVE Yes, amount NEGATIVE.
  * Credit entry -> ISDEEMEDPOSITIVE No,  amount POSITIVE.
  * All entries must add up to zero, otherwise Tally rejects it.
  * Sales / Credit Note use the BUYER as party; Purchase / Debit Note
    use the SELLER as party.
  * Tally Prime EDU only accepts voucher dates on the 1st, 2nd or last
    day of a month. EDU mode (ON by default) moves the voucher date to
    the 1st of the bill's month. Set TALLY_EDU_MODE=0 in .env for a
    licensed Tally so the real bill date is used.
"""

import os
import re
from datetime import datetime
from xml.sax.saxutils import escape

from extensions import db


# Raised when the bill data is not good enough to make a valid voucher.
# The route should catch this and show the message to the CA.
class XmlBuildError(ValueError):
    pass


GSTIN_FORMAT = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")

# bill_type -> (Tally voucher type, party is debited?, main ledger key,
#               tax ledger set, party group key, which party)
KINDS = {
    "purchase":        ("Purchase",    False, "purchase", "in",  "creditors", "seller"),
    "sales":           ("Sales",       True,  "sales",    "out", "debtors",   "buyer"),
    "sales_return":    ("Credit Note", False, "sales",    "out", "debtors",   "buyer"),
    "purchase_return": ("Debit Note",  True,  "purchase", "in",  "creditors", "seller"),
}


# EDU mode is ON unless the firm setting or the environment turns it off.
# Order: firm setting "edu_mode" (if present) > env TALLY_EDU_MODE > ON.
def edu_mode_enabled(settings):
    if isinstance(settings, dict) and "edu_mode" in settings:
        return bool(settings.get("edu_mode"))
    value = os.getenv("TALLY_EDU_MODE", "1").strip().lower()
    return value not in ("0", "false", "no", "off")


# Escape text for XML and remove control characters Tally cannot read.
def _esc(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text or ""))
    return escape(text, {'"': "&quot;", "'": "&apos;"})


# Tidy a name so it is safe to use as a Tally ledger name.
def _clean_name(text, limit=90):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace(":", "-")
    return text[:limit].strip(" -,.")


def _money(value):
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip() or 0)
    except ValueError:
        return 0.0


# Turn the bill date into a datetime. We do NOT silently use today's
# date because a wrong date in the books is worse than an error.
def _parse_date(raw):
    s = str(raw or "").strip()
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d",
               "%d %b %Y", "%d %B %Y", "%d/%m/%y", "%d-%m-%y"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise XmlBuildError("Invoice date is missing or unreadable. Please edit it (example 05-10-2026).")


def _names(settings):
    settings = settings if isinstance(settings, dict) else {}

    def get(key, default):
        return settings.get(key) or default

    return {
        "purchase":  get("purchase_ledger",      "Purchase Account"),
        "sales":     get("sales_ledger",         "Sales Account"),
        "cgst_in":   get("cgst_input_ledger",    "Input CGST"),
        "sgst_in":   get("sgst_input_ledger",    "Input SGST"),
        "igst_in":   get("igst_input_ledger",    "Input IGST"),
        "cgst_out":  get("cgst_output_ledger",   "Output CGST"),
        "sgst_out":  get("sgst_output_ledger",   "Output SGST"),
        "igst_out":  get("igst_output_ledger",   "Output IGST"),
        "creditors": get("party_group_purchase", "Sundry Creditors"),
        "debtors":   get("party_group_sales",    "Sundry Debtors"),
        "round_off": get("round_off_ledger",     "Round Off"),
    }


# The company that must be OPEN in Tally = the client's business.
def _resolve_company_name(firm, invoice):
    client_id = invoice.get("client_id")
    if client_id:
        client = db.clients.find_one(
            {"_id": client_id}, {"business_name": 1, "tally_company_name": 1})
        if client:
            explicit = (client.get("tally_company_name") or "").strip()
            if explicit:
                return explicit
            business = (client.get("business_name") or "").strip()
            if business:
                return business
    settings = firm.get("tally_settings") or {}
    return settings.get("company_name") or firm.get("name") or "INVEXA Company"


def _ledger_master(name, parent, extra=""):
    return (
        "      <TALLYMESSAGE xmlns:UDF=\"TallyUDF\">\n"
        f'        <LEDGER NAME="{_esc(name)}" ACTION="Create">\n'
        f"          <NAME>{_esc(name)}</NAME>\n"
        f"          <PARENT>{_esc(parent)}</PARENT>\n"
        f"{extra}"
        "          <OPENINGBALANCE>0</OPENINGBALANCE>\n"
        "        </LEDGER>\n"
        "      </TALLYMESSAGE>\n"
    )


def _party_master(name, group, gstin):
    # Only send a GSTIN if it has the right shape; a bad one can make
    # Tally reject the whole import.
    if gstin and GSTIN_FORMAT.match(gstin):
        extra = ("          <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>\n"
                 f"          <PARTYGSTIN>{_esc(gstin)}</PARTYGSTIN>\n")
    else:
        extra = "          <GSTREGISTRATIONTYPE>Unregistered</GSTREGISTRATIONTYPE>\n"
    return _ledger_master(name, group, extra)


def _tax_master(name, head):
    extra = ("          <TAXTYPE>GST</TAXTYPE>\n"
             f"          <GSTDUTYHEAD>{head}</GSTDUTYHEAD>\n")
    return _ledger_master(name, "Duties & Taxes", extra)


# One ledger line of the voucher. Debit = negative, credit = positive.
def _entry(ledger, amount, is_debit, bill_ref=None):
    signed = -amount if is_debit else amount
    if abs(signed) < 0.005:
        signed = 0.0
    block = (
        "          <ALLLEDGERENTRIES.LIST>\n"
        f"            <LEDGERNAME>{_esc(ledger)}</LEDGERNAME>\n"
        f"            <ISDEEMEDPOSITIVE>{'Yes' if is_debit else 'No'}</ISDEEMEDPOSITIVE>\n"
        f"            <AMOUNT>{signed:.2f}</AMOUNT>\n"
    )
    if bill_ref:
        block += (
            "            <BILLALLOCATIONS.LIST>\n"
            f"              <NAME>{_esc(bill_ref)}</NAME>\n"
            "              <BILLTYPE>New Ref</BILLTYPE>\n"
            f"              <AMOUNT>{signed:.2f}</AMOUNT>\n"
            "            </BILLALLOCATIONS.LIST>\n"
        )
    block += "          </ALLLEDGERENTRIES.LIST>\n"
    return block, signed


def build_tally_xml(firm, invoice):
    ocr = invoice.get("ocr") or {}
    settings = firm.get("tally_settings") or {}
    names = _names(settings)

    # ---- voucher kind ----
    raw_type = str(invoice.get("bill_type") or ocr.get("detected_type") or "purchase")
    key = raw_type.strip().lower().replace(" ", "_")
    if key not in KINDS:
        key = "purchase"
    voucher_type, party_is_debit, main_key, tax_set, group_key, which = KINDS[key]

    # ---- party (buyer for sales, seller for purchase) ----
    if which == "buyer":
        party = _clean_name(ocr.get("buyer_name") or ocr.get("party_name"))
        gstin = (ocr.get("buyer_gstin") or ocr.get("party_gstin") or "").strip().upper()
    else:
        party = _clean_name(ocr.get("seller_name") or ocr.get("vendor_name"))
        gstin = (ocr.get("seller_gstin") or ocr.get("gstin") or "").strip().upper()
    if not party:
        label = "Buyer (Bill To)" if which == "buyer" else "Seller"
        raise XmlBuildError(f"{label} name is missing. Please fill it in before approving.")

    # ---- amounts ----
    total = _money(ocr.get("total_amount"))
    cgst = _money(ocr.get("cgst"))
    sgst = _money(ocr.get("sgst"))
    igst = _money(ocr.get("igst"))
    taxable = _money(ocr.get("taxable_amount"))
    if taxable <= 0 and total > 0:
        taxable = round(total - cgst - sgst - igst, 2)
    if total <= 0 or taxable <= 0:
        raise XmlBuildError("Total / taxable amount is missing. Please correct the amounts.")
    if (cgst or sgst) and igst:
        raise XmlBuildError("A bill cannot have both IGST and CGST/SGST.")

    others = round(taxable + cgst + sgst + igst, 2)
    diff = round(total - others, 2)
    if abs(diff) > 1.0:
        raise XmlBuildError(
            f"Amounts do not add up: taxable {taxable:.2f} + tax {others - taxable:.2f} "
            f"= {others:.2f}, but total is {total:.2f}. Please correct them.")

    # ---- date ----
    # Tally EDU rejects most dates with "Voucher Date is missing", so in
    # EDU mode the voucher goes in on the 1st of the bill's month.
    # The real bill date is kept in the reference date and narration.
    bill_date = _parse_date(ocr.get("invoice_date"))
    voucher_date = bill_date.replace(day=1) if edu_mode_enabled(settings) else bill_date
    date_str = voucher_date.strftime("%Y%m%d")
    bill_date_str = bill_date.strftime("%Y%m%d")

    voucher_number = _clean_name(ocr.get("invoice_number") or str(invoice.get("_id", "")), 40)
    company = _resolve_company_name(firm, invoice)

    # ---- ledger names ----
    main_ledger = names[main_key]
    party_group = names[group_key]
    if tax_set == "in":
        tax_names = (names["cgst_in"], names["sgst_in"], names["igst_in"])
    else:
        tax_names = (names["cgst_out"], names["sgst_out"], names["igst_out"])

    # ---- masters (created before the voucher) ----
    masters = [
        _party_master(party, party_group, gstin),
        _ledger_master(main_ledger, "Purchase Accounts" if main_key == "purchase" else "Sales Accounts"),
    ]
    if cgst:
        masters.append(_tax_master(tax_names[0], "Central Tax"))
    if sgst:
        masters.append(_tax_master(tax_names[1], "State Tax"))
    if igst:
        masters.append(_tax_master(tax_names[2], "Integrated Tax"))
    if diff:
        masters.append(_ledger_master(names["round_off"], "Indirect Expenses"))

    # ---- voucher entries ----
    # The party takes one side, everything else takes the opposite side.
    others_debit = not party_is_debit
    entries = []
    running = 0.0

    def add(ledger, amount, is_debit, ref=None):
        nonlocal running
        text, signed = _entry(ledger, amount, is_debit, ref)
        entries.append(text)
        running += signed

    add(party, total, party_is_debit, ref=voucher_number)
    add(main_ledger, taxable, others_debit)
    if cgst:
        add(tax_names[0], cgst, others_debit)
    if sgst:
        add(tax_names[1], sgst, others_debit)
    if igst:
        add(tax_names[2], igst, others_debit)
    if diff:
        # total bigger than parts: round-off goes on the same side as the parts
        add(names["round_off"], abs(diff), others_debit if diff > 0 else party_is_debit)

    if abs(running) > 0.005:
        raise XmlBuildError(f"Voucher is not balanced (difference {running:.2f}).")

    narration = f"Imported from INVEXA | Bill {voucher_number} dated {bill_date.strftime('%d-%m-%Y')}"

    return (
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <VERSION>1</VERSION>\n"
        "    <TALLYREQUEST>Import</TALLYREQUEST>\n"
        "    <TYPE>Data</TYPE>\n"
        "    <ID>Vouchers</ID>\n"
        "  </HEADER>\n"
        "  <BODY>\n"
        "    <DESC>\n"
        "      <STATICVARIABLES>\n"
        f"        <SVCURRENTCOMPANY>{_esc(company)}</SVCURRENTCOMPANY>\n"
        "      </STATICVARIABLES>\n"
        "    </DESC>\n"
        "    <DATA>\n"
        + "".join(masters) +
        "      <TALLYMESSAGE xmlns:UDF=\"TallyUDF\">\n"
        f'        <VOUCHER VCHTYPE="{voucher_type}" ACTION="Create" OBJVIEW="Accounting Voucher View">\n'
        f"          <DATE>{date_str}</DATE>\n"
        f"          <EFFECTIVEDATE>{date_str}</EFFECTIVEDATE>\n"
        f"          <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>\n"
        f"          <VOUCHERNUMBER>{_esc(voucher_number)}</VOUCHERNUMBER>\n"
        f"          <REFERENCE>{_esc(voucher_number)}</REFERENCE>\n"
        f"          <REFERENCEDATE>{bill_date_str}</REFERENCEDATE>\n"
        f"          <PARTYLEDGERNAME>{_esc(party)}</PARTYLEDGERNAME>\n"
        + (f"          <PARTYGSTIN>{_esc(gstin)}</PARTYGSTIN>\n" if gstin and GSTIN_FORMAT.match(gstin) else "")
        + f"          <NARRATION>{_esc(narration)}</NARRATION>\n"
        "          <ISINVOICE>No</ISINVOICE>\n"
        "          <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>\n"
        + "".join(entries) +
        "        </VOUCHER>\n"
        "      </TALLYMESSAGE>\n"
        "    </DATA>\n"
        "  </BODY>\n"
        "</ENVELOPE>\n"
    )