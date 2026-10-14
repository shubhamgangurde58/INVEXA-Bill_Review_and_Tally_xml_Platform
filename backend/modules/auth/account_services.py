from extensions import db
from models import utc_now
from modules.auth.helpers import (
    collection_for_kind, find_user_by_email, make_session, public_user,
)
from utils.audit import log_action
from utils.auth_tokens import consume_auth_token, create_auth_token, print_dev_link
from utils.passwords import check_password, hash_password
from utils.validators import password_error

# A real bcrypt hash of a throwaway password. When a login email does not
# exist we still check against it, so the reply takes the same time either
# way and response speed never reveals which emails have accounts.
DUMMY_HASH = hash_password("Dummy#Password1")


# Check a login password, using the dummy hash when there is no account.
def password_matches(password, user_doc):
    if user_doc is None:
        check_password(password, DUMMY_HASH)
        return False
    return check_password(password, user_doc["password_hash"])


# Log a user in. Every failure gives the same "Invalid credentials" reply so
# an attacker cannot learn which emails have accounts. "role" is "ca" or
# "client" and comes from which login page was used, so each page only
# accepts its own kind of account. A rejected client is told so, but only
# after the password was correct. A pending client can log in.
def login_user(data, role):
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return None, ("Email and password are required", 400)
    if role not in ("ca", "client"):
        return None, ("Invalid request", 400)

    failed = (None, ("Invalid credentials", 401))
    kind, user_doc = find_user_by_email(email.strip().lower(), role)
    if not password_matches(password, user_doc):
        return failed

    firm_doc = db.firms.find_one({"_id": user_doc["firm_id"]})
    if firm_doc is None:
        return failed

    if role == "client" and user_doc["status"] == "rejected":
        return None, ("Your request was not approved", 403)

    if role == "ca":
        db.cas.update_one({"_id": user_doc["_id"], "firm_id": user_doc["firm_id"]},
                          {"$set": {"lastLoginAt": utc_now()}})
    return make_session(user_doc, role, firm_doc), None


# Fresh profile for the logged-in user, used when the browser reloads and
# only has a token. It reads the current status, so an approved client sees
# the change without logging in again.
def load_profile(auth_user):
    collection = collection_for_kind(auth_user["role"])
    user_doc = collection.find_one({"_id": auth_user["user_id"], "firm_id": auth_user["firm_id"]})
    firm_doc = db.firms.find_one({"_id": auth_user["firm_id"]})
    return public_user(user_doc, auth_user["role"], firm_doc)


# Mark an email as verified using the link token.
def verify_email(raw_token):
    token_doc = consume_auth_token(raw_token, "verify_email")
    if token_doc is None:
        return None, ("This link is invalid or has expired", 400)

    collection = collection_for_kind(token_doc["user_type"])
    collection.update_one({"_id": token_doc["user_id"], "firm_id": token_doc["firm_id"]},
                          {"$set": {"email_verified": True}})
    log_action(token_doc["firm_id"], token_doc["user_id"], token_doc["user_type"],
               "email_verified", target_id=token_doc["user_id"])
    return {"verified": True}, None


# Start a password reset. The caller always gets the same reply, whether or
# not the email exists, so this cannot be used to discover accounts.
def start_password_reset(email):
    kind, user_doc = find_user_by_email(email.strip().lower())
    if user_doc is not None:
        raw_token = create_auth_token(user_doc["_id"], user_doc["firm_id"], kind, "reset_password", 1)
        print_dev_link("Reset password", "/reset-password", raw_token)


# Finish a password reset with the emailed token and a new password.
# The password is checked before the token is used up, so a typo in the new
# password does not burn the link.
def finish_password_reset(raw_token, new_password, ip_address):
    message = password_error(new_password)
    if message != "":
        return None, (message, 400)

    token_doc = consume_auth_token(raw_token, "reset_password")
    if token_doc is None:
        return None, ("This link is invalid or has expired", 400)

    collection = collection_for_kind(token_doc["user_type"])
    collection.update_one({"_id": token_doc["user_id"], "firm_id": token_doc["firm_id"]},
                          {"$set": {"password_hash": hash_password(new_password)}})
    log_action(token_doc["firm_id"], token_doc["user_id"], token_doc["user_type"],
               "password_reset", target_id=token_doc["user_id"], ip_address=ip_address)
    return {"reset": True}, None
