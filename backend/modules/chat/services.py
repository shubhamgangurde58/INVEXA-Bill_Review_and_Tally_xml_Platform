"""
Chat business logic. One thread per (firm, client) pair. Unread
counters live on the thread so the inbox never has to count
messages on every poll.

This version adds file uploads and bill sharing. Both build on the
existing _insert_message helper so notifications and thread
counters stay consistent.
"""

from bson import ObjectId
from bson.errors import InvalidId

from extensions import db, fs
from models import utc_now
from models.chat_models import new_message_doc, new_thread_doc
from utils.notifications import create_notification
from utils.serializers import to_iso
from utils.uploads import read_upload

MAX_MESSAGE_LENGTH = 2000


# Find a client's thread, creating it the first time if needed.
def find_or_create_client_thread(user):
    firm_id = user["firm_id"]
    client_id = user["user_id"]

    thread = db.chat_threads.find_one({"firm_id": firm_id, "client_id": client_id})
    if thread is None:
        doc = new_thread_doc(firm_id, client_id)
        result = db.chat_threads.insert_one(doc)
        thread = {**doc, "_id": result.inserted_id}
    return thread


# JSON shape the frontend expects for one message.
def serialize_message(m):
    return {
        "id": str(m["_id"]),
        "sender_id": str(m["sender_id"]),
        "sender_role": m["sender_role"],
        "message_type": m.get("message_type", "text"),
        "content": m.get("content", ""),
        "file_id": str(m["file_id"]) if m.get("file_id") else None,
        "invoice_id": str(m["invoice_id"]) if m.get("invoice_id") else None,
        "created_at": to_iso(m.get("created_at")),
        "read_at": to_iso(m.get("read_at")),
    }


# Client side: my thread plus its messages. Marks CA-sent
# messages as read at the same time.
def get_my_thread(user):
    if user["role"] != "client":
        return None, ("Only clients use this endpoint", 403)

    thread = find_or_create_client_thread(user)
    messages = db.chat_messages.find({"thread_id": thread["_id"]}) \
        .sort("created_at", 1).limit(200)

    db.chat_threads.update_one(
        {"_id": thread["_id"]},
        {"$set": {"unread_count_client": 0}},
    )

    return {
        "thread": {
            "id": str(thread["_id"]),
            "client_id": str(thread["client_id"]),
        },
        "messages": [serialize_message(m) for m in messages],
    }, None


# CA side: every thread in the firm with the last message preview
# and an unread badge.
def list_ca_threads(user):
    threads = db.chat_threads.find({"firm_id": user["firm_id"]}) \
        .sort("last_message_at", -1).limit(100)

    rows = []
    for t in threads:
        client = db.clients.find_one(
            {"_id": t["client_id"]},
            {"business_name": 1, "owner_name": 1},
        )
        last = db.chat_messages.find_one(
            {"thread_id": t["_id"]},
            sort=[("created_at", -1)],
            projection={"content": 1, "created_at": 1, "sender_role": 1},
        )
        rows.append({
            "thread_id": str(t["_id"]),
            "client_id": str(t["client_id"]),
            "business_name": client["business_name"] if client else "Client",
            "owner_name": client["owner_name"] if client else "",
            "last_message": last["content"] if last else "",
            "last_message_at": to_iso(last["created_at"]) if last else "",
            "unread_count": t.get("unread_count_ca", 0),
        })
    return {"threads": rows}, None


# Read a thread's messages. Either side can call for a thread they
# belong to. Clears their own unread counter.
def get_thread_messages(user, raw_thread_id):
    try:
        thread_id = ObjectId(raw_thread_id)
    except (InvalidId, TypeError):
        return None, ("Thread not found", 404)

    thread = db.chat_threads.find_one({"_id": thread_id, "firm_id": user["firm_id"]})
    if thread is None:
        return None, ("Thread not found", 404)

    if user["role"] == "client" and thread["client_id"] != user["user_id"]:
        return None, ("Thread not found", 404)

    messages = db.chat_messages.find({"thread_id": thread_id}) \
        .sort("created_at", 1).limit(200)

    counter = "unread_count_ca" if user["role"] == "ca" else "unread_count_client"
    db.chat_threads.update_one({"_id": thread_id}, {"$set": {counter: 0}})

    return {"messages": [serialize_message(m) for m in messages]}, None


