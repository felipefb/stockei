"""
Stockei - Validação de datas de validade extraídas por OCR.
Suporta DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY, MM/YYYY e "VAL: ..." prefixos.
"""

import re
from datetime import date, datetime

# (regex, formato, nº grupos, exige_plausibilidade)
# Formatos curtos/com espaço são ambíguos (confundem com lote) — só valem se
# mês/ano fizerem sentido para uma validade (_plausible_month_year).
_PATTERNS = [
    # DD/MM/YYYY ou DD-MM-YYYY ou DD.MM.YYYY
    (re.compile(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b"), "%d/%m/%Y", 3, False),
    # DD/MM/YY
    (re.compile(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{2})\b"), "%d/%m/%y", 3, False),
    # DD MM YY separado por espaço (estampa/jato de tinta: "15 08 26")
    (re.compile(r"\b(\d{2}) (\d{2}) (\d{2})\b"), "%d/%m/%y", 3, True),
    # MM/YYYY (comum em validade)
    (re.compile(r"\b(\d{2})[/\-.](\d{4})\b"), "%m/%Y", 2, False),
    # MM/AA ou "MM AA" (gravação em metal: "05/26", "05 26")
    (re.compile(r"\b(\d{2})[/\-. ](\d{2})\b"), "%m/%y", 2, True),
]

MAX_YEARS_AHEAD = 10  # validade além disso é provavelmente erro de OCR


class DateResult(dict):
    """{valid, date (iso), raw, error, suggestions}"""


def extract_date(text: str) -> DateResult:
    """Extrai e valida a primeira data plausível do texto de OCR."""
    cleaned = _normalize_ocr(text)

    for pattern, fmt, groups, needs_plausibility in _PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        if needs_plausibility and not _plausible_month_year(match.groups(), fmt):
            continue
        raw = "/".join(match.groups())
        try:
            parsed = datetime.strptime(raw, fmt).date()
            if fmt in ("%m/%Y", "%m/%y"):
                # validade "MM/AA" vale até o ÚLTIMO dia do mês
                import calendar

                parsed = parsed.replace(
                    day=calendar.monthrange(parsed.year, parsed.month)[1])
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


# Rótulos que indicam FABRICAÇÃO (descartar) e VALIDADE (priorizar)
_FAB_LABEL = re.compile(r"\b(F|FAB|FABR|FABRICA[CÇ][AÃ]O|MFG|PROD)\b", re.IGNORECASE)
_VAL_LABEL = re.compile(r"\b(V|VAL|VALIDADE|VENC|VENCIMENTO|EXP|BB|BEST BEFORE)\b",
                        re.IGNORECASE)


def _label_score(text: str, match_start: int) -> int:
    """
    Classifica uma data pelo rótulo mais próximo À ESQUERDA (janela de 12 chars):
    +1 se validade (V/VAL/VENC), -1 se fabricação (F/FAB), 0 sem rótulo.
    """
    window = text[max(0, match_start - 12):match_start]
    val = list(_VAL_LABEL.finditer(window))
    fab = list(_FAB_LABEL.finditer(window))
    last_val = val[-1].start() if val else -1
    last_fab = fab[-1].start() if fab else -1
    if last_val == last_fab:      # nenhum rótulo
        return 0
    return 1 if last_val > last_fab else -1


def extract_best_expiry(text: str) -> DateResult:
    """
    Extrai a VALIDADE de um texto que pode conter várias datas (ex.: linha com
    FAB e VAL). Prioriza a data rotulada como validade; descarta a de fabricação;
    entre datas sem rótulo, escolhe a mais distante no futuro (validade > fabricação).
    """
    cleaned = _normalize_ocr(text)
    raw_matches = []  # (start, end, label_score, parsed_date, raw, DateResult)

    for pattern, fmt, groups, needs_plausibility in _PATTERNS:
        for match in pattern.finditer(cleaned):
            if needs_plausibility and not _plausible_month_year(match.groups(), fmt):
                continue
            raw = "/".join(match.groups())
            try:
                parsed = datetime.strptime(raw, fmt).date()
                if fmt in ("%m/%Y", "%m/%y"):
                    import calendar
                    parsed = parsed.replace(
                        day=calendar.monthrange(parsed.year, parsed.month)[1])
            except ValueError:
                continue
            result = extract_date(match.group(0))
            raw_matches.append((match.start(), match.end(),
                                _label_score(cleaned, match.start()),
                                parsed, raw, result))

    # descarta matches contidos em outro mais longo (MM/AA dentro de DD/MM/AA)
    candidates = []
    for m in raw_matches:
        if any(o is not m and o[0] <= m[0] and o[1] >= m[1] and
               (o[1] - o[0]) > (m[1] - m[0]) for o in raw_matches):
            continue
        candidates.append((m[2], m[3], m[4], m[5]))  # score, parsed, raw, result

    if not candidates:
        return DateResult(valid=False, date=None, raw=text.strip(),
                          error="Nenhuma data reconhecida", suggestions=[])

    # descarta explicitamente as de fabricação se houver alguma não-fabricação
    non_fab = [c for c in candidates if c[0] >= 0]
    pool = non_fab or candidates
    # 1º critério: maior label_score (validade rotulada vence); 2º: data mais futura
    best = max(pool, key=lambda c: (c[0], c[1]))
    return best[3]


def _plausible_month_year(groups: tuple, fmt: str) -> bool:
    """Aceita formatos curtos só quando mês e ano fazem sentido para validade."""
    year_now = date.today().year % 100
    if fmt == "%m/%y":
        month, year = int(groups[0]), int(groups[1])
    else:  # %d/%m/%y com espaços
        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
        if not 1 <= day <= 31:
            return False
    return 1 <= month <= 12 and (year_now - 2) <= year <= (year_now + MAX_YEARS_AHEAD)


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
