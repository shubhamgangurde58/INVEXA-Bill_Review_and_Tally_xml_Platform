import os
import sys
from datetime import timedelta

from bson import ObjectId
from dotenv import load_dotenv

from db_setup import create_collections, create_indexes
from extensions import db
from models import utc_now
from models.chat_models import new_message_doc, new_thread_doc
from models.invoice_models import REUPLOAD_REASONS, new_invoice_doc
from models.tenant_models import new_ca_doc, new_client_doc, new_firm_doc
from seed_helpers import (
    build_bill_data,
    delete_demo_data,
    demo_email,
    make_bill_image,
    save_bill_file,
)
from utils.audit import log_action
from utils.invite_codes import generate_invite_code
from utils.notifications import create_notification
from utils.passwords import hash_password

DEMO_IP = "127.0.0.1"
LEGACY_COLLECTIONS = ["ca_users", "client_ca_assignment"]

# The first three clients are active. The fourth is pending, so the
# approval screen has something to approve.
FIRMS = [
    {
        "name": "Kulkarni and Associates",
        "gstin": "27AAKFK1234A1Z5",
        "address": "FC Road, Pune, Maharashtra",
        "key": "kulkarni",
        "invoice_prefix": "KUL",
        "ca": {"name": "Anil Kulkarni", "membership": "123456"},
        "clients": [
            {"business": "Sharma General Store", "owner": "Ramesh Sharma", "gstin": "27BBCPS4321C1Z8", "mobile": "9876500001", "status": "active"},
            {"business": "Patil Hardware", "owner": "Suresh Patil", "gstin": "27CCDPT2468D1Z2", "mobile": "9876500002", "status": "active"},
            {"business": "Deshmukh Stationers", "owner": "Mohan Deshmukh", "gstin": "27DDEPU1357E1Z6", "mobile": "9876500003", "status": "active"},
            {"business": "Joshi Medical Agency", "owner": "Vikas Joshi", "gstin": "27HHIPY2222J1Z9", "mobile": "9876500004", "status": "pending"},
        ],
    },
    {
        "name": "Mehta Shah and Co",
        "gstin": "24AABFM5678B1Z3",
        "address": "CG Road, Ahmedabad, Gujarat",
        "key": "mehta",
        "invoice_prefix": "MSC",
        "ca": {"name": "Hiren Mehta", "membership": "345678"},
        "clients": [
            {"business": "Gandhi Textiles", "owner": "Kiran Gandhi", "gstin": "24EEFPV9753F1Z1", "mobile": "9876500011", "status": "active"},
            {"business": "Trivedi Electronics", "owner": "Jay Trivedi", "gstin": "24FFGPW8642G1Z4", "mobile": "9876500012", "status": "active"},
            {"business": "Desai Foods", "owner": "Nilesh Desai", "gstin": "24GGHPX7531H1Z7", "mobile": "9876500013", "status": "active"},
            {"business": "Patel Sweets", "owner": "Dhruv Patel", "gstin": "24HHJPZ3333K1Z2", "mobile": "9876500014", "status": "pending"},
        ],
    },
]

# One bill for every status. client_index says which of the firm's
# active clients uploaded it. The first template must stay first,
# because the chat seed shares that bill.
INVOICE_TEMPLATES = [
    {
        "status": "uploaded", "client_index": 0, "invoice_suffix": "1001",
        "vendor_name": "Sunrise Packaging Pvt Ltd", "vendor_gstin": "27AAAPS1111A1Z1",
        "taxable_amount": 12500, "gst_rate": 18, "tax_type": "intra", "days_ago": 1,
    },
    {
        "status": "pending_review", "client_index": 1, "invoice_suffix": "1002",
        "vendor_name": "Bharat Steel Traders", "vendor_gstin": "27BBBPB2222B1Z2",
        "taxable_amount": 48000, "gst_rate": 18, "tax_type": "inter", "days_ago": 3,
    },
    {
        "status": "approved", "client_index": 1, "invoice_suffix": "1003",
        "vendor_name": "National Paper Mart", "vendor_gstin": "27CCCPN3333C1Z3",
        "taxable_amount": 20000, "gst_rate": 12, "tax_type": "intra", "days_ago": 6,
    },
    {
        "status": "rejected", "client_index": 2, "invoice_suffix": "1004",
        "vendor_name": "City Electricals", "vendor_gstin": "27DDDPC4444D1Z4",
        "taxable_amount": 7500, "gst_rate": 18, "tax_type": "intra", "days_ago": 8,
    },
    {
        "status": "reupload_requested", "client_index": 0, "invoice_suffix": "1005",
        "vendor_name": "Metro Office Supplies", "vendor_gstin": "27EEEPM5555E1Z5",
        "taxable_amount": 9800, "gst_rate": 18, "tax_type": "intra", "days_ago": 2,
    },
]


