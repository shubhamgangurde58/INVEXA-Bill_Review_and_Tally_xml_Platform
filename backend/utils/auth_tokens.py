import hashlib
import secrets
from datetime import timedelta

from config import Config
from extensions import db
from models import utc_now


# Hash a token before saving it. If the database leaks, the saved hashes
# cannot be used as reset links.
def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# Create a one-time token for email verification or password reset.
# Returns the raw token (to put in the link); only its hash is stored.
def create_auth_token(user_id, firm_id, user_type, purpose, valid_hours):
    raw_token = secrets.token_urlsafe(32)
    now = utc_now()
    db.auth_tokens.insert_one({
        "user_id": user_id,
        "firm_id": firm_id,
        "user_type": user_type,
        "purpose": purpose,
        "token_hash": hash_token(raw_token),
        "created_at": now,
        "expires_at": now + timedelta(hours=valid_hours),
        "used_at": None,
    })
    return raw_token


# Check a token and use it up in one step. The single update means two
# clicks at the same moment cannot both succeed. Returns the token record,
# or None if the token is wrong, used or expired.
def consume_auth_token(raw_token, purpose):
    return db.auth_tokens.find_one_and_update(
        {
            "token_hash": hash_token(raw_token),
            "purpose": purpose,
            "used_at": None,
            "expires_at": {"$gt": utc_now()},
        },
        {"$set": {"used_at": utc_now()}},
    )


# Email sending is not built yet, so print the link to the server console.
# This is for local development only; replace it with real email later.
def print_dev_link(label, path, raw_token):
    print("[DEV ONLY] " + label + ": " + Config.FRONTEND_ORIGIN + path + "?token=" + raw_token)
