import unittest

from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher


class PasswordHasherTests(unittest.TestCase):
    def test_verifies_hexadecimal_hashes_used_by_the_database_seed(self) -> None:
        from controllers.password_service import hash_password

        encoded = hash_password("senha do seed")
        hasher = Pbkdf2PasswordHasher()
        self.assertTrue(hasher.verify_password("senha do seed", encoded))
        self.assertFalse(hasher.verify_password("outra senha", encoded))

    def test_rejects_malformed_password_hashes(self) -> None:
        hasher = Pbkdf2PasswordHasher()
        valid = hasher.hash_password("senha")
        scheme, _, salt, digest = valid.split("$")
        for encoded in (f"${valid}", f"{scheme}$0${salt}${digest}", f"{valid}!", f"{scheme}$310000$bad$bad"):
            with self.subTest(encoded=encoded):
                self.assertFalse(hasher.verify_password("senha", encoded))

    def test_each_password_hash_has_a_random_salt(self) -> None:
        hasher = Pbkdf2PasswordHasher()
        first = hasher.hash_password("senha")
        second = hasher.hash_password("senha")

        self.assertNotEqual(first, second)
        self.assertTrue(hasher.verify_password("senha", first))
        self.assertFalse(hasher.verify_password("outra", first))


if __name__ == "__main__":
    unittest.main()
