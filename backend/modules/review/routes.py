"""
HTTP endpoints for the review queue. Every route is CA-only and
scoped to the CA's firm via the JWT. Business logic lives in
services.py; these functions only parse the request, call a
service, and return the standard JSON envelope.

The /ocr-status route is new: it tells the frontend whether
Tesseract is actually usable, so the CA sees a real warning
instead of a fake "OCR complete" toast.
"""

from flask import Blueprint, g, request

from extensions import db, limiter
from modules.review import services
from modules.review.ocr import ocr_status
from utils.decorators import require_auth, require_role
from utils.responses import respond, success

review_bp = Blueprint("review", __name__)


# Status endpoint the modal calls before offering the Extract
# button. Tells the truth: is OCR going to work or not.
@review_bp.route("/ocr-status", methods=["GET"])
@require_auth
@require_role("ca")
def get_ocr_status():
    return success(ocr_status())


# Ask OCR to read the bill again. Rate-limited because each call
# spins up Tesseract and takes a couple of seconds.
@review_bp.route("/reextract/<invoice_id>", methods=["POST"])
@require_auth
@require_role("ca")
@limiter.limit("30 per minute")
def reextract(invoice_id):
    result, problem = services.run_ocr_for_bill(g.user, invoice_id)
    return respond(result, problem)


# Save the CA's manual edits to the OCR fields.
@review_bp.route("/update-ocr/<invoice_id>", methods=["PUT"])
@require_auth
@require_role("ca")
def update_ocr(invoice_id):
    payload = request.get_json(silent=True) or {}
    result, problem = services.save_ocr(g.user, invoice_id, payload)
    return respond(result, problem)


# Approve the bill and return the download URL for the XML.
@review_bp.route("/approve/<invoice_id>", methods=["PUT"])
@require_auth
@require_role("ca")
def approve(invoice_id):
    payload = request.get_json(silent=True) or {}
    result, problem = services.approve_bill(g.user, invoice_id, payload)
    return respond(result, problem)


# Reject with a mandatory reason the client will see.
@review_bp.route("/reject/<invoice_id>", methods=["PUT"])
@require_auth
@require_role("ca")
def reject(invoice_id):
    payload = request.get_json(silent=True) or {}
    result, problem = services.reject_bill(g.user, invoice_id, payload)
    return respond(result, problem)


# Ask the client for a clearer photo.
@review_bp.route("/request-reupload/<invoice_id>", methods=["PUT"])
@require_auth
@require_role("ca")
def request_reupload(invoice_id):
    payload = request.get_json(silent=True) or {}
    result, problem = services.request_reupload(g.user, invoice_id, payload)
    return respond(result, problem)


# Mark a bill as imported to Tally after a successful manual
# import. Closes the loop so the CA knows which bills are done.
@review_bp.route("/mark-imported/<invoice_id>", methods=["PUT"])
@require_auth
@require_role("ca")
def mark_imported(invoice_id):
    result, problem = services.mark_imported(g.user, invoice_id)
    return respond(result, problem)


# Numbers for the four dashboard tiles. Counted in MongoDB so we
# never download every bill just to display a total.
@review_bp.route("/stats", methods=["GET"])
@require_auth
@require_role("ca")
def stats():
    pipeline = [
        {"$match": {"firm_id": g.user["firm_id"]}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = list(db.invoices.aggregate(pipeline))
    counts = {row["_id"]: row["count"] for row in rows}

    return respond({
        "pending":  counts.get("uploaded", 0) + counts.get("pending_review", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "total":    sum(counts.values()),
    }, None)