from extensions import db
from models.notification_models import new_notification_doc


# Save one in-app notification for one recipient.
# Every route that needs to tell someone something (bill uploaded,
# approved, new message) calls this one function, so the document shape
# stays identical everywhere. Pass session when the call is inside a
# transaction so the notification is rolled back with the change.
def create_notification(firm_id, user_id, user_role, ntype, title, body, link_to=None, session=None):
    notification = new_notification_doc(firm_id, user_id, user_role, ntype, title, body, link_to)
    result = db.notifications.insert_one(notification, session=session)
    return result.inserted_id
