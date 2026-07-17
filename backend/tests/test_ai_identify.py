"""Stockei - Testes da identificação por IA (sem chamadas reais: mock)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from backend import ai_identify


@pytest.fixture(autouse=True)
def isolated_usage(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_identify, "USAGE_FILE", tmp_path / "usage.json")


class _FakeUsage:
    input_tokens = 1500
    output_tokens = 80


class _FakeBlock:
    type = "text"
    text = json.dumps({
        "brand": "Vigor", "product_name": "Iogurte Grego", "variant": "Tradicional",
        "size": "90g", "category": "Laticínios", "confidence": "alta",
    })


class _FakeResponse:
    content = [_FakeBlock()]
    usage = _FakeUsage()


def _mock_client(monkeypatch, calls):
    class _FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return _FakeResponse()

    class _FakeClient:
        def __init__(self):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)


def test_identify_package_builds_name_and_counts_usage(monkeypatch):
    calls = []
    _mock_client(monkeypatch, calls)
    result = ai_identify.identify_package(b"fake-jpeg")
    assert result["suggested_name"] == "Vigor Iogurte Grego Tradicional 90g"
    assert calls[0]["model"] == "claude-haiku-4-5"
    stats = ai_identify.usage_stats()
    assert stats["today_calls"] == 1
    assert stats["remaining"] == ai_identify.DAILY_LIMIT - 1
    assert stats["est_cost_today_brl"] > 0


def test_daily_limit_enforced(monkeypatch):
    calls = []
    _mock_client(monkeypatch, calls)
    monkeypatch.setattr(ai_identify, "DAILY_LIMIT", 2)
    ai_identify.identify_package(b"a")
    ai_identify.identify_package(b"b")
    with pytest.raises(ai_identify.AILimitReached):
        ai_identify.identify_package(b"c")
    assert len(calls) == 2  # a terceira nem chega na API


def test_usage_resets_next_day(monkeypatch):
    calls = []
    _mock_client(monkeypatch, calls)
    ai_identify.identify_package(b"a")
    # simula virada de dia corrompendo a data persistida
    data = json.loads(ai_identify.USAGE_FILE.read_text())
    data["date"] = "2000-01-01"
    ai_identify.USAGE_FILE.write_text(json.dumps(data))
    assert ai_identify.usage_stats()["today_calls"] == 0