# Shared write path. Validates the message, inserts it, updates the
# thread counters, and fires a notification for the other side.
def _insert_message(thread, sender, payload):
    content = (payload.get("content") or "").strip()
    if not content:
        return None, ("Message cannot be empty", 400)
    if len(content) > MAX_MESSAGE_LENGTH:
        return None, (f"Message too long (max {MAX_MESSAGE_LENGTH} characters)", 400)

    message_type = payload.get("message_type") or "text"
    if message_type not in ("text", "file", "bill"):
        message_type = "text"

    now = utc_now()
    doc = new_message_doc(
        thread["_id"], sender["user_id"], sender["role"],
        message_type, content,
        file_id=payload.get("file_id"),
        invoice_id=payload.get("invoice_id"),
        created_at=now,
    )
    result = db.chat_messages.insert_one(doc)

    counter = "unread_count_ca" if sender["role"] == "client" else "unread_count_client"
    db.chat_threads.update_one(
        {"_id": thread["_id"]},
        {"$set": {"last_message_at": now}, "$inc": {counter: 1}},
    )

    firm = db.firms.find_one({"_id": thread["firm_id"]}, {"owner_ca_id": 1})
    if sender["role"] == "client":
        recipient_id = firm["owner_ca_id"]
        recipient_role = "ca"
        link = "/ca/chat"
    else:
        recipient_id = thread["client_id"]
        recipient_role = "client"
        link = "/client/chat"

    create_notification(
        thread["firm_id"], recipient_id, recipient_role,
        "new_message", "New message", content[:120], link,
    )

    return {"message": serialize_message({**doc, "_id": result.inserted_id})}, None


# Client sends to their own thread.
def send_message(user, payload):
    if user["role"] == "client":
        thread = find_or_create_client_thread(user)
        return _insert_message(thread, user, payload)
    return None, ("Use /chat/send-to/<client_id> as a CA", 400)


# CA sends to a specific client's thread.
def send_message_to_client(user, raw_client_id, payload):
    try:
        client_id = ObjectId(raw_client_id)
    except (InvalidId, TypeError):
        return None, ("Client not found", 404)

    client = db.clients.find_one({"_id": client_id, "firm_id": user["firm_id"]})
    if client is None:
        return None, ("Client not found", 404)

    thread = db.chat_threads.find_one({"firm_id": user["firm_id"], "client_id": client_id})
    if thread is None:
        doc = new_thread_doc(user["firm_id"], client_id)
        result = db.chat_threads.insert_one(doc)
        thread = {**doc, "_id": result.inserted_id}

    return _insert_message(thread, user, payload)


# Upload a file into the conversation. Stored in GridFS with the
# firm and client tagged so another firm can never fetch it.
# Clients upload to their own thread; the CA passes client_id.
def upload_chat_file(user, file_storage, raw_client_id=None):
    upload, problem = read_upload(file_storage)
    if problem is not None:
        return None, problem

    if user["role"] == "client":
        thread = find_or_create_client_thread(user)
    else:
        try:
            client_id = ObjectId(raw_client_id)
        except (InvalidId, TypeError):
            return None, ("Pick a client first", 400)
        client = db.clients.find_one({"_id": client_id, "firm_id": user["firm_id"]})
        if client is None:
            return None, ("Client not found", 404)
        thread = db.chat_threads.find_one({"firm_id": user["firm_id"], "client_id": client_id})
        if thread is None:
            doc = new_thread_doc(user["firm_id"], client_id)
            result = db.chat_threads.insert_one(doc)
            thread = {**doc, "_id": result.inserted_id}

    file_id = fs.put(
        upload["data"],
        filename=upload["file_name"],
        content_type=upload["mime_type"],
        firm_id=user["firm_id"],
        client_id=thread["client_id"],
        thread_id=thread["_id"],
    )

    payload = {
        "content": upload["file_name"],
        "message_type": "file",
        "file_id": file_id,
    }
    return _insert_message(thread, user, payload)


# Share a bill into the conversation. The message carries the
# invoice_id so the frontend can render a small card with the
# invoice number and current status.
def share_bill(user, payload):
    raw_invoice_id = payload.get("invoice_id")
    if not raw_invoice_id:
        return None, ("Pick a bill first", 400)

    try:
        invoice_id = ObjectId(raw_invoice_id)
    except (InvalidId, TypeError):
        return None, ("Bill not found", 404)

    invoice = db.invoices.find_one({"_id": invoice_id, "firm_id": user["firm_id"]})
    if invoice is None:
        return None, ("Bill not found", 404)

    if user["role"] == "client":
        if invoice["client_id"] != user["user_id"]:
            return None, ("Bill not found", 404)
        thread = find_or_create_client_thread(user)
    else:
        raw_client_id = payload.get("client_id")
        try:
            client_id = ObjectId(raw_client_id)
        except (InvalidId, TypeError):
            return None, ("Pick a client first", 400)
        thread = db.chat_threads.find_one({"firm_id": user["firm_id"], "client_id": client_id})
        if thread is None:
            doc = new_thread_doc(user["firm_id"], client_id)
            result = db.chat_threads.insert_one(doc)
            thread = {**doc, "_id": result.inserted_id}

    number = invoice.get("invoice_number") or invoice["file_name"]
    message_payload = {
        "content": f"Bill {number}",
        "message_type": "bill",
        "invoice_id": invoice_id,
    }
    return _insert_message(thread, user, message_payload)