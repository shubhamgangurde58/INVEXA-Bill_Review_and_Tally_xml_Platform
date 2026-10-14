"""
Chat HTTP endpoints.

Client side: one thread, always with the firm's CA.
CA side: one thread per client of the firm.

New in this version: file upload and share-a-bill, both stored as
messages so both sides see them in the same timeline.
"""

from flask import Blueprint, g, request

from extensions import limiter
from modules.chat import services
from utils.decorators import require_active_client, require_auth, require_role
from utils.responses import respond

chat_bp = Blueprint("chat", __name__)


# Client's own thread plus the messages. Creates the thread on the
# first call if it does not exist yet.
@chat_bp.route("/my-thread", methods=["GET"])
@require_auth
@require_role("client")
def my_thread():
    result, problem = services.get_my_thread(g.user)
    return respond(result, problem)


# CA sees a list of every thread in their firm with an unread badge.
@chat_bp.route("/threads", methods=["GET"])
@require_auth
@require_role("ca")
def threads():
    result, problem = services.list_ca_threads(g.user)
    return respond(result, problem)


# Read one thread's messages. Either side can call this for a
# thread they belong to.
@chat_bp.route("/thread/<thread_id>", methods=["GET"])
@require_auth
def thread_messages(thread_id):
    result, problem = services.get_thread_messages(g.user, thread_id)
    return respond(result, problem)


# Client sends a text message. Limited to prevent spam.
@chat_bp.route("/send", methods=["POST"])
@require_auth
@require_active_client
@limiter.limit("60 per minute")
def send():
    payload = request.get_json(silent=True) or {}
    result, problem = services.send_message(g.user, payload)
    return respond(result, problem)


# CA sends a text message to a specific client.
@chat_bp.route("/send-to/<client_id>", methods=["POST"])
@require_auth
@require_role("ca")
@limiter.limit("60 per minute")
def send_to_client(client_id):
    payload = request.get_json(silent=True) or {}
    result, problem = services.send_message_to_client(g.user, client_id, payload)
    return respond(result, problem)


# Upload a file. Client uploads to their own thread; the CA must
# pass the client_id they are messaging.
@chat_bp.route("/upload", methods=["POST"])
@require_auth
@require_active_client
@limiter.limit("20 per minute")
def upload_file():
    file_storage = request.files.get("file")
    client_id = request.form.get("client_id")  # only used when the CA uploads
    result, problem = services.upload_chat_file(g.user, file_storage, client_id)
    return respond(result, problem, 201)


# Share a bill into the conversation. Both sides can do this; the
# CA passes client_id, the client does not.
@chat_bp.route("/share-bill", methods=["POST"])
@require_auth
@require_active_client
def share_bill():
    payload = request.get_json(silent=True) or {}
    result, problem = services.share_bill(g.user, payload)
    return respond(result, problem, 201)