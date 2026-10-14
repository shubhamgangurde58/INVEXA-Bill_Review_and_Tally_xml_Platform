from extensions import db

# Return the six numbers the client dashboard shows. Doing the counts
# in MongoDB means the dashboard doesn't need to download every row
# just to display a total.
def get_dashboard_stats(user):
    base = {"firm_id": user["firm_id"], "client_id": user["user_id"]}

    def count(status):
        q = dict(base)
        if status:
            q["status"] = status
        return db.invoices.count_documents(q)

    return {
        "total":         count(None),
        "with_ca":       count("uploaded"),
        "in_review":     count("pending_review"),
        "approved":      count("approved"),
        "rejected":      count("rejected"),
        "reupload":      count("reupload_requested"),
    }, None