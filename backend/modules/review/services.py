"""Business logic for the review queue. Single XML file per approve."""

from bson import ObjectId

from extensions import db, fs
from models import utc_now
from models.invoice_models import REUPLOAD_REASONS
from modules.review.ocr import OcrNotAvailable, extract_fields
from modules.xml.tally_builder import build_tally_xml
from utils.audit import log_action
from utils.notifications import create_notification
from utils.serializers import invoice_detail
from utils.validators import amount_error, clean_text, to_object_id


ALLOWED_VOUCHER_TYPES = {
    "purchase", "sales",
    "purchase_return", "sales_return",
    "credit_note", "debit_note",
    "payment", "receipt", "journal",
    "expense", "contra",
    "delivery_note", "receipt_note",
    "rejection_in", "rejection_out",
}


def find_bill(firm_id, raw_id):
    invoice_id = to_object_id(raw_id)
    if invoice_id is None:
        return None
    return db.invoices.find_one({"_id": invoice_id, "firm_id": firm_id})


def client_name_for(firm_id, client_id):
    c = db.clients.find_one({"_id": client_id, "firm_id": firm_id}, {"business_name": 1})
    return c.get("business_name", "") if c else ""


def load_bill_bytes(bill):
    try:
        return fs.get(bill["file_id"]).read(), None
    except Exception as exc:
        print("[review] file read failed:", exc)
        return None, ("Could not read the stored bill", 500)


def run_ocr_for_bill(user, raw_id):
    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)

    image_bytes, problem = load_bill_bytes(bill)
    if problem:
        return None, problem

    extension = (bill.get("file_extension") or "png").lower()

    try:
        ocr = extract_fields(image_bytes, extension)
    except OcrNotAvailable as exc:
        return None, (str(exc), 503)
    except Exception as exc:
        print("[review] OCR unexpected:", exc)
        return None, ("OCR failed. Check the server console.", 500)

    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {"ocr": ocr, "status": "pending_review", "ocr_at": utc_now()}},
    )

    log_action(user["firm_id"], user["user_id"], "ca", "ocr_run",
               target_id=bill["_id"], details={}, ip_address=None)

    bill["ocr"] = ocr
    bill["status"] = "pending_review"
    return invoice_detail(bill, client_name_for(user["firm_id"], bill["client_id"]), True), None


def save_ocr(user, raw_id, payload):
    ocr = payload.get("ocr")
    if not isinstance(ocr, dict):
        return None, ("Invalid OCR data", 400)

    for key in ("taxable_amount", "cgst", "sgst", "igst", "total_amount"):
        value = ocr.get(key, 0)
        if isinstance(value, str):
            value = value.strip() or 0
            try:
                value = float(value.replace(",", ""))
            except ValueError:
                return None, (f"{key} must be a number", 400)
        ocr[key] = value

    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)

    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {"ocr": ocr, "ocr_edited_at": utc_now()}},
    )
    log_action(user["firm_id"], user["user_id"], "ca", "ocr_edited",
               target_id=bill["_id"], details={}, ip_address=None)
    return {"saved": True}, None


def _validate_approve(ocr, bill_type):
    if bill_type not in ALLOWED_VOUCHER_TYPES:
        return "Voucher type is not supported."
    if not clean_text(ocr.get("invoice_number")):
        return "Invoice number is required."
    if not clean_text(ocr.get("vendor_name")):
        return "Vendor name is required."
    err = amount_error(ocr.get("total_amount", 0))
    if err:
        return err
    return ""