# Add the audit row and the notification that the real routes will
# create for each bill status. Seed data should look like real data
# after each workflow step, so the bell and audit screens are never empty.
def seed_invoice_events(firm_id, ca_id, client_id, invoice_id, status, invoice_number):
    if status in ("uploaded", "pending_review"):
        create_notification(firm_id, ca_id, "ca", "bill_uploaded", "New bill uploaded", "Bill " + invoice_number + " is waiting for review.", "/ca/documents")

    if status == "approved":
        log_action(firm_id, ca_id, "ca", "invoice_approved", invoice_id, {"invoice_number": invoice_number}, DEMO_IP)
        create_notification(firm_id, client_id, "client", "bill_approved", "Bill approved", "Bill " + invoice_number + " was approved.", "/client/invoices")

    if status == "rejected":
        log_action(firm_id, ca_id, "ca", "invoice_rejected", invoice_id, {"invoice_number": invoice_number}, DEMO_IP)
        create_notification(firm_id, client_id, "client", "bill_rejected", "Bill rejected", "Bill " + invoice_number + " was rejected.", "/client/invoices")

    if status == "reupload_requested":
        log_action(firm_id, ca_id, "ca", "reupload_requested", invoice_id, {"invoice_number": invoice_number}, DEMO_IP)
        create_notification(firm_id, client_id, "client", "reupload_requested", "Clearer photo needed", "Your CA needs a clearer photo of bill " + invoice_number + ".", "/client/invoices")


# Create one invoice (with its real PNG file in GridFS) for a client.
# The status decides which extra fields are filled, so the demo data
# looks the way real data will look after each step of the workflow.
# Returns the invoice id and number so the chat seed can share the bill.
def seed_invoice(firm_id, client_id, template, ca_id, number_prefix):
    status = template["status"]
    bill = build_bill_data(template, number_prefix)
    file_name = bill["invoice_number"].lower() + ".png"
    file_bytes = make_bill_image(bill, blurry=(status == "reupload_requested"))
    file_id = save_bill_file(firm_id, client_id, file_name, file_bytes)

    invoice = new_invoice_doc(firm_id, client_id, client_id, file_id, file_name, "png", "purchase")
    invoice["status"] = status
    invoice["uploaded_at"] = utc_now() - timedelta(days=template["days_ago"])

    if status in ("pending_review", "approved", "rejected"):
        invoice["ocr"] = {**bill, "raw_text": ""}

    if status == "approved":
        invoice["invoice_number"] = bill["invoice_number"]
        invoice["approved_by"] = ca_id
        invoice["approved_at"] = utc_now() - timedelta(days=template["days_ago"] - 1)

    if status == "rejected":
        invoice["remarks"] = "GSTIN on the bill does not match the vendor. Please upload a clearer copy."

    if status == "reupload_requested":
        invoice["reupload_reason"] = REUPLOAD_REASONS[0]
        invoice["reupload_requested_at"] = utc_now() - timedelta(days=1)
        invoice["reupload_requested_by"] = ca_id

    invoice_id = db.invoices.insert_one(invoice).inserted_id
    seed_invoice_events(firm_id, ca_id, client_id, invoice_id, status, bill["invoice_number"])
    return invoice_id, bill["invoice_number"]


# Create one chat thread with five messages between a client and the CA.
# The fourth message is a "bill" message, like the "Share to CA" button
# will create. The last message is from the client and unread, so the CA
# inbox shows a badge of 1 and the bell shows a "new_message" item.
def seed_chat(firm_id, client_id, ca_id, business_name, shared_invoice_id, shared_invoice_number):
    thread_id = db.chat_threads.insert_one(new_thread_doc(firm_id, client_id)).inserted_id
    now = utc_now()

    conversation = [
        ("client", "text", "Good morning sir, I have uploaded this month's purchase bill.", None, 50, True),
        ("ca", "text", "Thank you. I will review it today.", None, 45, True),
        ("client", "bill", "Bill " + shared_invoice_number, shared_invoice_id, 30, True),
        ("ca", "text", "The GSTIN looks faint. Can you send a clearer photo?", None, 20, True),
        ("client", "text", "Sure, I will send it in the evening.", None, 10, False),
    ]

    last_time = now
    for role, kind, text, invoice_id, minutes_ago, was_read in conversation:
        sender_id = client_id
        if role == "ca":
            sender_id = ca_id

        created_at = now - timedelta(minutes=minutes_ago)
        read_at = None
        if was_read:
            read_at = created_at + timedelta(minutes=1)

        message = new_message_doc(
            thread_id, sender_id, role, kind, text,
            created_at=created_at, read_at=read_at, invoice_id=invoice_id,
        )
        db.chat_messages.insert_one(message)
        last_time = created_at

    db.chat_threads.update_one(
        {"_id": thread_id, "firm_id": firm_id},
        {"$set": {"last_message_at": last_time, "unread_count_ca": 1, "unread_count_client": 0}},
    )
    create_notification(firm_id, ca_id, "ca", "new_message", "New message", business_name + " sent you a message.", "/ca/chat")


