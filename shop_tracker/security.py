import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(stored_hash, password):
    if stored_hash.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored_hash, password)

    # Support legacy SHA-256 hashes until a user logs in successfully.
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(stored_hash, legacy_hash)


def needs_password_rehash(stored_hash):
    return not stored_hash.startswith(("scrypt:", "pbkdf2:"))
