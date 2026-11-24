from collections.abc import Iterator
from contextlib import contextmanager


class InMemoryAdminTransaction:
    """Commit administrative changes and their history under the same lock.

    The registered dictionaries contain immutable domain values. A shallow
    snapshot is sufficient to roll back both records and secondary indexes.
    """

    def __init__(self, lock) -> None:
        self.lock = lock
        self._stores: list[dict] = []

    def register(self, *stores: dict) -> None:
        self._stores.extend(stores)

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with self.lock:
            snapshots = [store.copy() for store in self._stores]
            try:
                yield
            except BaseException:
                for store, snapshot in zip(self._stores, snapshots):
                    store.clear()
                    store.update(snapshot)
                raise
