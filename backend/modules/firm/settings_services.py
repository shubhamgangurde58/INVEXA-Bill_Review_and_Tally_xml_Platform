import ipaddress
import ntpath
import posixpath

from extensions import db
from models import utc_now
from utils.audit import log_action
from utils.serializers import to_iso
from utils.validators import clean_text, is_valid_gstin

MAX_NAME_LENGTH = 100
MAX_ADDRESS_LENGTH = 300
MAX_FOLDER_LENGTH = 260
TALLY_NAME_FIELDS = [
    "company_name", "party_group_purchase", "party_group_sales",
    "purchase_ledger", "sales_ledger",
    "cgst_input_ledger", "sgst_input_ledger", "igst_input_ledger",
    "cgst_output_ledger", "sgst_output_ledger", "igst_output_ledger",
]


# The firm's profile for the CA dashboard and settings page. It includes
# the invite code (only the CA may see it) and two counters for the badges.
def get_firm_profile(firm_id):
    firm = db.firms.find_one({"_id": firm_id})
    if firm is None:
        return None, ("Firm not found", 404)

    return {
        "id": str(firm["_id"]),
        "name": firm["name"],
        "gstin": firm["gstin"],
        "address": firm["address"],
        "invite_code": firm["invite_code"],
        "invite_code_updated_at": to_iso(firm.get("invite_code_updated_at")),
        "tally_settings": firm["tally_settings"],
        "created_at": to_iso(firm.get("createdAt")),
        "active_clients": db.clients.count_documents({"firm_id": firm_id, "status": "active"}),
        "pending_requests": db.clients.count_documents({"firm_id": firm_id, "status": "pending"}),
    }, None


# Accept only localhost or a private network address as the Tally host.
# Tally runs on the CA's own network, and without this rule the server could
# be told to send requests to any website. Returns "" when fine.
def tally_host_problem(host):
    message = "Host must be localhost or a private network IP address"
    if not isinstance(host, str):
        return message
    if host == "localhost":
        return ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return message
    if address.is_loopback or address.is_private:
        return ""
    return message


# The folder must be a full Windows or Linux path with no ".." parts, or
# empty (which means the default Desktop folder).
def tally_folder_problem(folder):
    message = "Folder must be a full path without '..'"
    if not isinstance(folder, str) or len(folder) > MAX_FOLDER_LENGTH:
        return message
    if folder == "":
        return ""
    if not (ntpath.isabs(folder) or posixpath.isabs(folder)):
        return message
    if ".." in folder.replace("\\", "/").split("/"):
        return message
    return ""


# Check one Tally setting and return a message, or "" when it is fine.
def tally_setting_problem(key, value):
    if key == "port":
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 65535:
            return "Port must be a number from 1 to 65535"
        return ""
    if key == "host":
        return tally_host_problem(value)
    if key == "xml_output_folder":
        return tally_folder_problem(value)
    if key in TALLY_NAME_FIELDS:
        if not isinstance(value, str) or value.strip() == "" or len(value) > MAX_NAME_LENGTH:
            return key.replace("_", " ").capitalize() + " must be 1 to 100 characters"
        return ""
    return "Unknown Tally setting"


# Turn the "tally_settings" part of the request into $set entries.
# Only the known keys are accepted, so nobody can write other fields.
def collect_tally_updates(raw_settings, updates):
    if not isinstance(raw_settings, dict):
        return ("tally_settings must be an object", 400)
    for key, value in raw_settings.items():
        problem = tally_setting_problem(key, value)
        if problem != "":
            return (problem, 400)
        if isinstance(value, str):
            value = value.strip()
        updates["tally_settings." + key] = value
    return None


# Turn the name, GSTIN and address fields of the request into $set entries.
def collect_basic_updates(data, updates):
    if "name" in data:
        name = clean_text(data["name"])
        if name == "" or len(name) > MAX_NAME_LENGTH:
            return ("Firm name must be 1 to 100 characters", 400)
        updates["name"] = name
    if "gstin" in data:
        gstin = clean_text(data["gstin"]).upper()
        if gstin != "" and not is_valid_gstin(gstin):
            return ("Enter a valid 15-character GSTIN", 400)
        updates["gstin"] = gstin
    if "address" in data:
        address = clean_text(data["address"])
        if len(address) > MAX_ADDRESS_LENGTH:
            return ("Address is too long", 400)
        updates["address"] = address
    return None


# Update the firm's profile and Tally settings. The update is limited to the
# CA's own firm by its _id, only listed fields can change, and the audit row
# names which fields changed (not their values).
def update_firm_profile(user, data, ip_address):
    updates = {}
    problem = collect_basic_updates(data, updates)
    if problem is None and "tally_settings" in data:
        problem = collect_tally_updates(data["tally_settings"], updates)
    if problem is not None:
        return None, problem
    if len(updates) == 0:
        return None, ("Nothing to update", 400)

    firm_id = user["firm_id"]
    db.firms.update_one({"_id": firm_id}, {"$set": updates})
    log_action(firm_id, user["user_id"], "ca", "firm_updated", firm_id,
               {"fields": sorted(updates.keys()), "at": utc_now().isoformat()}, ip_address)
    return get_firm_profile(firm_id)
