from flask import Blueprint, g, request

from modules.firm import services, settings_services
from utils.decorators import require_auth, require_role
from utils.responses import respond
from utils.validators import read_json_body

firm_bp = Blueprint("firm", __name__)


# Show the CA's firm profile, invite code and counters.
@firm_bp.route("/get-profile", methods=["GET"])
@require_auth
@require_role("ca")
def get_profile():
    result, problem = settings_services.get_firm_profile(g.user["firm_id"])
    return respond(result, problem)


# Change the firm's name, GSTIN, address or Tally settings.
@firm_bp.route("/update-profile", methods=["PUT"])
@require_auth
@require_role("ca")
def update_profile():
    result, problem = settings_services.update_firm_profile(g.user, read_json_body(), request.remote_addr)
    return respond(result, problem)


# Replace the invite code. The old one stops working immediately.
@firm_bp.route("/regenerate-invite-code", methods=["POST"])
@require_auth
@require_role("ca")
def regenerate_invite_code():
    result, problem = services.regenerate_invite_code(g.user, request.remote_addr)
    return respond(result, problem)


# List the firm's approved clients.
@firm_bp.route("/list-clients", methods=["GET"])
@require_auth
@require_role("ca")
def list_clients():
    status = request.args.get("status", "active")
    result, problem = services.list_clients(g.user["firm_id"], status, ["active"])
    return respond(result, problem)


# List join requests: ?status=pending (default) or ?status=rejected.
@firm_bp.route("/list-join-requests", methods=["GET"])
@require_auth
@require_role("ca")
def list_join_requests():
    status = request.args.get("status", "pending")
    result, problem = services.list_clients(g.user["firm_id"], status, ["pending", "rejected"])
    return respond(result, problem)


# Approve a pending (or earlier rejected) client.
@firm_bp.route("/approve-client/<client_id>", methods=["POST"])
@require_auth
@require_role("ca")
def approve_client(client_id):
    result, problem = services.decide_client(g.user, client_id, True, request.remote_addr)
    return respond(result, problem)


# Reject a pending client.
@firm_bp.route("/reject-client/<client_id>", methods=["POST"])
@require_auth
@require_role("ca")
def reject_client(client_id):
    result, problem = services.decide_client(g.user, client_id, False, request.remote_addr)
    return respond(result, problem)
