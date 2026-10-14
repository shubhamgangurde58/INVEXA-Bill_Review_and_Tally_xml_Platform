from models import utc_now

USER_ROLES = ["ca", "client"]
NOTIFICATION_TYPES = [
    "bill_uploaded",
    "bill_approved",
    "bill_rejected",
    "reupload_requested",
    "new_message",
    "client_joined",
    "client_approved",
    "client_rejected",
]


# Build one notifications document for a single recipient.
# The type list is checked here so a typo in a route fails loudly in
# development instead of creating a notification the bell cannot show.
# link_to is the frontend page opened when the user clicks it.
def new_notification_doc(firm_id, user_id, user_role, ntype, title, body, link_to=None):
    if user_role not in USER_ROLES:
        raise ValueError("user_role must be one of: " + ", ".join(USER_ROLES))
    if ntype not in NOTIFICATION_TYPES:
        raise ValueError("type must be one of: " + ", ".join(NOTIFICATION_TYPES))

    return {
        "firm_id": firm_id,
        "user_id": user_id,
        "user_role": user_role,
        "type": ntype,
        "title": title,
        "body": body,
        "link_to": link_to,
        "is_read": False,
        "created_at": utc_now(),
    }
