"""Stockei - Testes de rastreamento e contagem única."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.counting_logic import UniqueCounter
from ml.tracking_engine import ObjectTracker, iou


def det(name, x, y, conf=0.9, size=100):
    return {"class_name": name, "confidence": conf, "bbox": [x, y, x + size, y + size]}


def test_iou():
    assert iou([0, 0, 100, 100], [0, 0, 100, 100]) == 1.0
    assert iou([0, 0, 100, 100], [200, 200, 300, 300]) == 0.0
    assert 0.3 < iou([0, 0, 100, 100], [50, 0, 150, 100]) < 0.4


def test_track_id_stable_across_frames():
    tracker = ObjectTracker()
    t1 = tracker.update([det("caixa", 10, 10)])
    t2 = tracker.update([det("caixa", 15, 12)])  # mesmo objeto, moveu um pouco
    assert t1[0].track_id == t2[0].track_id
    assert t2[0].age == 2


def test_new_object_gets_new_id():
    tracker = ObjectTracker()
    tracker.update([det("caixa", 10, 10)])
    tracks = tracker.update([det("caixa", 12, 10), det("caixa", 400, 400)])
    assert len({t.track_id for t in tracks}) == 2


def test_different_class_not_matched():
    tracker = ObjectTracker()
    a = tracker.update([det("caixa", 10, 10)])
    b = tracker.update([det("garrafa", 10, 10)])  # mesma posição, outra classe
    assert a[0].track_id != b[0].track_id


def test_occlusion_recovery():
    tracker = ObjectTracker(max_missing=5)
    original = tracker.update([det("caixa", 10, 10)])[0].track_id
    for _ in range(3):  # objeto some por 3 frames (oclusão)
        tracker.update([])
    recovered = tracker.update([det("caixa", 14, 12)])[0].track_id
    assert recovered == original


def test_track_expires_after_leaving_frame():
    tracker = ObjectTracker(max_missing=2)
    tracker.update([det("caixa", 10, 10)])
    for _ in range(3):
        tracker.update([])
    assert len(tracker.tracks) == 0


def test_no_duplicate_counting():
    counter = UniqueCounter(min_age=2)
    # mesmo objeto visível por 10 frames -> conta 1 vez
    for i in range(10):
        result = counter.process_frame([det("caixa", 10 + i, 10)])
    assert result["totals"] == {"caixa": 1}
    assert result["total_unique"] == 1


def test_counts_multiple_unique_objects():
    counter = UniqueCounter(min_age=2)
    for i in range(5):
        counter.process_frame([
            det("caixa", 10 + i, 10),
            det("caixa", 300 + i, 300),
            det("garrafa", 500, 100 + i),
        ])
    totals = counter.counts
    assert totals["caixa"] == 2
    assert totals["garrafa"] == 1


def test_min_age_filters_flicker():
    counter = UniqueCounter(min_age=3)
    # falso positivo que aparece 1 frame só
    counter.process_frame([det("caixa", 10, 10)])
    result = counter.process_frame([])
    assert result["total_unique"] == 0


def test_camera_movement_gradual():
    # câmera em movimento: todas as caixas deslocam juntas gradualmente
    counter = UniqueCounter(min_age=2)
    for i in range(8):
        shift = i * 8
        counter.process_frame([det("caixa", 10 + shift, 10), det("caixa", 200 + shift, 10)])
    assert counter.counts["caixa"] == 2  # sem duplicar apesar do movimento


def test_reset():
    counter = UniqueCounter(min_age=1)
    counter.process_frame([det("caixa", 0, 0)])
    counter.reset()
    assert counter.process_frame([])["total_unique"] == 0
