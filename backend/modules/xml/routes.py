"""HTTP endpoints for Tally XML. Single file per bill."""

import io

from flask import Blueprint, g, send_file

from extensions import db, fs
from modules.xml.tally_builder import build_tally_xml, XmlBuildError
from utils.decorators import require_auth_allow_query, require_role
from utils.responses import error, success
from utils.validators import to_object_id

xml_bp = Blueprint("xml", __name__)


def _find_visible_bill(user, raw_id):
    invoice_id = to_object_id(raw_id)
    if invoice_id is None:
        return None
    q = {"_id": invoice_id, "firm_id": user["firm_id"]}
    if user["role"] == "client":
        q["client_id"] = user["user_id"]
    return db.invoices.find_one(q)


def _filename(invoice):
    number = invoice.get("invoice_number") or str(invoice["_id"])
    safe = "".join(c for c in str(number) if c.isalnum() or c in "-_")
    return f"INVEXA_{safe}.xml"


@xml_bp.route("/download/<invoice_id>", methods=["GET"])
@require_auth_allow_query
def download(invoice_id):
    bill = _find_visible_bill(g.user, invoice_id)
    if bill is None:
        return error("Bill not found", 404)
    if bill["status"] != "approved":
        return error("Only approved bills can be exported", 400)

    data_bytes = None

    if bill.get("xml_file_id"):
        try:
            stored = fs.get(bill["xml_file_id"])
            data_bytes = stored.read()
        except Exception:
            data_bytes = None

    if data_bytes is None:
        firm = db.firms.find_one({"_id": g.user["firm_id"]})
        try:
            xml_text = build_tally_xml(firm, bill)
            data_bytes = xml_text.encode("utf-8")
        except XmlBuildError as e:
            return error(str(e), 400)

        file_id = fs.put(
            data_bytes,
            filename=_filename(bill),
            content_type="application/xml",
            firm_id=bill["firm_id"],
            client_id=bill["client_id"],
            invoice_id=bill["_id"],
            kind="xml_voucher",
        )
        db.invoices.update_one(
            {"_id": bill["_id"]},
            {"$set": {"xml_file_id": file_id}},
        )

    buf = io.BytesIO(data_bytes)
    return send_file(
        buf,
        mimetype="application/xml",
        as_attachment=True,
        download_name=_filename(bill),
    )


@xml_bp.route("/preview/<invoice_id>", methods=["GET"])
@require_auth_allow_query
@require_role("ca")
def preview(invoice_id):
    bill = _find_visible_bill(g.user, invoice_id)
    if bill is None:
        return error("Bill not found", 404)
    firm = db.firms.find_one({"_id": g.user["firm_id"]})
    return success({"xml": build_tally_xml(firm, bill)})