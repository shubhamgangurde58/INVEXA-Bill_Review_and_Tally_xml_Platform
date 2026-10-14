from functools import wraps

from bson import ObjectId
from bson.errors import InvalidId
from flask import g, request

from extensions import db
from utils.jwt_utils import decode_token
from utils.responses import error


# Read "Authorization: Bearer <token>" from the request headers.
def read_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return ""


# Turn a token into a verified user, or None.
# The token alone is not enough: we also check the account still exists in
# the same firm with the same role, so a deleted account stops working
# immediately instead of living on until the token expires.
# A client's status (pending, active, rejected) is read from the database
# here, not from the token, so an approval takes effect at once.
def load_user_from_token(token):
    payload = decode_token(token)
    if payload is None:
        return None

    try:
        user_id = ObjectId(payload["user_id"])
        firm_id = ObjectId(payload["firm_id"])
    except (InvalidId, TypeError):
        return None

    role = payload["role"]
    if role == "client":
        collection = db.clients
    elif role == "ca":
        collection = db.cas
    else:
        return None

    user_doc = collection.find_one({"_id": user_id, "firm_id": firm_id}, {"email": 1, "status": 1})
    if user_doc is None:
        return None

    return {
        "user_id": user_id,
        "firm_id": firm_id,
        "role": role,
        "email": user_doc["email"],
        "status": user_doc.get("status", ""),
    }


# Protect a route: only requests with a valid token get through, and the
# verified user is placed in g.user for the route to use.
def require_auth(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        user = load_user_from_token(read_bearer_token())
        if user is None:
            return error("Authentication required", 401)
        g.user = user
        return view_function(*args, **kwargs)
    return wrapper


# Same as require_auth but also accepts ?token= in the URL. Only file
# routes use it, because <img> and <iframe> tags cannot send headers.
def require_auth_allow_query(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        token = read_bearer_token()
        if token == "":
            token = request.args.get("token", "")
        user = load_user_from_token(token)
        if user is None:
            return error("Authentication required", 401)
        g.user = user
        return view_function(*args, **kwargs)
    return wrapper


# Limit a route to certain roles, for example require_role("ca").
# Use it below @require_auth so g.user is already filled in.
def require_role(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            user = getattr(g, "user", None)
            if user is None:
                return error("Authentication required", 401)
            if user["role"] not in allowed_roles:
                return error("You do not have permission to do this", 403)
            return view_function(*args, **kwargs)
        return wrapper
    return decorator


# Limit a route to clients the CA has approved. A pending client can log in
# and see the waiting screen, but every upload and chat route uses this, so
# they stay locked until approval. Use it below @require_auth.
def require_active_client(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        user = getattr(g, "user", None)
        if user is None:
            return error("Authentication required", 401)
        if user["role"] != "client":
            return error("You do not have permission to do this", 403)
        if user["status"] == "pending":
            return error("Your account is waiting for approval by your CA", 403)
        if user["status"] != "active":
            return error("Your request was not approved", 403)
        return view_function(*args, **kwargs)
    return wrapper


# Allow a CA, or a client who has been approved. Invoice detail and file
# routes use this: the route itself then narrows a client down to their own
# bills. A pending or rejected client is turned away here.
def require_ca_or_active_client(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        user = getattr(g, "user", None)
        if user is None:
            return error("Authentication required", 401)
        if user["role"] == "ca":
            return view_function(*args, **kwargs)
        if user["role"] == "client" and user["status"] == "active":
            return view_function(*args, **kwargs)
        if user["role"] == "client" and user["status"] == "pending":
            return error("Your account is waiting for approval by your CA", 403)
        return error("You do not have permission to do this", 403)
    return wrapper
