from flask import Blueprint, g, request

from modules.client import services
from utils.decorators import require_active_client, require_auth, require_role
from utils.responses import respond

client_bp = Blueprint("client", __name__)


# The client's own profile. Open to pending clients so the "waiting for
# approval" screen can show their details.
@client_bp.route("/get-profile", methods=["GET"])
@require_auth
@require_role("client")
def get_profile():
    result, problem = services.get_client_profile(g.user)
    return respond(result, problem)


# The firm and CA this client belongs to. Also open to pending clients.
@client_bp.route("/get-my-firm", methods=["GET"])
@require_auth
@require_role("client")
def get_my_firm():
    result, problem = services.get_my_firm(g.user)
    return respond(result, problem)


# The client's own bills, newest first.
@client_bp.route("/list-my-invoices", methods=["GET"])
@require_auth
@require_active_client
def list_my_invoices():
    result, problem = services.list_my_invoices(g.user, request.args)
    return respond(result, problem)

from modules.client import stats_services

@client_bp.route("/dashboard-stats", methods=["GET"])
@require_auth
@require_role("client")
def dashboard_stats():
    result, problem = stats_services.get_dashboard_stats(g.user)
    return respond(result, problem)

# Upload a new bill (multipart form: file, optional bill_type).
@client_bp.route("/upload-invoice", methods=["POST"])
@require_auth
@require_active_client
def upload_invoice():
    result, problem = services.upload_invoice(g.user, request.files.get("file"), request.form, request.remote_addr)
    return respond(result, problem, 201)


# Upload a new file for a bill the CA asked to be re-uploaded.
@client_bp.route("/reupload-invoice/<invoice_id>", methods=["PUT"])
@require_auth
@require_active_client
def reupload_invoice(invoice_id):
    result, problem = services.reupload_invoice(g.user, invoice_id, request.files.get("file"), request.remote_addr)
    return respond(result, problem)

@client_bp.route("/delete-invoice/<invoice_id>", methods=["DELETE"])
@require_auth
@require_active_client
def delete_invoice(invoice_id):
    result, problem = services.delete_my_invoice(g.user, invoice_id)
    return respond(result, problem)

@client_bp.route("/update-profile", methods=["PUT"])
@require_auth
@require_role("client")
def update_profile():
    data = request.get_json(silent=True) or {}
    result, problem = services.update_client_profile(g.user, data)
    return respond(result, problem)