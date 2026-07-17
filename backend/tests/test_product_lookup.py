"""Stockei - Testes da consulta de EAN (sem rede: monkeypatch)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend import product_lookup


def test_lookup_prefers_cosmos(monkeypatch):
    monkeypatch.setattr(product_lookup, "_from_cosmos", lambda e: "Produto Cosmos 90g")
    monkeypatch.setattr(product_lookup, "_from_open_food_facts", lambda e: "Outro")
    r = product_lookup.lookup_ean("789")
    assert r == {"name": "Produto Cosmos 90g", "source": "cosmos"}


def test_lookup_falls_back_to_off(monkeypatch):
    monkeypatch.setattr(product_lookup, "_from_cosmos", lambda e: None)
    monkeypatch.setattr(
        product_lookup, "_from_open_food_facts", lambda e: "Vigor Grego Tradicional 90 g"
    )
    r = product_lookup.lookup_ean("789")
    assert r["source"] == "openfoodfacts"


def test_lookup_unknown(monkeypatch):
    monkeypatch.setattr(product_lookup, "_from_cosmos", lambda e: None)
    monkeypatch.setattr(product_lookup, "_from_open_food_facts", lambda e: None)
    assert product_lookup.lookup_ean("000") is None


def test_cosmos_skipped_without_token(monkeypatch):
    monkeypatch.delenv("COSMOS_API_TOKEN", raising=False)
    assert product_lookup._from_cosmos("789") is None
