"""
Stockei - Validação de datas de validade extraídas por OCR.
Suporta DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY, MM/YYYY e "VAL: ..." prefixos.
"""

import re
from datetime import date, datetime

_PATTERNS = [
    # DD/MM/YYYY ou DD-MM-YYYY ou DD.MM.YYYY
    (re.compile(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b"), "%d/%m/%Y", 3),
    # DD/MM/YY
    (re.compile(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{2})\b"), "%d/%m/%y", 3),
    # MM/YYYY (comum em validade)
    (re.compile(r"\b(\d{2})[/\-.](\d{4})\b"), "%m/%Y", 2),
]

MAX_YEARS_AHEAD = 10  # validade além disso é provavelmente erro de OCR


class DateResult(dict):
    """{valid, date (iso), raw, error, suggestions}"""


def extract_date(text: str) -> DateResult:
    """Extrai e valida a primeira data plausível do texto de OCR."""
    cleaned = _normalize_ocr(text)

    for pattern, fmt, groups in _PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        raw = "/".join(match.groups())
        try:
            parsed = datetime.strptime(raw, fmt).date()
        except ValueError:
            return DateResult(
                valid=False, date=None, raw=raw,
                error="Data com valores impossíveis (ex.: mês 13)",
                suggestions=_suggest(match.groups(), groups),
            )
        problem = _check_range(parsed)
        if problem:
            return DateResult(valid=False, date=parsed.isoformat(), raw=raw,
                              error=problem, suggestions=[])
        return DateResult(valid=True, date=parsed.isoformat(), raw=raw,
                          error=None, suggestions=[])

    return DateResult(valid=False, date=None, raw=text.strip(),
                      error="Nenhuma data reconhecida", suggestions=[])


def _normalize_ocr(text: str) -> str:
    """Corrige confusões comuns do OCR em contexto numérico."""
    out = text.upper()
    out = re.sub(r"(?:VAL|VENC|EXP)[.:\s]*", "", out)
    # O->0, I/l->1, S->5, B->8 apenas quando cercados de dígitos/separadores
    for wrong, right in [("O", "0"), ("I", "1"), ("L", "1"), ("S", "5"), ("B", "8")]:
        out = re.sub(rf"(?<=[\d/\-.]){wrong}(?=[\d/\-.])", right, out)
    return out


def _check_range(parsed: date) -> str | None:
    today = date.today()
    if parsed < today:
        return "Produto vencido"
    if parsed.year > today.year + MAX_YEARS_AHEAD:
        return f"Data além de {MAX_YEARS_AHEAD} anos — provável erro de leitura"
    return None


def _suggest(groups: tuple, count: int) -> list[str]:
    """Sugere correções trocando dia/mês (erro comum de OCR/formato)."""
    if count == 3:
        d, m, y = groups
        try:
            swapped = datetime.strptime(f"{m}/{d}/{y}", "%d/%m/%Y" if len(y) == 4 else "%d/%m/%y")
            return [swapped.date().isoformat()]
        except ValueError:
            pass
    return []
