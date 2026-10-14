"""Create collections and indexes. Runs at startup; safe to run twice."""

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

from extensions import db

COLLECTION_NAMES = [
    "firms", "cas", "clients", "invoices",
    "chat_threads", "chat_messages",
    "notifications", "audit_logs", "auth_tokens",
]


# Create an index but accept an existing one under a different
# name. Older runs of setup may have created the same index with a
# default name and MongoDB refuses a duplicate (error 85).
def ensure_index(collection, keys, **options):
    try:
        collection.create_index(keys, **options)
    except OperationFailure as problem:
        if problem.code == 85 and "different name" in str(problem):
            return
        raise


# Create every collection that does not exist yet. MongoDB
# transactions (used in CA signup) are happiest when the
# collections already exist.
def create_collections():
    existing = set(db.list_collection_names())
    for name in COLLECTION_NAMES:
        if name in existing:
            continue
        try:
            db.create_collection(name)
        except CollectionInvalid:
            pass


def create_invoice_indexes():
    ensure_index(db.invoices, 
        [("firm_id", ASCENDING), ("status", ASCENDING)],
        name="invoices_by_firm_status",
    )
    ensure_index(db.invoices, 
        [("client_id", ASCENDING), ("uploaded_at", DESCENDING)],
        name="invoices_by_client_time",
    )
    ensure_index(db.invoices,
        [("firm_id", ASCENDING), ("bill_type", ASCENDING)],
        name="invoices_by_firm_type",
    )
    ensure_index(db.invoices, 
        [("client_id", ASCENDING), ("invoice_number", ASCENDING)],
        unique=True,
        partialFilterExpression={"invoice_number": {"$type": "string"}},
        name="uniq_client_invoice_number",
    )

def setup_database():
    create_collections()
    create_invoice_indexes()