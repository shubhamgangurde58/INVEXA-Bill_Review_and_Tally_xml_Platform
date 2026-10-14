import secrets

from extensions import db

# Letters and digits without look-alikes (no 0/O, 1/I) so a code read
# aloud or copied from a screen is hard to mistype.
CODE_CHARACTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SUFFIX_LENGTH = 5
MAX_ATTEMPTS = 10


# Take the first four letters of the firm name as the readable part of
# the code (Kulkarni and Associates becomes KULK).
# Short names are padded with X so every code has the same shape.
def build_prefix(firm_name):
    letters = []
    for character in firm_name.upper():
        if character.isalpha():
            letters.append(character)

    prefix = "".join(letters[:4])
    while len(prefix) < 4:
        prefix = prefix + "X"
    return prefix


# Make the random part of the code with the secrets module.
# secrets is used instead of random because invite codes act like a
# key into a firm and must not be guessable.
def build_suffix():
    suffix = ""
    for _ in range(SUFFIX_LENGTH):
        suffix = suffix + secrets.choice(CODE_CHARACTERS)
    return suffix


# Generate a code like KULK-4A8F2 that no firm is using yet.
# This is a lookup by code, so it cannot carry a firm_id filter. The
# unique index on invite_code is the final guard if two requests ever
# pick the same code at the same moment.
def generate_invite_code(firm_name):
    prefix = build_prefix(firm_name)

    for _ in range(MAX_ATTEMPTS):
        code = prefix + "-" + build_suffix()
        existing_firm = db.firms.find_one({"invite_code": code}, {"_id": 1})
        if existing_firm is None:
            return code

    raise RuntimeError("Could not generate a unique invite code")
