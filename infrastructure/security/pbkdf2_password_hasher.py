import base64
import hashlib
import hmac
import os


class Pbkdf2PasswordHasher:
    """PBKDF2-SHA256 with a fresh random salt for every password."""

    ITERATIONS = 310_000
    SALT_BYTES = 16

    def hash_password(self, password: str) -> str:
        salt = os.urandom(self.SALT_BYTES)
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self.ITERATIONS
        )
        return "$".join((
            "pbkdf2_sha256",
            str(self.ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived).decode("ascii"),
        ))

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        if not isinstance(encoded_hash, str):
            return False
        try:
            scheme, iterations, salt_text, digest_text = encoded_hash.split("$", 3)
            if scheme != "pbkdf2_sha256":
                return False
            # The database seed stores hexadecimal values. New hashes use Base64.
            if len(salt_text) == self.SALT_BYTES * 2 and len(digest_text) == 64:
                salt = bytes.fromhex(salt_text)
                expected = bytes.fromhex(digest_text)
            else:
                salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
                expected = base64.b64decode(digest_text, altchars=b"-_", validate=True)
            if len(salt) != self.SALT_BYTES or len(expected) != 32:
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, int(iterations)
            )
        except (ValueError, TypeError, OverflowError):
            return False
        return hmac.compare_digest(actual, expected)
