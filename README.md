# Stockei — Sistema de Agentes Especializados

Sistema multi-agente que opera o negócio do **Stockei**, um SaaS de gestão de estoque para pequenos negócios. Arquitetura replicada do padrão `agent_team_app`: herança de `AgentBase`, comunicação via message broker e event system, aprendizado contínuo por feedback, configuração YAML e orquestração por times.

## Arquitetura

20 agentes em 6 categorias, cada uma com sua classe base e time:

| Categoria | Agentes |
|---|---|
| Strategic | CEO, CFO, CTO |
| Planning | Product Manager, Tech Architect, Project Manager |
| Execution | Backend, Frontend, ML/AI, DevOps |
| Validation | QA, Security, Compliance |
| Commercialization | Sales, Marketing, Customer Success, Design/UX |
| Evolutionary | Product Evolution, Market Research, Competitive Analysis |

```
stockei/
├── agents/            # 6 bases + 20 agentes especializados
├── teams/             # TeamBase + 6 times
├── communication/     # MessageBroker, EventSystem
├── learning/          # ContinuousLearning, FeedbackSystem, KnowledgeBase
├── orchestration/     # StockeiOrchestrator, WorkflowManager
├── config/            # stockei_config.yaml, agents_config.yaml
├── utils/             # helpers, LLMClient plugável
├── tests/             # testes de agentes e orquestração
└── main.py            # ponto de entrada / demo
```

## Uso

```bash
pip install -r requirements.txt
python main.py            # demo do sistema completo
pytest tests/ -v          # testes
```

Exemplo:

```python
from main import build_system

orchestrator = build_system()
ceo = orchestrator.teams["strategic"].agents["CEO Agent"]
report = ceo.execute({"action": "monitor_kpis", "metrics": {
    "arr": 5_500_000, "churn_rate": 0.04, "cac": 450,
    "ltv": 12_000, "market_share": 0.18,
}})
print(report["health_status"])  # EXCELLENT
```

## Padrões replicados do agent_team_app

1. **Herança** — todos os agentes herdam de `AgentBase`
2. **Comunicação** — via `message_broker` e `event_system`
3. **Aprendizado** — feedback loop com `learning` (histórico, decisões, feedback)
4. **Configuração** — YAML com lista de agentes (`config/agents_config.yaml`)
5. **Orquestração** — `StockeiOrchestrator` coordena os 6 times e workflows

## LLM opcional

Os agentes usam lógica programática por padrão. Para habilitar chamadas a LLM, edite `config/stockei_config.yaml` (`llm.enabled: true`) e defina `OPENAI_API_KEY` no `.env`.
