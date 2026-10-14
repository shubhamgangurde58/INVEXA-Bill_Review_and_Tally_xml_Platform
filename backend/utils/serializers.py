# Convert a stored datetime to text for JSON. Missing dates become "".
from datetime import timezone

# Return the datetime as an ISO string WITH the UTC marker. The frontend
# uses `new Date(...)` which treats a plain string as local time; adding
# the Z tells the browser the value is UTC so IST displays correctly.
def to_iso(value):
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

# The client fields the CA screens may see. Never include password_hash.
def client_row(client):
    return {
        "id": str(client["_id"]),
        "business_name": client["business_name"],
        "owner_name": client["owner_name"],
        "email": client["email"],
        "mobile": client["mobile"],
        "gstin": client["gstin"],
        "address": client["address"],
        "status": client["status"],
        "created_at": to_iso(client.get("createdAt")),
        "status_changed_at": to_iso(client.get("status_changed_at")),
    }


# One line of a bill list. It never includes file ids or the XML path:
# files are always fetched through the invoice id, so the browser never
# learns how files are stored.
def invoice_row(invoice, client_name=""):
    ocr = invoice.get("ocr") or {}
    return {
        "id": str(invoice["_id"]),
        "client_id": str(invoice["client_id"]),
        "client_name": client_name,
        "file_name": invoice["file_name"],
        "file_extension": invoice["file_extension"],
        "status": invoice["status"],
        "bill_type": invoice["bill_type"],
        "invoice_number": invoice.get("invoice_number") or "",
        "vendor_name": ocr.get("vendor_name", ""),
        "total_amount": ocr.get("total_amount", 0),
        "remarks": invoice.get("remarks", ""),
        "reupload_reason": invoice.get("reupload_reason", ""),
        "uploaded_at": to_iso(invoice.get("uploaded_at")),
        "approved_at": to_iso(invoice.get("approved_at")),
    }


# The full view of one bill. The CA also gets the Tally import result;
# clients do not. xml_file_path stays hidden from everyone: it is a path
# on the CA's computer, and only "has_xml" is shown.
def invoice_detail(invoice, client_name, for_ca):
    detail = invoice_row(invoice, client_name)
    detail["ocr"] = dict(invoice.get("ocr") or {})
    detail["reupload_requested_at"] = to_iso(invoice.get("reupload_requested_at"))
    detail["file_versions"] = len(invoice.get("file_history", [])) + 1

    if for_ca:
        detail["tally_import_status"] = invoice.get("tally_import_status", "not_imported")
        detail["tally_import_message"] = invoice.get("tally_import_message", "")
        detail["tally_imported_at"] = to_iso(invoice.get("tally_imported_at"))
        detail["has_xml"] = invoice.get("xml_file_path") is not None
    else:
        detail["ocr"].pop("raw_text", None)
    return detail
