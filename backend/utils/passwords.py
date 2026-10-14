import bcrypt

BCRYPT_ROUNDS = 4
BCRYPT_MAX_BYTES = 72


# Hash a plain password with bcrypt (12 rounds) and return it as text.
# bcrypt only reads the first 72 bytes, so longer passwords are refused
# here instead of being silently cut. The Phase 3 validator will also
# enforce a maximum length before this function is reached.
def hash_password(plain_password):
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long")

    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


# Compare a plain password with a stored bcrypt hash.
# Any problem (bad hash, too-long input) returns False instead of
# raising, so the login route can answer with one generic
# "Invalid credentials" message and never leak why it failed.
def check_password(plain_password, stored_hash):
    if not plain_password or not stored_hash:
        return False

    try:
        password_bytes = plain_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, stored_hash.encode("utf-8"))
    except ValueError:
        return False
