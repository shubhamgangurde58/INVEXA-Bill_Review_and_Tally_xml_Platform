from extensions import db, fs
from models import utc_now
from models.invoice_models import BILL_TYPES, INVOICE_STATUSES, empty_ocr_data, new_invoice_doc
from utils.audit import log_action
from utils.notifications import create_notification
from utils.paging import read_paging
from utils.serializers import invoice_row, to_iso
from utils.transactions import run_in_transaction
from utils.uploads import read_upload
from utils.validators import clean_text, to_object_id


# Raised inside a transaction when the bill is no longer in the expected
# state, so the whole transaction is cancelled.
class BillStateChanged(Exception):
    pass


# The client's own profile, for the profile page and for the "waiting for
# approval" screen. It works for pending clients too.
def get_client_profile(user):
    client = db.clients.find_one({"_id": user["user_id"], "firm_id": user["firm_id"]})
    if client is None:
        return None, ("Profile not found", 404)

    return {
        "id": str(client["_id"]),
        "business_name": client["business_name"],
        "owner_name": client["owner_name"],
        "email": client["email"],
        "mobile": client["mobile"],
        "gstin": client["gstin"],
        "address": client["address"],
        "status": client["status"],
        "email_verified": client.get("email_verified", False),
        "joined_at": to_iso(client.get("createdAt")),
    }, None


# The firm and CA this client belongs to. Only the CA's name and ICAI
# number are shared, not their email.
def get_my_firm(user):
    firm = db.firms.find_one({"_id": user["firm_id"]})
    if firm is None:
        return None, ("Firm not found", 404)
    ca = db.cas.find_one({"_id": firm["owner_ca_id"], "firm_id": user["firm_id"]}, {"name": 1, "membership_number": 1})
    if ca is None:
        return None, ("Firm not found", 404)

    return {
        "firm_name": firm["name"],
        "ca_name": ca["name"],
        "ca_membership_number": ca["membership_number"],
    }, None


# The client's own bills, newest first. Both firm_id and client_id are in
# the filter, so a client can never list someone else's bills.
# List this client's bills with optional status filter, text search,
# and paging. Both firm_id and client_id are in the query, so a client
# can never see another client's bills. Search looks at file name,
# invoice number, and the OCR vendor name.
def list_my_invoices(user, args):
    query = {"firm_id": user["firm_id"], "client_id": user["user_id"]}

    status = (args.get("status") or "").strip()
    if status and status != "all":
        if status not in INVOICE_STATUSES:
            return None, ("Unknown status", 400)
        query["status"] = status

    # Text search: match the file name, the invoice number, or the
    # vendor name inside the OCR blob.
    q = (args.get("q") or "").strip()
    if q:
        safe = q.replace("(", r"\(").replace(")", r"\)")
        pattern = {"$regex": safe, "$options": "i"}
        query["$or"] = [
            {"file_name": pattern},
            {"invoice_number": pattern},
            {"ocr.vendor_name": pattern},
            {"ocr.invoice_number": pattern},
        ]

    page, page_size, skip = read_paging(args)
    bills = list(
        db.invoices.find(query)
        .sort("uploaded_at", -1)
        .skip(skip)
        .limit(page_size)
    )

    return {
        "invoices": [invoice_row(bill) for bill in bills],
        "total": db.invoices.count_documents(query),
        "page": page,
        "page_size": page_size,
    }, None


# Remove a stored file again if saving the invoice failed, so a failed
# upload never leaves an orphan file in GridFS.
def discard_file(file_id):
    try:
        fs.delete(file_id)
    except Exception:
        pass


# Upload a new bill. The file is checked, stored in GridFS (tagged with the
# firm and client), and the invoice, audit row and "bill_uploaded"
# notification for the CA are saved together. If that fails, the file is
# deleted again. Only approved clients reach this function.
def upload_invoice(user, file_storage, form, ip_address):
    bill_type = clean_text(form.get("bill_type")) or "purchase"
    if bill_type not in BILL_TYPES:
        return None, ("Bill type must be purchase or sales", 400)

    upload, problem = read_upload(file_storage)
    if problem is not None:
        return None, problem

    firm = db.firms.find_one({"_id": user["firm_id"]}, {"owner_ca_id": 1})
    file_id = fs.put(upload["data"], filename=upload["file_name"], content_type=upload["mime_type"],
                     firm_id=user["firm_id"], client_id=user["user_id"])
    invoice = new_invoice_doc(user["firm_id"], user["user_id"], user["user_id"], file_id,
                              upload["file_name"], upload["extension"], bill_type)

    def save_all(session):
        result = db.invoices.insert_one(invoice, session=session)
        log_action(user["firm_id"], user["user_id"], "client", "invoice_uploaded", result.inserted_id,
                   {"file_name": upload["file_name"]}, ip_address, session=session)
        create_notification(user["firm_id"], firm["owner_ca_id"], "ca", "bill_uploaded",
                            "New bill uploaded", "A client uploaded " + upload["file_name"] + ".",
                            "/ca/documents", session=session)

    try:
        run_in_transaction(save_all)
    except Exception:
        discard_file(file_id)
        raise
    return invoice_row(invoice), None


