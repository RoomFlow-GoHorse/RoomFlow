import unittest
from concurrent.futures import ThreadPoolExecutor

from infrastructure.repositories.in_memory_authorized_enrollment_repository import (
    InMemoryAuthorizedEnrollmentRepository,
)
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment
from models.domain.exceptions import ResourceNotFound


class AuthorizedEnrollmentRepositoryTests(unittest.TestCase):
    def test_atomic_repository_allows_only_one_concurrent_consumption(self) -> None:
        repository = InMemoryAuthorizedEnrollmentRepository()
        repository.add(AuthorizedEnrollment("e-1", "institution-1", "RA-1"))

        def consume(user_id: str) -> bool:
            try:
                repository.consume("institution-1", "RA-1", user_id)
                return True
            except ResourceNotFound:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(consume, ("u-1", "u-2")))
        self.assertEqual(sum(results), 1)
        self.assertEqual(repository.find("institution-1", "RA-1").status.value, "utilizado")


if __name__ == "__main__":
    unittest.main()
