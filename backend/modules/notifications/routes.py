from flask import Blueprint, g, request
from extensions import db
from utils.decorators import require_auth
from utils.responses import success
from utils.serializers import to_iso

# Notification endpoints. Every query is scoped to the logged-in user,
# so nobody can read another user's notifications.

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/list", methods=["GET"])
@require_auth
def list_notifications():
    # Only the current user's notifications, newest first. Limit 50 to
    # keep the payload small — the page can paginate later.
    cursor = db.notifications.find({"user_id": g.user["user_id"]}) \
        .sort("created_at", -1).limit(50)

    rows = []
    for n in cursor:
        rows.append({
            "id": str(n["_id"]),
            "type": n["type"],
            "title": n["title"],
            "body": n["body"],
            "link_to": n.get("link_to"),
            "is_read": n.get("is_read", False),
            "created_at": to_iso(n.get("created_at")),
        })
    return success({"notifications": rows})


@notifications_bp.route("/unread-count", methods=["GET"])
@require_auth
def unread_count():
    count = db.notifications.count_documents({
        "user_id": g.user["user_id"],
        "is_read": False,
    })
    return success({"count": count})


@notifications_bp.route("/mark-all-read", methods=["PUT"])
@require_auth
def mark_all_read():
    db.notifications.update_many(
        {"user_id": g.user["user_id"]},
        {"$set": {"is_read": True}},
    )
    return success({"ok": True})


@notifications_bp.route("/mark-read/<nid>", methods=["PUT"])
@require_auth
def mark_read(nid):
    from bson import ObjectId
    try:
        _id = ObjectId(nid)
    except Exception:
        return success({"ok": False})
    db.notifications.update_one(
        {"_id": _id, "user_id": g.user["user_id"]},
        {"$set": {"is_read": True}},
    )
    return success({"ok": True})