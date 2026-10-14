from datetime import datetime, timedelta, timezone

import jwt

from config import Config


# Build the login token. It carries who the user is, their role and their
# firm, so every route can scope data without trusting anything the browser
# sends in the request body. It expires after 24 hours.
def create_token(user_id, role, firm_id, email):
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id),
        "role": role,
        "firm_id": str(firm_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=Config.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


# Read a token back. Returns the payload, or None if the token is fake,
# tampered with or expired. Pinning the algorithm stops "alg: none" tricks.
def decode_token(token):
    try:
        return jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "user_id", "role", "firm_id"]},
        )
    except jwt.InvalidTokenError:
        return None
