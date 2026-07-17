"""Stockei - Testes da normalização de produtos."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.normalizer import normalize_product


def test_normalize_vigor_from_ocr():
    # texto real lido pelo OCR da embalagem
    n = normalize_product("Vigor Comcrehe 90 G Iogurte Adocado Tradicional")
    assert n["brand"] == "Vigor"
    assert n["size_value"] == 90
    assert n["size_unit"] == "g"
    assert n["category"] == "Laticínios"
    assert "Iogurte" in n["name"]
    assert n["display_name"].startswith("Vigor")
    assert n["display_name"].endswith("90g")


def test_normalize_coca_from_gtin():
    n = normalize_product("REFRIGERANTE COCA-COLA ORIGINAL GARRAFA 2L")
    assert n["brand"] == "Coca-Cola"
    assert n["size_value"] == 2
    assert n["size_unit"] == "l"
    assert n["category"] == "Bebidas"


def test_normalize_accessory():
    n = normalize_product("Porta Cartao Magnetico Desli. Zante Em Fibra De Aramida Genuina Pt-Marca:Lenyes")
    assert n["brand"] == "Lenyes"
    assert n["category"] == "Acessórios"
    assert "Marca" not in n["name"]


def test_normalize_decimal_size():
    n = normalize_product("Leite Italac Integral 1,5 L")
    assert n["brand"] == "Italac"
    assert n["size_value"] == 1.5
    assert n["size_unit"] == "l"


def test_normalize_unknown_brand_keeps_name():
    n = normalize_product("Produto Generico Sem Marca")
    assert n["brand"] is None
    assert n["display_name"] == "Produto Generico Sem Marca"
    assert n["name_raw"] == "Produto Generico Sem Marca"
