from flask import Blueprint, g, request

from config import Config
from extensions import limiter
from modules.auth import account_services, services
from utils.decorators import require_auth
from utils.responses import error, success
from utils.validators import clean_text, read_json_body

auth_bp = Blueprint("auth", __name__)


# Turn a service result into the standard JSON reply. Services return either
# (data, None) or (None, (message, status)), so every route stays tiny.
def respond(result, problem, success_status=200):
    if problem is not None:
        return error(problem[0], problem[1])
    return success(result, success_status)


# Create a CA account and their firm, and generate the invite code.
# Limited per IP so nobody can spam-create firms.
@auth_bp.route("/signup-ca", methods=["POST"])
@limiter.limit(Config.SIGNUP_RATE_LIMIT)
def signup_ca():
    result, problem = services.register_ca(read_json_body(), request.remote_addr)
    return respond(result, problem, 201)


# Create a client account with the firm's invite code. It stays pending
# until the CA approves it. The signup limit also slows down anyone trying
# to guess invite codes.
@auth_bp.route("/signup-client", methods=["POST"])
@limiter.limit(Config.SIGNUP_RATE_LIMIT)
def signup_client():
    result, problem = services.register_client(read_json_body(), request.remote_addr)
    return respond(result, problem, 201)


# Show the firm name for an invite code, for the client signup form.
# Same limit as signup, because this is also a way to test guessed codes.
@auth_bp.route("/invite-lookup", methods=["GET"])
@limiter.limit(Config.SIGNUP_RATE_LIMIT)
def invite_lookup():
    result, problem = services.lookup_invite(request.args.get("code", ""))
    return respond(result, problem)


# Log in with email, password and role ("ca" or "client"). Limited to 5
# tries per 15 minutes per IP so passwords cannot be guessed in bulk.
@auth_bp.route("/login", methods=["POST"])
@limiter.limit(Config.LOGIN_RATE_LIMIT)
def login():
    data = read_json_body()
    result, problem = account_services.login_user(data, clean_text(data.get("role")))
    return respond(result, problem)


# Return the current user from the token, for page reloads.
@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    return success(account_services.load_profile(g.user))


# Tokens are stateless, so the real logout is the browser deleting its token.
# This route exists so the frontend has one place to call.
@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    return success({"logged_out": True})


# Confirm an email address using the token from the emailed link.
@auth_bp.route("/verify-email", methods=["POST"])
@limiter.limit(Config.LOGIN_RATE_LIMIT)
def verify_email():
    token = clean_text(read_json_body().get("token"))
    result, problem = account_services.verify_email(token)
    return respond(result, problem)


# Ask for a reset link. The reply is always the same on purpose.
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit(Config.LOGIN_RATE_LIMIT)
def forgot_password():
    email = clean_text(read_json_body().get("email"))
    if email != "":
        account_services.start_password_reset(email)
    return success({"message": "If that email is registered, a reset link has been sent"})


# Set a new password using the token from the reset link.
@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit(Config.LOGIN_RATE_LIMIT)
def reset_password():
    data = read_json_body()
    token = clean_text(data.get("token"))
    new_password = data.get("new_password")
    if token == "" or not isinstance(new_password, str):
        return error("Token and new password are required", 400)
    result, problem = account_services.finish_password_reset(token, new_password, request.remote_addr)
    return respond(result, problem)
