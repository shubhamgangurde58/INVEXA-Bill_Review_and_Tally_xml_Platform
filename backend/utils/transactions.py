from extensions import mongo_client


# Run a function inside a MongoDB transaction: everything it writes is
# saved together, or none of it is. Firm signup needs this so a firm can
# never exist without its CA. The function receives the session and must
# pass it to every insert. with_transaction also retries on temporary
# errors, so the function should be safe to run twice.
# Transactions need a replica set, which MongoDB Atlas provides.
def run_in_transaction(work):
    with mongo_client.start_session() as session:
        return session.with_transaction(work)
