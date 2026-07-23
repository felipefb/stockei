"""
Stockei - Precificação inteligente (P5).

Duas fontes de sugestão, sempre como SUGESTÃO (o lojista decide):

1. Margem sobre o custo da NF-e (P10 alimenta cost_price): se o preço atual
   está abaixo da margem-alvo da categoria — ou zerado — sugere o preço que
   recompõe a margem.
2. Desconto progressivo por validade: produto com estoque parado e
   vencimento próximo vale mais girando com desconto do que virando perda
   (P11). Faixas: ≤7 dias -50%, ≤15 dias -30%, ≤30 dias -15%.
   O desconto nunca derruba o preço abaixo do custo conhecido.
"""

from datetime import datetime

# markup-alvo sobre o custo, por categoria (referência do varejo de bairro)
MARGIN_BY_CATEGORY = {
    "Bebidas": 0.35, "Laticínios": 0.30, "Mercearia": 0.28,
    "Higiene": 0.40, "Limpeza": 0.35, "Medicamentos": 0.33, "Acessórios": 0.50,
}
DEFAULT_MARGIN = 0.30

# (dias restantes máximos, desconto)
EXPIRY_TIERS = [(7, 0.50), (15, 0.30), (30, 0.15)]


def _round_price(value: float) -> float:
    """Arredonda para o centavo, terminação .X9 quando possível (preço psicológico)."""
    if value <= 0:
        return 0.0
    cents = round(value * 100)
    # 12.34 -> 12.29 só quando não derruba mais que 5 centavos
    down = cents - ((cents + 1) % 10)
    return round((down if down > 0 and cents - down <= 5 else cents) / 100, 2)


def margin_suggestion(product) -> dict | None:
    """Sugere recompor a margem-alvo quando o preço atual não a cobre."""
    cost = product.cost_price or 0.0
    if cost <= 0:
        return None
    target_margin = MARGIN_BY_CATEGORY.get(product.category or "", DEFAULT_MARGIN)
    target_price = _round_price(cost * (1 + target_margin))
    current = product.price or 0.0
    if current >= target_price:
        return None
    current_margin = (current - cost) / cost if current > 0 else None
    return {
        "type": "margem",
        "suggested_price": target_price,
        "current_price": round(current, 2),
        "cost_price": round(cost, 2),
        "current_margin_pct": round(current_margin * 100, 1) if current_margin is not None else None,
        "target_margin_pct": round(target_margin * 100, 1),
        "reason": (f"Preço atual não cobre a margem-alvo de "
                   f"{target_margin:.0%} da categoria"),
    }


def expiry_suggestion(product, inventory, today=None) -> dict | None:
    """Sugere desconto para girar estoque com vencimento próximo."""
    if inventory is None or inventory.expiry_date is None:
        return None
    if (inventory.quantity or 0) <= 0 or (product.price or 0) <= 0:
        return None
    today = today or datetime.utcnow().date()
    days_left = (inventory.expiry_date.date() - today).days
    if days_left < 0:  # vencido: caso do módulo de perdas, não de preço
        return None
    for max_days, discount in EXPIRY_TIERS:
        if days_left <= max_days:
            suggested = product.price * (1 - discount)
            cost = product.cost_price or 0.0
            floored = cost > 0 and suggested < cost
            if floored:
                suggested = cost
            return {
                "type": "validade",
                # travado no custo não sofre terminação .X9 (cairia abaixo do custo)
                "suggested_price": round(suggested, 2) if floored else _round_price(suggested),
                "current_price": round(product.price, 2),
                "discount_pct": round(discount * 100),
                "days_left": days_left,
                "quantity": inventory.quantity,
                "value_at_risk": round(inventory.quantity * product.price, 2),
                "floored_at_cost": floored,
                "reason": (f"Vence em {days_left} dia(s) — girar com "
                           f"-{discount:.0%} evita a perda"),
            }
    return None