# Create the CA and the four clients of one firm.
# Pending clients also get a "client_joined" notification for the CA,
# exactly like a real signup will. Returns the client ids in order.
def seed_people(firm_id, firm_data, ca_id, password_hash):
    key = firm_data["key"]
    ca = firm_data["ca"]

    ca_doc = new_ca_doc(firm_id, ca["name"], demo_email("ca." + key), password_hash, ca["membership"], ca_id=ca_id)
    db.cas.insert_one(ca_doc)

    client_ids = []
    for index, client_data in enumerate(firm_data["clients"]):
        client_doc = new_client_doc(
            firm_id, client_data["business"], client_data["owner"],
            demo_email("client" + str(index + 1) + "." + key), client_data["gstin"],
            client_data["mobile"], firm_data["address"], password_hash,
            status=client_data["status"],
        )
        client_id = db.clients.insert_one(client_doc).inserted_id
        client_ids.append(client_id)

        if client_data["status"] == "pending":
            create_notification(firm_id, ca_id, "ca", "client_joined", "New client request", client_data["business"] + " wants to join your firm.", "/ca/clients")

    return client_ids


# Create one complete demo firm: firm, CA, clients, invoices and chat.
# The CA's id is made first so the firm can store owner_ca_id before the
# CA document exists, the same trick the signup transaction will use.
def seed_firm(firm_data, password_hash):
    ca_id = ObjectId()
    invite_code = generate_invite_code(firm_data["name"])
    firm_doc = new_firm_doc(firm_data["name"], firm_data["gstin"], firm_data["address"], invite_code, ca_id)
    firm_id = db.firms.insert_one(firm_doc).inserted_id

    client_ids = seed_people(firm_id, firm_data, ca_id, password_hash)

    shared_invoice = None
    for template in INVOICE_TEMPLATES:
        client_id = client_ids[template["client_index"]]
        invoice_id, invoice_number = seed_invoice(firm_id, client_id, template, ca_id, firm_data["invoice_prefix"])
        if shared_invoice is None:
            shared_invoice = (invoice_id, invoice_number)

    first_business = firm_data["clients"][0]["business"]
    seed_chat(firm_id, client_ids[0], ca_id, first_business, shared_invoice[0], shared_invoice[1])
    return invite_code


# Print what was created, but never the password itself.
# The password lives only in .env, so it cannot leak through the
# terminal history or a screenshot of this output.
def print_summary(invite_codes):
    print("")
    print("Demo data created. Log in with the password from DEMO_PASSWORD in .env.")
    for firm_data, invite_code in zip(FIRMS, invite_codes):
        key = firm_data["key"]
        print("")
        print(firm_data["name"] + "  (invite code: " + invite_code + ")")
        print("  CA      : " + demo_email("ca." + key))
        for index, client_data in enumerate(firm_data["clients"]):
            email = demo_email("client" + str(index + 1) + "." + key)
            print("  client  : " + email + "  [" + client_data["status"] + "]")


# Stop if the old v1 collections still exist.
# Mixing v1 data (ca_users, assignments) with v2 data would leave the
# database in a confusing half-migrated state.
def old_collections_exist():
    existing = set(db.list_collection_names())
    for name in LEGACY_COLLECTIONS:
        if name in existing:
            return True
    return False


# Entry point: check the password, prepare the database, remove old
# demo data, then create fresh demo data.
# Refusing to run without DEMO_PASSWORD keeps credentials out of code.
def main():
    load_dotenv()
    demo_password = os.getenv("DEMO_PASSWORD", "")
    if len(demo_password) < 8:
        print("DEMO_PASSWORD is missing or shorter than 8 characters in .env. Seed cancelled.")
        sys.exit(1)

    if old_collections_exist():
        print("Old v1 collections found. Run: python cleanup_v1_collections.py first.")
        sys.exit(1)

    create_collections()
    create_indexes()
    delete_demo_data()

    # One hash is reused for every demo user because bcrypt with 12
    # rounds is slow on purpose, and all demo users share one password.
    password_hash = hash_password(demo_password)

    invite_codes = []
    for firm_data in FIRMS:
        invite_codes.append(seed_firm(firm_data, password_hash))

    print_summary(invite_codes)


if __name__ == "__main__":
    main()
