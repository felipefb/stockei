"""
Stockei - Análise comparativa de custo de cloud (AWS vs GCP vs Azure)
Consulta CTO Agent (avaliação de stack) e CFO Agent (revisão de orçamento).

Preços de referência (jul/2026, on-demand, USD):
- GPU T4 (custo dominante): AWS g4dn.xlarge $0.526/h · Azure NC4as_T4_v3 $0.526/h ·
  GCP n1-standard-4 + T4 ≈ $0.54/h (mas com desconto automático de uso contínuo ~30%)
- Regiões Brasil encarecem ~40-60% em todos; Azure Brazil South tem
  disponibilidade limitada de GPU T4.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.strategic.cfo_agent import CFOAgent
from agents.strategic.cto_agent import CTOAgent

# Estimativa mensal MVP (12h/dia de GPU + RDS/SQL gerenciado + rede/monitoramento)
MONTHLY_USD = {
    "AWS (sa-east-1)":      {"gpu": 190, "db": 130, "compute": 70, "rede_outros": 115},  # 505
    "GCP (southamerica-e1)": {"gpu": 155, "db": 125, "compute": 65, "rede_outros": 105}, # 450 (desc. uso contínuo)
    "Azure (Brazil South)":  {"gpu": 200, "db": 140, "compute": 70, "rede_outros": 110}, # 520 (GPU fora de BR-South)
}

cto = CTOAgent()
cfo = CFOAgent()

# CTO: maturidade, fit com o time e eficiência de custo (1-5)
cto_result = cto.execute({
    "action": "evaluate_stack",
    "candidates": [
        {"name": "AWS",   "maturity": 5, "team_fit": 5, "cost_efficiency": 3},
        {"name": "GCP",   "maturity": 4, "team_fit": 3, "cost_efficiency": 4},
        {"name": "Azure", "maturity": 4, "team_fit": 3, "cost_efficiency": 3},
    ],
})

# CFO: cada provedor comparado ao orçamento aprovado de $505/mês (AWS baseline)
totals = {name: sum(parts.values()) for name, parts in MONTHLY_USD.items()}
cfo_result = cfo.execute({
    "action": "budget_review",
    "budget": {name: 505 for name in totals},
    "actuals": totals,
})

print("=== CTO Agent - evaluate_stack ===")
print(json.dumps(cto_result, indent=2, ensure_ascii=False))
print("\n=== CFO Agent - budget_review (vs baseline $505/mes) ===")
print(json.dumps(cfo_result, indent=2, ensure_ascii=False))
print("\n=== Totais mensais estimados (USD, MVP) ===")
for name, total in sorted(totals.items(), key=lambda kv: kv[1]):
    print(f"  {name}: ${total}")
