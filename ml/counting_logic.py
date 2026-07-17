"""
Stockei - Contagem de objetos únicos sem duplicação.
Um objeto conta uma única vez por sessão, identificado pelo track_id.
"""

from collections import Counter

from ml.tracking_engine import ObjectTracker

MIN_TRACK_AGE = 3  # frames mínimos para confirmar (filtra falsos positivos)


class UniqueCounter:
    """Conta objetos únicos por classe ao longo de uma sessão de contagem."""

    def __init__(self, tracker: ObjectTracker | None = None,
                 min_age: int = MIN_TRACK_AGE):
        self.tracker = tracker or ObjectTracker()
        self.min_age = min_age
        self._counted_ids: set[int] = set()
        self.counts: Counter = Counter()

    def process_frame(self, detections: list[dict]) -> dict:
        """Processa detecções de um frame e atualiza contagens únicas."""
        active = self.tracker.update(detections)
        new = 0
        for track in active:
            if track.age >= self.min_age and track.track_id not in self._counted_ids:
                self._counted_ids.add(track.track_id)
                self.counts[track.class_name] += 1
                new += 1
        return {
            "active_tracks": len(active),
            "new_counted": new,
            "totals": dict(self.counts),
            "total_unique": sum(self.counts.values()),
        }

    def reset(self):
        self.tracker = ObjectTracker()
        self._counted_ids.clear()
        self.counts.clear()
