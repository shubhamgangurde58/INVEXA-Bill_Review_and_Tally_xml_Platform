import re

from dotenv import load_dotenv
from pymongo.errors import OperationFailure

from extensions import db
from seed_helpers import DEMO_EMAIL_PATTERN, delete_demo_data, delete_empty_demo_firms

LEGACY_COLLECTIONS = ["ca_users", "client_ca_assignment"]


# List which of the old v1 collections are still in the database.
# If none are left, the cleanup has already been done.
def find_legacy_collections():
    existing = set(db.list_collection_names())
    found = []
    for name in LEGACY_COLLECTIONS:
        if name in existing:
            found.append(name)
    return found


# Check whether ca_users holds anything that is not demo data.
# We only ever seeded demo users into it, so a real-looking email means
# something unexpected happened and we must stop before dropping it.
def has_real_ca_users():
    if "ca_users" not in db.list_collection_names():
        return False

    for ca in db.ca_users.find({}, {"email": 1}):
        email = ca.get("email", "")
        if re.search(DEMO_EMAIL_PATTERN, email) is None:
            return True
    return False


# Collect the ids and firm ids of the old demo CAs before the
# collection is dropped, so their audit logs and firms can be removed.
def read_old_ca_ids():
    old_ca_ids = []
    old_firm_ids = set()
    if "ca_users" not in db.list_collection_names():
        return old_ca_ids, old_firm_ids

    for ca in db.ca_users.find({}, {"firm_id": 1}):
        old_ca_ids.append(ca["_id"])
        old_firm_ids.add(ca["firm_id"])
    return old_ca_ids, old_firm_ids


# Remove the single-field clients index from v1.
# v2 uses the compound firm_id + status index instead, so the old one
# is redundant. A missing index is fine and is ignored.
def drop_old_client_index():
    try:
        db.clients.drop_index("clients_by_firm")
    except OperationFailure:
        pass


# Entry point: drop the v1 collections and every piece of v1 demo data,
# but only after confirming that nothing real is stored in them.
def main():
    load_dotenv()
    legacy = find_legacy_collections()
    if len(legacy) == 0:
        print("Nothing to clean. No v1 collections found.")
        return

    if has_real_ca_users():
        print("ca_users contains non-demo accounts. Nothing was changed.")
        return

    old_ca_ids, old_firm_ids = read_old_ca_ids()
    db.audit_logs.delete_many({"actor_id": {"$in": old_ca_ids}})

    for name in legacy:
        db.drop_collection(name)
        print("Dropped collection: " + name)

    drop_old_client_index()
    delete_demo_data()
    delete_empty_demo_firms(old_firm_ids)
    print("Cleanup finished. Now run: python seed_demo.py")


if __name__ == "__main__":
    main()
