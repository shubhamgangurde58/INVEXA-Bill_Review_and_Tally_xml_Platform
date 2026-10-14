from models import utc_now

SENDER_ROLES = ["ca", "client"]
MESSAGE_TYPES = ["text", "image", "file", "bill"]


# Build one chat_threads document.
# There is one thread per client inside a firm (enforced by a unique
# index). There is no ca_id because the CA of a thread is always the
# firm's owner_ca_id. The unread counters let the thread list show
# badges without counting messages on every poll.
def new_thread_doc(firm_id, client_id):
    return {
        "firm_id": firm_id,
        "client_id": client_id,
        "last_message_at": None,
        "unread_count_ca": 0,
        "unread_count_client": 0,
    }


# Build one chat_messages document.
# file_id points to GridFS for image and file messages. invoice_id is
# used only by "bill" messages (the "Share to CA" and "Ask Client"
# buttons), so the chat can show the bill name and a thumbnail.
# created_at can be passed in so the seed script can create believable
# older conversations.
def new_message_doc(thread_id, sender_id, sender_role, message_type, content, file_id=None, created_at=None, read_at=None, invoice_id=None):
    if sender_role not in SENDER_ROLES:
        raise ValueError("sender_role must be one of: " + ", ".join(SENDER_ROLES))
    if message_type not in MESSAGE_TYPES:
        raise ValueError("message_type must be one of: " + ", ".join(MESSAGE_TYPES))
    if message_type == "bill" and invoice_id is None:
        raise ValueError("a bill message needs an invoice_id")

    if created_at is None:
        created_at = utc_now()

    return {
        "thread_id": thread_id,
        "sender_id": sender_id,
        "sender_role": sender_role,
        "message_type": message_type,
        "content": content,
        "file_id": file_id,
        "invoice_id": invoice_id,
        "created_at": created_at,
        "read_at": read_at,
    }
