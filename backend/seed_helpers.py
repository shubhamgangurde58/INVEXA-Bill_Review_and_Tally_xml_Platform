import io
from datetime import timedelta

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from extensions import db, fs
from models import utc_now

DEMO_EMAIL_DOMAIN = "demo.invexa.test"
DEMO_EMAIL_PATTERN = r"@demo\.invexa\.test$"


# Build a demo email address. Every seeded user ends with the same
# domain, which is how the cleanup step finds demo data and leaves real
# data alone.
def demo_email(local_part):
    return local_part + "@" + DEMO_EMAIL_DOMAIN


# Load a readable font for the sample bill.
# Newer Pillow versions accept a size for the built-in font. Older ones
# do not, so we fall back to the small default instead of crashing.
def load_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# Turn an ISO date (2026-09-05) into the DD/MM/YYYY style printed on
# Indian bills, so the sample image looks like a real invoice.
def to_display_date(iso_date):
    year, month, day = iso_date.split("-")
    return day + "/" + month + "/" + year


# Work out the tax amounts and total for one demo bill.
# Intra-state bills split tax into CGST and SGST. Inter-state bills use
# IGST only, which matches the rule that CGST and IGST never co-exist.
def build_bill_data(template, number_prefix):
    taxable = float(template["taxable_amount"])
    rate = float(template["gst_rate"])
    cgst = 0.0
    sgst = 0.0
    igst = 0.0

    if template["tax_type"] == "intra":
        cgst = round(taxable * rate / 200, 2)
        sgst = round(taxable * rate / 200, 2)
    else:
        igst = round(taxable * rate / 100, 2)

    bill_date = utc_now() - timedelta(days=template["days_ago"] + 1)

    return {
        "invoice_number": number_prefix + "-" + template["invoice_suffix"],
        "invoice_date": bill_date.strftime("%Y-%m-%d"),
        "vendor_name": template["vendor_name"],
        "gstin": template["vendor_gstin"],
        "taxable_amount": taxable,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_amount": round(taxable + cgst + sgst + igst, 2),
    }


# Draw a plain sample bill as a PNG and return the raw bytes.
# The text uses labels like "Invoice No" and "Total Amount" so the
# rule-based OCR in Phase 5 has something realistic to read.
# blurry=True softens the picture, which gives the "Request Reupload"
# demo bill a believable reason.
def make_bill_image(bill, blurry=False):
    image = Image.new("RGB", (900, 1000), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(40)
    body_font = load_font(26)

    draw.text((60, 50), "TAX INVOICE", fill="black", font=title_font)
    draw.text((60, 130), bill["vendor_name"], fill="black", font=body_font)

    lines = [
        "GSTIN: " + bill["gstin"],
        "Invoice No: " + bill["invoice_number"],
        "Date: " + to_display_date(bill["invoice_date"]),
        "",
        "Taxable Value: " + format(bill["taxable_amount"], ".2f"),
        "CGST: " + format(bill["cgst"], ".2f"),
        "SGST: " + format(bill["sgst"], ".2f"),
        "IGST: " + format(bill["igst"], ".2f"),
        "",
        "Total Amount: " + format(bill["total_amount"], ".2f"),
    ]

    y_position = 220
    for line in lines:
        draw.text((60, y_position), line, fill="black", font=body_font)
        y_position = y_position + 60

    if blurry:
        image = image.filter(ImageFilter.GaussianBlur(6))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# Store one file in GridFS with firm and client ids as metadata.
# The file route later checks that metadata so a CA from another firm
# cannot download this file even if they guess its id.
def save_bill_file(firm_id, client_id, file_name, file_bytes):
    return fs.put(
        file_bytes,
        filename=file_name,
        content_type="image/png",
        firm_id=firm_id,
        client_id=client_id,
    )


# Delete the demo clients' invoices and their GridFS files.
# Files go first, then the invoice documents that point to them.
def delete_demo_invoices(client_ids):
    invoices = db.invoices.find({"client_id": {"$in": client_ids}}, {"file_id": 1})
    for invoice in invoices:
        fs.delete(invoice["file_id"])
    db.invoices.delete_many({"client_id": {"$in": client_ids}})


# Delete the demo clients' chat threads, messages and chat files.
# Deleting a GridFS file that is already gone is harmless in PyMongo.
def delete_demo_chats(client_ids):
    threads = list(db.chat_threads.find({"client_id": {"$in": client_ids}}, {"_id": 1}))
    thread_ids = [thread["_id"] for thread in threads]

    messages = db.chat_messages.find({"thread_id": {"$in": thread_ids}}, {"file_id": 1})
    for message in messages:
        if message.get("file_id") is not None:
            fs.delete(message["file_id"])

    db.chat_messages.delete_many({"thread_id": {"$in": thread_ids}})
    db.chat_threads.delete_many({"_id": {"$in": thread_ids}})


# Remove a demo firm only when nobody real is left inside it.
# A real client could have joined a demo firm with its invite code, and
# we must never delete their firm out from under them.
def delete_empty_demo_firms(firm_ids):
    for firm_id in firm_ids:
        remaining_cas = db.cas.count_documents({"firm_id": firm_id})
        remaining_clients = db.clients.count_documents({"firm_id": firm_id})
        if remaining_cas == 0 and remaining_clients == 0:
            db.firms.delete_one({"_id": firm_id})


# Delete only the data created by an earlier seed run.
# Demo users are found by their email domain, and everything else is
# removed through their ids. Real firms, users and bills are untouched.
def delete_demo_data():
    email_filter = {"email": {"$regex": DEMO_EMAIL_PATTERN}}
    demo_cas = list(db.cas.find(email_filter, {"firm_id": 1}))
    demo_clients = list(db.clients.find(email_filter, {"firm_id": 1}))

    ca_ids = [ca["_id"] for ca in demo_cas]
    client_ids = [client["_id"] for client in demo_clients]
    user_ids = ca_ids + client_ids
    firm_ids = set()
    for user in demo_cas + demo_clients:
        firm_ids.add(user["firm_id"])
    for firm_id in db.firms.distinct("_id", {"is_demo": True}):
        firm_ids.add(firm_id)

    delete_demo_invoices(client_ids)
    delete_demo_chats(client_ids)
    db.notifications.delete_many({"user_id": {"$in": user_ids}})
    db.auth_tokens.delete_many({"user_id": {"$in": user_ids}})
    db.audit_logs.delete_many({"actor_id": {"$in": user_ids}})
    db.clients.delete_many({"_id": {"$in": client_ids}})
    db.cas.delete_many({"_id": {"$in": ca_ids}})
    delete_empty_demo_firms(firm_ids)
