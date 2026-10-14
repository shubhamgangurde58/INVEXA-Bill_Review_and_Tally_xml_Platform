"""Invoice model helpers and constants."""

from models import utc_now

INVOICE_STATUSES = ["uploaded", "pending_review", "approved", "rejected", "reupload_requested"]
BILL_TYPES = ["purchase", "sales"]
TALLY_IMPORT_STATUSES = ["not_imported", "imported", "failed"]
REUPLOAD_REASONS = [
    "Image is blurry",
    "Bill is cut off",
    "Wrong bill uploaded",
    "Missing pages",
    "Other",
]


def empty_ocr_data():
    return {
        "invoice_number": "",
        "invoice_date": "",
        "vendor_name": "",
        "gstin": "",
        "taxable_amount": 0,
        "cgst": 0,
        "sgst": 0,
        "igst": 0,
        "total_amount": 0,
        "raw_text": "",
        "detected_type": "",
    }


def new_invoice_doc(firm_id, client_id, uploaded_by, file_id, file_name,
                    file_extension, bill_type="purchase"):
    if bill_type not in BILL_TYPES:
        bill_type = "purchase"

    return {
        "firm_id": firm_id,
        "client_id": client_id,
        "uploaded_by": uploaded_by,
        "file_id": file_id,
        "file_history": [],
        "file_name": file_name,
        "file_extension": file_extension.lower().lstrip("."),
        "status": "uploaded",
        "invoice_number": None,
        "ocr": empty_ocr_data(),
        "bill_type": bill_type,
        "approved_by": None,
        "approved_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "remarks": "",
        "reupload_reason": "",
        "reupload_requested_at": None,
        "reupload_requested_by": None,
        "xml_file_id": None,
        "xml_generated_at": None,
        "tally_import_status": "not_imported",
        "tally_imported_at": None,
        "uploaded_at": utc_now(),
        "ocr_at": None,
        "ocr_edited_at": None,
    }