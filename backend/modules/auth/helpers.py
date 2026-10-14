from extensions import db
from utils.jwt_utils import create_token
from utils.validators import (
    is_valid_email, is_valid_gstin, is_valid_membership, is_valid_mobile,
    missing_fields, password_error, clean_text,
)


# Check the fields a signup form must send and their formats.
# GSTIN is checked whenever it is present, but it is only "required" if the
# caller lists it, because a CA firm can add it later and a small shop may
# not have one. Returns None when fine, or (message, status_code).
def validate_fields(data, required_fields):
    missing = missing_fields(data, required_fields)
    if len(missing) > 0:
        return ("Missing required fields: " + ", ".join(missing), 400)
    if "email" in required_fields and not is_valid_email(data["email"].strip()):
        return ("Enter a valid email address", 400)
    if "mobile" in required_fields and not is_valid_mobile(data["mobile"].strip()):
        return ("Enter a valid 10-digit mobile number", 400)
    if "membership_number" in required_fields and not is_valid_membership(data["membership_number"].strip()):
        return ("Enter a valid ICAI membership number", 400)

    gstin = clean_text(data.get("gstin")).upper()
    if gstin != "" and not is_valid_gstin(gstin):
        return ("Enter a valid 15-character GSTIN", 400)

    if "password" in required_fields:
        message = password_error(data["password"])
        if message != "":
            return (message, 400)
    return None


# Pick the collection for a kind of account: "ca" accounts live in cas and
# "client" accounts live in clients.
def collection_for_kind(kind):
    if kind == "ca":
        return db.cas
    return db.clients


# Look an email up in CA accounts and/or client accounts.
# kind="ca" or "client" searches only that collection (login uses this, so
# each login page only accepts its own kind of account). With no kind both
# are searched, which signup uses to keep emails unique across the app.
# Returns ("ca", doc), ("client", doc) or (None, None).
def find_user_by_email(email, kind=None):
    if kind in (None, "ca"):
        ca = db.cas.find_one({"email": email})
        if ca is not None:
            return "ca", ca
    if kind in (None, "client"):
        client = db.clients.find_one({"email": email})
        if client is not None:
            return "client", client
    return None, None


# Find a firm from its invite code. This is a lookup before the user has any
# firm, so it has no firm_id filter.
def find_firm_by_invite_code(code):
    return db.firms.find_one({"invite_code": clean_text(code).upper()})


# The user data the browser is allowed to see (never the password hash).
# Clients also get their status, because the frontend uses it to show the
# "waiting for approval" screen.
def public_user(user_doc, role, firm_doc):
    result = {
        "id": str(user_doc["_id"]),
        "email": user_doc["email"],
        "role": role,
        "firm_id": str(firm_doc["_id"]),
        "firm_name": firm_doc["name"],
        "email_verified": user_doc.get("email_verified", False),
    }
    if role == "client":
        result["name"] = user_doc["owner_name"]
        result["business_name"] = user_doc["business_name"]
        result["status"] = user_doc["status"]
    else:
        result["name"] = user_doc["name"]
    return result


# Package a login result: the 24-hour token plus the public user data.
def make_session(user_doc, role, firm_doc):
    token = create_token(user_doc["_id"], role, firm_doc["_id"], user_doc["email"])
    return {"token": token, "user": public_user(user_doc, role, firm_doc)}
