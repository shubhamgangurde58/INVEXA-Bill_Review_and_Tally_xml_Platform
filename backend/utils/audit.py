from extensions import db
from models import utc_now


# Write one row to audit_logs for a mutation (approve, reject, update,
# delete, assign). Auditors use this trail to see who changed what and
# when. Never put passwords, tokens or full request bodies in details.
# Pass session when the call happens inside a transaction so the log
# is committed or rolled back together with the change itself.
def log_action(firm_id, actor_id, actor_role, action, target_id=None, details=None, ip_address=None, session=None):
    if details is None:
        details = {}

    entry = {
        "firm_id": firm_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "target_id": target_id,
        "details": details,
        "ip_address": ip_address,
        "timestamp": utc_now(),
    }
    db.audit_logs.insert_one(entry, session=session)
