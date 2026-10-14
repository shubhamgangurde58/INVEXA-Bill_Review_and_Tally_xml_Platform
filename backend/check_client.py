# Wipe every firm/client/invoice/chat EXCEPT:
#   CA:     monica@gmail.com      (firm "Monika && monica")
#   Client: punam@gmail.com       (belongs to that firm)
# Run once. Everything else is removed.
from extensions import db, fs

KEEP_CA_EMAIL = "monica@gmail.com"
KEEP_CLIENT_EMAIL = "punam@gmail.com"

# Find the CA we want to keep.
keep_ca = db.cas.find_one({"email": KEEP_CA_EMAIL})
if not keep_ca:
    print(f"No CA found with email {KEEP_CA_EMAIL}")
    raise SystemExit(1)

keep_firm_id = keep_ca["firm_id"]
print(f"Keeping firm: {keep_firm_id}")

# Find the client we want to keep (must be in the same firm).
keep_client = db.clients.find_one({
    "email": KEEP_CLIENT_EMAIL,
    "firm_id": keep_firm_id,
})
if not keep_client:
    print(f"No client found with email {KEEP_CLIENT_EMAIL} in that firm")
    raise SystemExit(1)

keep_client_id = keep_client["_id"]
print(f"Keeping client: {keep_client_id}")

# ----- Delete everything else -----

# 1. Invoices from other firms + their GridFS files.
other_invoices = db.invoices.find({"firm_id": {"$ne": keep_firm_id}})
inv_count = 0
for inv in other_invoices:
    try:
        fs.delete(inv["file_id"])
    except Exception:
        pass
    inv_count += 1
db.invoices.delete_many({"firm_id": {"$ne": keep_firm_id}})
print(f"Deleted {inv_count} invoices from other firms")

# 2. Invoices from other clients in the kept firm (defensive — none should exist).
extra = db.invoices.find({"firm_id": keep_firm_id, "client_id": {"$ne": keep_client_id}})
extra_count = 0
for inv in extra:
    try:
        fs.delete(inv["file_id"])
    except Exception:
        pass
    extra_count += 1
db.invoices.delete_many({"firm_id": keep_firm_id, "client_id": {"$ne": keep_client_id}})
print(f"Deleted {extra_count} other invoices from the kept firm")

# 3. Chat threads + messages from other firms.
other_threads = list(db.chat_threads.find({"firm_id": {"$ne": keep_firm_id}}, {"_id": 1}))
other_thread_ids = [t["_id"] for t in other_threads]
db.chat_messages.delete_many({"thread_id": {"$in": other_thread_ids}})
db.chat_threads.delete_many({"firm_id": {"$ne": keep_firm_id}})
print(f"Deleted {len(other_thread_ids)} chat threads from other firms")

# 4. Notifications from other firms.
db.notifications.delete_many({"firm_id": {"$ne": keep_firm_id}})
print("Deleted notifications from other firms")

# 5. Clients from other firms + extra clients in the kept firm.
db.clients.delete_many({"firm_id": {"$ne": keep_firm_id}})
db.clients.delete_many({"firm_id": keep_firm_id, "_id": {"$ne": keep_client_id}})
print("Deleted every client except Punam")

# 6. CAs from other firms.
db.cas.delete_many({"firm_id": {"$ne": keep_firm_id}})
print("Deleted every CA except Monica")

# 7. Firms from other firms.
db.firms.delete_many({"_id": {"$ne": keep_firm_id}})
print("Deleted every firm except Monica's")

# 8. Audit logs from other firms.
db.audit_logs.delete_many({"firm_id": {"$ne": keep_firm_id}})
print("Deleted stale audit logs")

print()
print("=" * 50)
print("DONE.")
print(f"CA     : {KEEP_CA_EMAIL}")
print(f"Client : {KEEP_CLIENT_EMAIL}")
print(f"Firm   : {keep_firm_id}")
print("=" * 50)