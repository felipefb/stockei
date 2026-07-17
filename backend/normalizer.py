"""
Stockei - Normalização de produtos.

Converte o texto cru (OCR da embalagem ou descrição de base GTIN) em campos
estruturados: marca, nome, tamanho (valor + unidade) e categoria.

Exemplo:
  "Vigor Comcrehe 90 G Iogurte Adocado Tradicional"
  -> brand="Vigor", size_value=90, size_unit="g", category="Laticínios",
     name="Iogurte Adocado Tradicional"
"""

import re
import unicodedata

# Marcas comuns no varejo brasileiro (expandir com o catálogo dos clientes)
KNOWN_BRANDS = [
    "vigor", "nestle", "danone", "itambe", "piracanjuba", "italac", "batavo",
    "coca-cola", "coca cola", "pepsi", "guarana antarctica", "ambev", "heineken",
    "sadia", "perdigao", "seara", "friboi", "swift",
    "omo", "ype", "veja", "minuano", "brilhante",
    "colgate", "oral-b", "sensodyne", "dove", "nivea", "rexona",
    "neston", "nescau", "toddy", "quaker", "3 coracoes", "pilao", "melitta",
    "lenyes", "samsung", "philips", "multilaser",
]

_SIZE_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(kg|g|mg|l|lt|ml|un|und|unidades?|caps?|comprimidos?)\b",
    re.IGNORECASE,
)

CATEGORY_KEYWORDS = {
    "Laticínios": ["iogurte", "leite", "queijo", "requeijao", "manteiga", "grego", "coalhada"],
    "Bebidas": ["refrigerante", "suco", "agua", "cerveja", "energetico", "cha", "cafe"],
    "Mercearia": ["arroz", "feijao", "macarrao", "farinha", "acucar", "oleo", "molho"],
    "Higiene": ["sabonete", "shampoo", "creme dental", "desodorante", "absorvente"],
    "Limpeza": ["detergente", "sabao", "amaciante", "desinfetante", "agua sanitaria"],
    "Medicamentos": ["comprimido", "capsula", "xarope", "dipirona", "paracetamol", "mg"],
    "Acessórios": ["porta cartao", "capa", "carregador", "cabo", "fone", "suporte"],
}

# Ruído comum de OCR/embalagem que não pertence ao nome
_NOISE_WORDS = re.compile(
    r"\b(marca|modelo|cor)\s*[:.]|\b(pt|en|es)\b[-:.]|\bcom\s*crehe\b"
    r"|\bmade in \w+|\bindustria \w+",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def normalize_product(raw: str) -> dict:
    """Extrai campos estruturados do texto cru de identificação."""
    raw = raw.strip()
    work = _strip_accents(raw.lower())

    # tamanho
    size_value, size_unit = None, None
    m = _SIZE_RE.search(work)
    if m:
        size_value = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        size_unit = {"lt": "l", "und": "un", "unidade": "un", "unidades": "un"}.get(unit, unit)

    # marca
    brand = None
    for candidate in sorted(KNOWN_BRANDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(candidate)}\b", work):
            brand = candidate.title()
            break

    # categoria
    category = None
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in work for kw in keywords):
            category = cat
            break

    # nome limpo: remove marca, tamanho e ruído do texto original
    name = raw
    if m:
        name = re.sub(_SIZE_RE, " ", name)
    if brand:
        name = re.sub(rf"(?i)\b{re.escape(brand)}\b", " ", _strip_accents(name))
    name = _NOISE_WORDS.sub(" ", name)
    name = re.sub(r"[^\w\sÀ-ÿ-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip().title() or raw.title()

    display = " ".join(
        part for part in [
            brand,
            name,
            f"{size_value:g}{size_unit}" if size_value and size_unit else None,
        ] if part
    )

    return {
        "brand": brand,
        "name": name,
        "category": category,
        "size_value": size_value,
        "size_unit": size_unit,
        "display_name": display,
        "name_raw": raw,
    }
