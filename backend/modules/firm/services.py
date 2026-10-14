from pymongo.errors import DuplicateKeyError

from extensions import db
from models import utc_now
from utils.audit import log_action
from utils.invite_codes import generate_invite_code
from utils.notifications import create_notification
from utils.serializers import client_row, to_iso
from utils.transactions import run_in_transaction
from utils.validators import to_object_id

MAX_CODE_TRIES = 5


# Raised inside a transaction when another request already changed the
# client's status, so the whole transaction is cancelled.
class RequestAlreadyHandled(Exception):
    pass


# List this firm's clients with one status. The firm_id filter is what keeps
# one CA from ever seeing another firm's clients. The route chooses which
# statuses are allowed: the client list shows "active", the join requests
# screen shows "pending" and "rejected".
def list_clients(firm_id, status, allowed_statuses):
    if status not in allowed_statuses:
        return None, ("Status must be one of: " + ", ".join(allowed_statuses), 400)

    clients = db.clients.find({"firm_id": firm_id, "status": status}).sort("createdAt", -1)
    return {"status": status, "clients": [client_row(client) for client in clients]}, None


# Replace the firm's invite code with a new one. The old code stops working
# at once, but clients who already joined are not affected. The code itself
# is never written to the audit log. If the new code collides with another
# firm's (very rare), the unique index refuses it and we try again.
def regenerate_invite_code(user, ip_address):
    firm_id = user["firm_id"]
    firm = db.firms.find_one({"_id": firm_id}, {"name": 1})
    if firm is None:
        return None, ("Firm not found", 404)

    for _ in range(MAX_CODE_TRIES):
        new_code = generate_invite_code(firm["name"])
        changed_at = utc_now()

        def save_code(session):
            db.firms.update_one({"_id": firm_id},
                                {"$set": {"invite_code": new_code, "invite_code_updated_at": changed_at}},
                                session=session)
            log_action(firm_id, user["user_id"], "ca", "invite_code_regenerated", firm_id,
                       {}, ip_address, session=session)

        try:
            run_in_transaction(save_code)
        except DuplicateKeyError:
            continue
        return {"invite_code": new_code, "invite_code_updated_at": to_iso(changed_at)}, None

    return None, ("Could not create a new code. Please try again.", 500)


# Build the notification text for an approve or reject decision.
def decision_message(approve, firm_name):
    if approve:
        return "client_approved", "Request approved", firm_name + " approved your request. You can upload bills now.", "/client/dashboard"
    return "client_rejected", "Request not approved", firm_name + " did not approve your request.", None


# Approve or reject a client's join request.
# Approve works on pending or rejected clients (a rejected one can be
# approved later if it was a mistake). Reject works on pending clients only.
# The status change, the audit row and the client's notification are saved
# together. The update also checks the old status, so two quick clicks
# cannot both succeed.
def decide_client(user, raw_client_id, approve, ip_address):
    client_id = to_object_id(raw_client_id)
    if client_id is None:
        return None, ("Client not found", 404)

    firm_id = user["firm_id"]
    client = db.clients.find_one({"_id": client_id, "firm_id": firm_id})
    if client is None:
        return None, ("Client not found", 404)

    allowed_from = ["pending"]
    new_status = "rejected"
    if approve:
        allowed_from = ["pending", "rejected"]
        new_status = "active"
    if client["status"] not in allowed_from:
        return None, ("This request was already handled", 409)

    firm = db.firms.find_one({"_id": firm_id}, {"name": 1})
    ntype, title, body, link = decision_message(approve, firm["name"])

    def save_all(session):
        result = db.clients.update_one(
            {"_id": client_id, "firm_id": firm_id, "status": {"$in": allowed_from}},
            {"$set": {"status": new_status, "status_changed_at": utc_now()}},
            session=session,
        )
        if result.matched_count == 0:
            raise RequestAlreadyHandled()
        log_action(firm_id, user["user_id"], "ca", ntype, client_id,
                   {"business_name": client["business_name"], "previous_status": client["status"]},
                   ip_address, session=session)
        create_notification(firm_id, client_id, "client", ntype, title, body, link, session=session)

    try:
        run_in_transaction(save_all)
    except RequestAlreadyHandled:
        return None, ("This request was already handled", 409)

    client["status"] = new_status
    return client_row(client), None
