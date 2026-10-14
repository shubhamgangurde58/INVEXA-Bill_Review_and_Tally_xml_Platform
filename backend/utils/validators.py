import re

from bson import ObjectId
from bson.errors import InvalidId
from flask import request

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")
MEMBERSHIP_PATTERN = re.compile(r"^\d{5,7}$")
MAX_AMOUNT = 1000000000  # 100 crore


# Check a request body for MongoDB operator keys such as "$ne" or "$gt".
# If these reach a query, an attacker can bypass logins (NoSQL injection),
# so we reject them before any route code runs.
def contains_dollar_key(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).startswith("$"):
                return True
            if contains_dollar_key(value):
                return True
        return False

    if isinstance(data, list):
        for item in data:
            if contains_dollar_key(item):
                return True
        return False

    return False


# Read the JSON body as a dict. A missing or broken body becomes an empty
# dict, so routes can report "missing fields" instead of crashing.
def read_json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return {}
    return body


# Return the names of required fields that are missing or not plain text.
# Requiring strings also blocks tricks like sending a number or a list.
def missing_fields(data, field_names):
    missing = []
    for name in field_names:
        value = data.get(name)
        if not isinstance(value, str) or value.strip() == "":
            missing.append(name)
    return missing


# Clean an optional text field: trimmed text, or "" if it is not text.
def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


# Turn a string from a URL or body into an ObjectId, or None if invalid.
# Routes use this so a bad id gives a clean 404 instead of a server error.
def to_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


# Check the password rules on the server (the browser check can be skipped).
# Returns an error message, or "" when the password is acceptable.
# The 72 limit exists because bcrypt only reads the first 72 bytes.
def password_error(password):
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password.encode("utf-8")) > 72:
        return "Password must be at most 72 characters"
    if not re.search(r"[A-Z]", password):
        return "Password needs at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password needs at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password needs at least one number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password needs at least one special character"
    return ""


# Format checks for the identity fields. They only check shape, not whether
# the number really exists in a government database.
def is_valid_email(email):
    return EMAIL_PATTERN.match(email) is not None


def is_valid_gstin(gstin):
    return GSTIN_PATTERN.match(gstin) is not None


def is_valid_mobile(mobile):
    return MOBILE_PATTERN.match(mobile) is not None


def is_valid_membership(number):
    return MEMBERSHIP_PATTERN.match(number) is not None


# Check a bill amount: it must be a real number above 0 and below 100 crore.
# Returns an error message, or "" when the amount is fine (used from Phase 5).
def amount_error(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "Amount must be a number"
    if value <= 0:
        return "Amount must be greater than 0"
    if value >= MAX_AMOUNT:
        return "Amount must be less than 100 crore"
    return ""
