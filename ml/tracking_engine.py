"""
Stockei - Rastreamento de objetos entre frames.

Implementa tracker por associação IoU (núcleo do SORT). Em produção, com GPU,
o DeepSORT (deep_sort_pytorch) substitui a associação por embeddings de aparência —
a interface `update(detections)` é a mesma.
"""

import itertools
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("stockei.tracking")

IOU_THRESHOLD = 0.3
MAX_FRAMES_MISSING = 10  # frames sem match até expirar o track (lida com oclusão)


def iou(box_a: list[float], box_b: list[float]) -> float:
    """Intersection over Union de duas caixas [x1,y1,x2,y2]."""
    xa, ya = max(box_a[0], box_b[0]), max(box_a[1], box_b[1])
    xb, yb = min(box_a[2], box_b[2]), min(box_a[3], box_b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    if inter == 0:
        return 0.0
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / (area_a + area_b - inter)


@dataclass
class Track:
    track_id: int
    class_name: str
    bbox: list[float]
    confidence: float
    frames_missing: int = 0
    age: int = 1
    history: list[list[float]] = field(default_factory=list)


class ObjectTracker:
    """Associa detecções entre frames mantendo IDs estáveis."""

    def __init__(self, iou_threshold: float = IOU_THRESHOLD,
                 max_missing: int = MAX_FRAMES_MISSING):
        self.iou_threshold = iou_threshold
        self.max_missing = max_missing
        self.tracks: dict[int, Track] = {}
        self._next_id = itertools.count(1)

    def update(self, detections: list[dict]) -> list[Track]:
        """
        Atualiza tracks com as detecções do frame atual.
        detections: [{class_name, confidence, bbox}]
        Retorna tracks ativos (visíveis neste frame).
        """
        unmatched = list(detections)
        matched_ids = set()

        # associação greedy por maior IoU (mesma classe)
        pairs = []
        for track_id, track in self.tracks.items():
            for i, det in enumerate(unmatched):
                if det["class_name"] != track.class_name:
                    continue
                score = iou(track.bbox, det["bbox"])
                if score >= self.iou_threshold:
                    pairs.append((score, track_id, i))
        pairs.sort(reverse=True)

        used_dets: set[int] = set()
        for score, track_id, i in pairs:
            if track_id in matched_ids or i in used_dets:
                continue
            det = unmatched[i]
            track = self.tracks[track_id]
            track.history.append(track.bbox)
            track.bbox = det["bbox"]
            track.confidence = det["confidence"]
            track.frames_missing = 0
            track.age += 1
            matched_ids.add(track_id)
            used_dets.add(i)

        # novas detecções -> novos tracks
        for i, det in enumerate(unmatched):
            if i in used_dets:
                continue
            tid = next(self._next_id)
            self.tracks[tid] = Track(
                track_id=tid,
                class_name=det["class_name"],
                bbox=det["bbox"],
                confidence=det["confidence"],
            )
            matched_ids.add(tid)

        # tracks sem match: incrementa ausência e expira
        expired = []
        for track_id, track in self.tracks.items():
            if track_id not in matched_ids:
                track.frames_missing += 1
                if track.frames_missing > self.max_missing:
                    expired.append(track_id)
        for track_id in expired:
            del self.tracks[track_id]

        return [t for tid, t in self.tracks.items() if tid in matched_ids]