# Build the update that puts a bill back in the review queue with its new
# file. The old OCR data described the old picture, so it is cleared, and
# the old file id moves to file_history instead of being deleted.
def build_reupload_update(old_file_id, new_file_id, upload):
    return {
        "$set": {
            "file_id": new_file_id,
            "file_name": upload["file_name"],
            "file_extension": upload["extension"],
            "status": "pending_review",
            "invoice_number": None,
            "ocr": empty_ocr_data(),
            "reupload_reason": "",
            "reupload_requested_at": None,
            "reupload_requested_by": None,
        },
        "$push": {"file_history": old_file_id},
    }


# Replace the file of a bill the CA asked to be re-uploaded. Only that
# client's own bill, and only while its status is "reupload_requested". The
# update re-checks the status, so a double click cannot run it twice.
def reupload_invoice(user, raw_invoice_id, file_storage, ip_address):
    invoice_id = to_object_id(raw_invoice_id)
    if invoice_id is None:
        return None, ("Bill not found", 404)

    scope = {"_id": invoice_id, "firm_id": user["firm_id"], "client_id": user["user_id"]}
    invoice = db.invoices.find_one(scope)
    if invoice is None:
        return None, ("Bill not found", 404)
    if invoice["status"] != "reupload_requested":
        return None, ("This bill is not waiting for a new photo", 409)

    upload, problem = read_upload(file_storage)
    if problem is not None:
        return None, problem

    firm = db.firms.find_one({"_id": user["firm_id"]}, {"owner_ca_id": 1})
    new_file_id = fs.put(upload["data"], filename=upload["file_name"], content_type=upload["mime_type"],
                         firm_id=user["firm_id"], client_id=user["user_id"])
    update = build_reupload_update(invoice["file_id"], new_file_id, upload)

    def save_all(session):
        result = db.invoices.update_one({**scope, "status": "reupload_requested"}, update, session=session)
        if result.matched_count == 0:
            raise BillStateChanged()
        log_action(user["firm_id"], user["user_id"], "client", "invoice_reuploaded", invoice_id,
                   {"file_name": upload["file_name"], "at": utc_now().isoformat()}, ip_address, session=session)
        create_notification(user["firm_id"], firm["owner_ca_id"], "ca", "bill_uploaded",
                            "Bill uploaded again", "A client uploaded a new photo for " + invoice["file_name"] + ".",
                            "/ca/documents", session=session)

    try:
        run_in_transaction(save_all)
    except BillStateChanged:
        discard_file(new_file_id)
        return None, ("This bill is not waiting for a new photo", 409)
    except Exception:
        discard_file(new_file_id)
        raise

    return invoice_row(db.invoices.find_one(scope)), None


# Delete a bill the client just uploaded, before the CA has touched it.
# Only status "uploaded" is allowed — once review starts, the record is
# kept for the CA's audit trail. The GridFS file is removed too.
def delete_my_invoice(user, raw_invoice_id):
    from extensions import fs
    from utils.validators import to_object_id

    invoice_id = to_object_id(raw_invoice_id)
    if invoice_id is None:
        return None, ("Bill not found", 404)

    bill = db.invoices.find_one({
        "_id": invoice_id,
        "firm_id": user["firm_id"],
        "client_id": user["user_id"],
    })
    if bill is None:
        return None, ("Bill not found", 404)

    if bill["status"] != "uploaded":
        return None, (
            "This bill is already in review and cannot be deleted. "
            "Ask your CA if it should be removed.",
            409,
        )

    # Remove the file from GridFS first, then the invoice document.
    try:
        fs.delete(bill["file_id"])
    except Exception:
        pass  # a missing file is fine

    db.invoices.delete_one({"_id": invoice_id, "client_id": user["user_id"]})
    log_action(user["firm_id"], user["user_id"], "client",
               "invoice_deleted", invoice_id,
               {"file_name": bill["file_name"]}, None)
    return {"deleted": True}, None

# Update the client's own editable fields. Only the fields listed
# here can be changed — email, GSTIN and status stay locked so
# account integrity and approvals are not silently bypassed.
def update_client_profile(user, data):
    from utils.validators import clean_text

    updates = {}
    if "business_name" in data:
        v = clean_text(data["business_name"])
        if not v:
            return None, ("Business name cannot be empty", 400)
        updates["business_name"] = v
    if "owner_name" in data:
        v = clean_text(data["owner_name"])
        if not v:
            return None, ("Owner name cannot be empty", 400)
        updates["owner_name"] = v
    if "mobile" in data:
        v = clean_text(data["mobile"])
        if v and (not v.isdigit() or len(v) != 10 or v[0] not in "6789"):
            return None, ("Enter a valid 10-digit mobile number", 400)
        updates["mobile"] = v
    if "address" in data:
        updates["address"] = clean_text(data["address"])

    if not updates:
        return None, ("Nothing to update", 400)

    db.clients.update_one(
        {"_id": user["user_id"], "firm_id": user["firm_id"]},
        {"$set": updates},
    )
    # Return the fresh profile.
    return get_client_profile(user)