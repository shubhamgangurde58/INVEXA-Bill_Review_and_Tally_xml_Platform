from models import utc_now

CLIENT_STATUSES = ["pending", "active", "rejected"]


# Build the default Tally settings for a new firm.
# The XML builder reads these names so the CA never types ledger names
# per bill. The CA can edit them later in firm settings.
# An empty xml_output_folder means "use Desktop/INVEXA_Tally_XML".
def default_tally_settings(firm_name):
    return {
        "company_name": firm_name,
        "host": "localhost",
        "port": 9000,
        "xml_output_folder": "",
        "party_group_purchase": "Sundry Creditors",
        "party_group_sales": "Sundry Debtors",
        "purchase_ledger": "Purchase Account",
        "sales_ledger": "Sales Account",
        "cgst_input_ledger": "Input CGST",
        "sgst_input_ledger": "Input SGST",
        "igst_input_ledger": "Input IGST",
        "cgst_output_ledger": "Output CGST",
        "sgst_output_ledger": "Output SGST",
        "igst_output_ledger": "Output IGST",
    }


# Build one firms document.
# GSTIN and address are optional at signup (the CA fills them later in
# settings), so missing values become empty strings, not None.
# owner_ca_id and firm_id are passed in because both ids are created first,
# so the firm and the CA can point at each other inside one transaction.
def new_firm_doc(name, gstin, address, invite_code, owner_ca_id, firm_id=None):
    firm_name = name.strip()

    clean_gstin = ""
    if gstin:
        clean_gstin = gstin.strip().upper()

    clean_address = ""
    if address:
        clean_address = address.strip()

    doc = {
        "name": firm_name,
        "gstin": clean_gstin,
        "owner_ca_id": owner_ca_id,
        "invite_code": invite_code,
        "invite_code_updated_at": utc_now(),
        "address": clean_address,
        "tally_settings": default_tally_settings(firm_name),
        "createdAt": utc_now(),
    }
    if firm_id is not None:
        doc["_id"] = firm_id
    return doc


# Build one cas document. There is no role field because every CA is
# the owner of exactly one firm.
# Email is lowercased here so the unique index cannot be bypassed by
# typing the same address with different capital letters.
# ca_id is optional so the signup code can create the _id up front.
def new_ca_doc(firm_id, name, email, password_hash, membership_number, ca_id=None):
    doc = {
        "firm_id": firm_id,
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "membership_number": membership_number.strip(),
        "createdAt": utc_now(),
        "lastLoginAt": None,
    }
    if ca_id is not None:
        doc["_id"] = ca_id
    return doc


# Build one clients document (a shop owner who uploads bills).
# New signups default to "pending": they cannot upload or chat until
# the CA approves them. This is what makes a leaked invite code harmless
# on its own.
def new_client_doc(firm_id, business_name, owner_name, email, gstin, mobile, address, password_hash, status="pending"):
    if status not in CLIENT_STATUSES:
        raise ValueError("status must be one of: " + ", ".join(CLIENT_STATUSES))

    return {
        "firm_id": firm_id,
        "business_name": business_name.strip(),
        "owner_name": owner_name.strip(),
        "email": email.strip().lower(),
        "gstin": gstin.strip().upper(),
        "mobile": mobile.strip(),
        "address": address.strip(),
        "password_hash": password_hash,
        "status": status,
        "status_changed_at": utc_now(),
        "createdAt": utc_now(),
    }