def approve_bill(user, raw_id, payload):
    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)

    ocr = payload.get("ocr")
    if not isinstance(ocr, dict):
        ocr = bill.get("ocr") or {}

    bill_type = clean_text(payload.get("bill_type")).lower() or "purchase"

    problem = _validate_approve(ocr, bill_type)
    if problem:
        return None, (problem, 400)

    firm = db.firms.find_one({"_id": user["firm_id"]})
    if firm is None:
        return None, ("Firm not found", 404)

    invoice_number = clean_text(ocr.get("invoice_number"))

    if bill.get("xml_file_id"):
        try:
            fs.delete(bill["xml_file_id"])
        except Exception:
            pass

    snapshot = dict(bill)
    snapshot["ocr"] = ocr
    snapshot["bill_type"] = bill_type

    try:
        xml_text = build_tally_xml(firm, snapshot)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return None, (f"XML build failed: {exc}", 500)

    safe_number = "".join(c for c in str(invoice_number) if c.isalnum() or c in "-_")

    try:
        file_id = fs.put(
            xml_text.encode("utf-8"),
            filename=f"INVEXA_{safe_number}.xml",
            content_type="application/xml",
            firm_id=bill["firm_id"],
            client_id=bill["client_id"],
            invoice_id=bill["_id"],
            kind="xml_voucher",
        )
    except Exception as exc:
        return None, (f"XML store failed: {exc}", 500)

    now = utc_now()
    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {
            "ocr": ocr,
            "bill_type": bill_type,
            "invoice_number": invoice_number,
            "status": "approved",
            "approved_by": user["user_id"],
            "approved_at": now,
            "xml_file_id": file_id,
            "xml_generated_at": now,
            "tally_import_status": "not_imported",
            "tally_imported_at": None,
        }},
    )

    create_notification(user["firm_id"], bill["client_id"], "client",
                        "bill_approved", "Bill approved",
                        f"{invoice_number} was approved.", "/client/invoices")

    log_action(user["firm_id"], user["user_id"], "ca", "invoice_approved",
               target_id=bill["_id"], details={"invoice_number": invoice_number},
               ip_address=None)

    return {
        "approved": True,
        "download_url": f"/api/xml/download/{str(bill['_id'])}",
        "xml_file_id": str(file_id),
    }, None


def reject_bill(user, raw_id, payload):
    remarks = clean_text(payload.get("remarks"))
    if len(remarks) < 5:
        return None, ("Please write at least 5 characters explaining the rejection", 400)

    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)

    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {"status": "rejected", "remarks": remarks,
                  "rejected_at": utc_now(), "rejected_by": user["user_id"]}},
    )
    create_notification(user["firm_id"], bill["client_id"], "client",
                        "bill_rejected", "Bill needs changes", remarks,
                        "/client/invoices")
    log_action(user["firm_id"], user["user_id"], "ca", "invoice_rejected",
               target_id=bill["_id"], details={"remarks": remarks}, ip_address=None)
    return {"rejected": True}, None


def request_reupload(user, raw_id, payload):
    reason = clean_text(payload.get("reason"))
    if reason not in REUPLOAD_REASONS:
        return None, ("Invalid reupload reason", 400)

    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)

    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {"status": "reupload_requested", "reupload_reason": reason,
                  "reupload_requested_at": utc_now(),
                  "reupload_requested_by": user["user_id"]}},
    )
    create_notification(user["firm_id"], bill["client_id"], "client",
                        "reupload_requested", "New photo needed",
                        f"Your CA asked for a clearer copy: {reason}.",
                        "/client/invoices")
    log_action(user["firm_id"], user["user_id"], "ca", "reupload_requested",
               target_id=bill["_id"], details={"reason": reason}, ip_address=None)
    return {"reupload_requested": True}, None


def mark_imported(user, raw_id):
    bill = find_bill(user["firm_id"], raw_id)
    if bill is None:
        return None, ("Bill not found", 404)
    if bill.get("status") != "approved":
        return None, ("Only approved bills can be marked as imported", 400)
    if not bill.get("xml_file_id"):
        return None, ("No XML exists for this bill. Approve it first.", 400)

    now = utc_now()
    db.invoices.update_one(
        {"_id": bill["_id"], "firm_id": user["firm_id"]},
        {"$set": {"tally_import_status": "imported", "tally_imported_at": now}},
    )
    log_action(user["firm_id"], user["user_id"], "ca", "tally_imported",
               target_id=bill["_id"], details={}, ip_address=None)
    return {"imported": True, "tally_imported_at": now.isoformat()}, None