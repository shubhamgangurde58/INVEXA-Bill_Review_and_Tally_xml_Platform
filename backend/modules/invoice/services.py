import gridfs

from extensions import db, fs
from models.invoice_models import INVOICE_STATUSES
from utils.paging import read_paging
from utils.serializers import invoice_detail, invoice_row
from utils.validators import to_object_id


# Build the database filter that decides which bills this user may touch.
# A CA sees every bill of their firm. A client sees only their own. Every
# invoice route starts from this filter, so firm_id is never forgotten.
def scope_for_user(user):
    query = {"firm_id": user["firm_id"]}
    if user["role"] == "client":
        query["client_id"] = user["user_id"]
    return query


# Look up business names for a set of client ids in one query, instead of
# one query per bill. The firm_id filter keeps it inside the firm.
def load_client_names(firm_id, client_ids):
    names = {}
    clients = db.clients.find({"_id": {"$in": list(client_ids)}, "firm_id": firm_id}, {"business_name": 1})
    for client in clients:
        names[client["_id"]] = client["business_name"]
    return names


# List all bills of the CA's firm, newest first, with optional ?status= and
# ?client_id= filters and paging.
def list_firm_invoices(user, args):
    query = scope_for_user(user)

    status = args.get("status", "")
    if status != "":
        if status not in INVOICE_STATUSES:
            return None, ("Unknown status", 400)
        query["status"] = status

    raw_client_id = args.get("client_id", "")
    if raw_client_id != "":
        client_id = to_object_id(raw_client_id)
        if client_id is None:
            return None, ("Client not found", 404)
        query["client_id"] = client_id

    page, page_size, skip = read_paging(args)
    bills = list(db.invoices.find(query).sort("uploaded_at", -1).skip(skip).limit(page_size))
    names = load_client_names(user["firm_id"], {bill["client_id"] for bill in bills})

    return {
        "invoices": [invoice_row(bill, names.get(bill["client_id"], "")) for bill in bills],
        "total": db.invoices.count_documents(query),
        "page": page,
        "page_size": page_size,
    }, None


# Find one bill the user is allowed to see, or None. A bill from another
# firm, or another client's bill, is answered with "not found" and never
# with "forbidden", so nobody can tell that it exists.
def find_visible_invoice(user, raw_invoice_id):
    invoice_id = to_object_id(raw_invoice_id)
    if invoice_id is None:
        return None
    query = scope_for_user(user)
    query["_id"] = invoice_id
    return db.invoices.find_one(query)


# One bill with its extracted data. The CA also gets the Tally import result.
def get_invoice(user, raw_invoice_id):
    invoice = find_visible_invoice(user, raw_invoice_id)
    if invoice is None:
        return None, ("Bill not found", 404)

    names = load_client_names(user["firm_id"], {invoice["client_id"]})
    client_name = names.get(invoice["client_id"], "")
    return invoice_detail(invoice, client_name, user["role"] == "ca"), None


# Read the stored file of a bill. Besides the invoice filter, the file's own
# firm_id tag must match too, as a second lock. Returns
# ((bytes, mime_type, file_name), None) or (None, (message, status)).
def load_invoice_file(user, raw_invoice_id):
    invoice = find_visible_invoice(user, raw_invoice_id)
    if invoice is None:
        return None, ("Bill not found", 404)

    try:
        stored_file = fs.get(invoice["file_id"])
    except gridfs.errors.NoFile:
        return None, ("File not found", 404)

    if getattr(stored_file, "firm_id", None) != user["firm_id"]:
        return None, ("File not found", 404)
    return (stored_file.read(), stored_file.content_type, invoice["file_name"]), None
