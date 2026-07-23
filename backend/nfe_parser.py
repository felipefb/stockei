"""
Stockei - Parser de NF-e (XML de nota fiscal eletrônica, modelo 55).

Extrai o mínimo que a conferência de recebimento e o pricing precisam:
chave da nota, emitente, data de emissão e os itens (EAN, descrição,
quantidade comercial e custo unitário). Tolera XML com ou sem o
envelope <nfeProc> e ignora namespaces.
"""

from datetime import datetime
from xml.etree import ElementTree


class NFEParseError(ValueError):
    pass


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(el, path: str):
    """find ignorando namespace (path com / simples)."""
    parts = path.split("/")
    current = [el]
    for part in parts:
        nxt = []
        for c in current:
            nxt.extend(ch for ch in c if _strip_ns(ch.tag) == part)
        current = nxt
        if not current:
            return None
    return current[0]


def _findall(el, tag: str):
    found = []

    def walk(node):
        for ch in node:
            if _strip_ns(ch.tag) == tag:
                found.append(ch)
            else:
                walk(ch)

    walk(el)
    return found


def _text(el, path: str, default: str = "") -> str:
    node = _find(el, path)
    return (node.text or "").strip() if node is not None else default


def _num(el, path: str) -> float:
    raw = _text(el, path, "0").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def parse_nfe(xml_bytes: bytes) -> dict:
    """
    Retorna {key, supplier, issued_at, items:[{ean, description, qty, unit_cost}]}.
    Levanta NFEParseError se o XML não for uma NF-e reconhecível.
    """
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise NFEParseError(f"XML inválido: {exc}")

    inf = _findall(root, "infNFe")
    if not inf:
        raise NFEParseError("XML não contém uma NF-e (infNFe ausente)")
    inf = inf[0]

    key = (inf.get("Id") or "").removeprefix("NFe")
    supplier = _text(inf, "emit/xNome")

    issued_at = None
    raw_date = _text(inf, "ide/dhEmi") or _text(inf, "ide/dEmi")
    if raw_date:
        try:
            issued_at = datetime.fromisoformat(raw_date).replace(tzinfo=None)
        except ValueError:
            pass

    items = []
    for det in _findall(inf, "det"):
        prod = _find(det, "prod")
        if prod is None:
            continue
        ean = _text(prod, "cEAN")
        if ean.upper() in ("", "SEM GTIN"):
            ean = _text(prod, "cEANTrib")
        if ean.upper() == "SEM GTIN":
            ean = ""
        qty = _num(prod, "qCom") or _num(prod, "qTrib")
        unit_cost = _num(prod, "vUnCom") or _num(prod, "vUnTrib")
        items.append({
            "ean": ean,
            "description": _text(prod, "xProd"),
            "qty": qty,
            "unit_cost": round(unit_cost, 4),
        })

    if not items:
        raise NFEParseError("NF-e sem itens (det/prod ausente)")

    return {"key": key, "supplier": supplier, "issued_at": issued_at, "items": items}
