"""
Signup and lookup services for both CA and client.

Key rule: register_client does NOT return a session. The client
sits as "pending" until the CA approves them from the dashboard.
This is what makes a leaked invite code useless on its own — the
CA still has to accept each person.
"""

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from extensions import db
from models.tenant_models import new_ca_doc, new_client_doc, new_firm_doc
from modules.auth.helpers import (
    find_firm_by_invite_code, find_user_by_email, make_session, validate_fields,
)
from utils.audit import log_action
from utils.auth_tokens import create_auth_token, print_dev_link
from utils.invite_codes import generate_invite_code
from utils.mailer import send_mail
from utils.notifications import create_notification
from utils.passwords import hash_password
from utils.transactions import run_in_transaction
from utils.validators import clean_text

DUPLICATE_MESSAGE = "An account with these details already exists"
MAX_INVITE_CODE_TRIES = 3
CA_REQUIRED_FIELDS = ["firm_name", "name", "email", "membership_number", "password"]
CLIENT_REQUIRED_FIELDS = ["invite_code", "business_name", "owner_name", "email", "mobile", "password"]


# Send the verification email. Uses the real mailer now, and keeps
# the console print as a fallback for local development.
def send_verification_link(user_id, firm_id, user_type):
    from config import Config
    raw_token = create_auth_token(user_id, firm_id, user_type, "verify_email", 48)
    link = f"{Config.FRONTEND_ORIGIN}/verify-email?token={raw_token}"
    send_mail(
        to="user@invexa.local",
        subject="Verify your INVEXA email",
        body=f"Click this link to verify your account:\n{link}",
    )
    # Kept as a second output so the developer always sees the link.
    print_dev_link("Verify email", "/verify-email", raw_token)


# Save the firm, its CA and the audit row inside one transaction.
# If the CA insert failed alone we would end up with a firm nobody
# can log in to.
def save_firm_and_ca(firm_doc, ca_doc, ip_address):
    def save_all(session):
        db.firms.insert_one(firm_doc, session=session)
        db.cas.insert_one(ca_doc, session=session)
        log_action(firm_doc["_id"], ca_doc["_id"], "ca", "firm_created", firm_doc["_id"],
                   {"firm_name": firm_doc["name"]}, ip_address, session=session)
    run_in_transaction(save_all)


# Build the firm with a fresh invite code and save it with its CA.
# Retries on the very rare invite-code collision; other duplicate
# keys (email) bubble up to the caller.
def create_firm_with_ca(data, firm_id, ca_doc, ip_address):
    for _ in range(MAX_INVITE_CODE_TRIES):
        invite_code = generate_invite_code(data["firm_name"])
        firm_doc = new_firm_doc(
            data["firm_name"], clean_text(data.get("gstin")), clean_text(data.get("address")),
            invite_code, ca_doc["_id"], firm_id=firm_id,
        )
        try:
            save_firm_and_ca(firm_doc, ca_doc, ip_address)
            return firm_doc
        except DuplicateKeyError:
            if db.firms.find_one({"invite_code": invite_code}, {"_id": 1}) is None:
                raise
    raise RuntimeError("Could not create a unique invite code")


# Sign up a CA. Creates the firm in the same transaction so the two
# rows can never disagree. Returns a session token because a CA is
# active immediately.
def register_ca(data, ip_address):
    problem = validate_fields(data, CA_REQUIRED_FIELDS)
    if problem is not None:
        return None, problem

    email = data["email"].strip().lower()
    if find_user_by_email(email)[0] is not None:
        return None, (DUPLICATE_MESSAGE, 409)

    firm_id = ObjectId()
    ca_doc = new_ca_doc(firm_id, data["name"], email, hash_password(data["password"]),
                        data["membership_number"], ca_id=ObjectId())
    try:
        firm_doc = create_firm_with_ca(data, firm_id, ca_doc, ip_address)
    except DuplicateKeyError:
        return None, (DUPLICATE_MESSAGE, 409)

    send_verification_link(ca_doc["_id"], firm_id, "ca")
    return make_session(ca_doc, "ca", firm_doc), None


# Save a pending client + the audit row + a "client_joined"
# notification for the CA, all inside one transaction.
def save_client_and_notify(client_doc, firm_doc, ip_address):
    def save_all(session):
        result = db.clients.insert_one(client_doc, session=session)
        log_action(firm_doc["_id"], result.inserted_id, "client", "client_signup_requested",
                   result.inserted_id, {"business_name": client_doc["business_name"]},
                   ip_address, session=session)
        create_notification(
            firm_doc["_id"], firm_doc["owner_ca_id"], "ca", "client_joined",
            "New client request", client_doc["business_name"] + " wants to join your firm.",
            "/ca/clients", session=session,
        )
    run_in_transaction(save_all)


# Sign up a shop owner with the firm's invite code.
# The account starts as "pending" and NO session token is issued.
# The client must come back after the CA approves them.
def register_client(data, ip_address):
    problem = validate_fields(data, CLIENT_REQUIRED_FIELDS)
    if problem is not None:
        return None, problem

    firm_doc = find_firm_by_invite_code(data["invite_code"])
    if firm_doc is None:
        return None, ("Invalid invite code", 400)

    email = data["email"].strip().lower()
    if find_user_by_email(email)[0] is not None:
        return None, (DUPLICATE_MESSAGE, 409)

    client_doc = new_client_doc(
        firm_doc["_id"], data["business_name"], data["owner_name"], email,
        clean_text(data.get("gstin")), data["mobile"], clean_text(data.get("address")),
        hash_password(data["password"]),
    )
    try:
        save_client_and_notify(client_doc, firm_doc, ip_address)
    except DuplicateKeyError:
        return None, (DUPLICATE_MESSAGE, 409)

    send_verification_link(client_doc["_id"], firm_doc["_id"], "client")

    # No session. The frontend shows a "waiting for approval" screen.
    return {
        "pending": True,
        "firm_name": firm_doc["name"],
    }, None


# Public lookup for the client signup form. Returns only the firm
# name so an attacker cannot learn anything else by guessing codes.
def lookup_invite(code):
    firm_doc = find_firm_by_invite_code(code)
    if firm_doc is None:
        return None, ("Invalid invite code", 404)
    return {"firm_name": firm_doc["name"]}, None