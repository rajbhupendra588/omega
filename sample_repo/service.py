"""Sample service class for entity-level analysis demo."""


class DataService:
    """Coordinates data access with moderate complexity."""

    MAX_RETRIES = 3

    def __init__(self, repository, logger):
        self.repository = repository
        self.logger = logger
        self._cache = {}

    def fetch_batch(self, ids, strict=False, transform=None, fallback=None):
        results = []
        for item_id in ids:
            if strict and item_id < 0:
                if fallback:
                    results.append(fallback(item_id))
                continue
            if transform:
                for step in range(3):
                    if step % 2 == 0:
                        results.append(transform(item_id, step))
            else:
                results.append(self.repository.get(item_id))
        return results
