import io

from flask import Blueprint, g, request, send_file

from modules.invoice import services
from utils.decorators import (
    require_auth, require_auth_allow_query, require_ca_or_active_client, require_role,
)
from utils.responses import error, respond

invoice_bp = Blueprint("invoice", __name__)


# List every bill of the CA's firm (filters: status, client_id, page).
@invoice_bp.route("/list-firm-invoices", methods=["GET"])
@require_auth
@require_role("ca")
def list_firm_invoices():
    result, problem = services.list_firm_invoices(g.user, request.args)
    return respond(result, problem)


# One bill. A CA can open any bill of the firm; a client only their own.
@invoice_bp.route("/get-by-id/<invoice_id>", methods=["GET"])
@require_auth
@require_ca_or_active_client
def get_by_id(invoice_id):
    result, problem = services.get_invoice(g.user, invoice_id)
    return respond(result, problem)


# The bill's picture or PDF. This is the only route that accepts ?token= in
# the URL, because <img> and <iframe> tags cannot send headers. The reply is
# marked private and "nosniff" so browsers do not cache it or guess its type.
@invoice_bp.route("/get-file/<invoice_id>", methods=["GET"])
@require_auth_allow_query
@require_ca_or_active_client
def get_file(invoice_id):
    result, problem = services.load_invoice_file(g.user, invoice_id)
    if problem is not None:
        return error(problem[0], problem[1])

    data, mime_type, file_name = result
    response = send_file(io.BytesIO(data), mimetype=mime_type, download_name=file_name, as_attachment=False)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response
