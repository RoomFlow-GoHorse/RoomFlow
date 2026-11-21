from threading import RLock


class InMemoryEnrollmentPreviewRepository:
    def __init__(self):
        self._lock = RLock()
        self._previews = {}

    def save(self, preview_id, institution_id, enrollments, expires_at):
        with self._lock:
            self._previews[preview_id] = institution_id, enrollments, expires_at

    def find(self, preview_id, institution_id, now):
        with self._lock:
            item = self._previews.get(preview_id)
            if item is None or item[0] != institution_id or item[2] <= now:
                return None
            return item[1]

    def consume(self, preview_id, institution_id, at):
        with self._lock:
            if self.find(preview_id, institution_id, at) is not None:
                del self._previews[preview_id]
