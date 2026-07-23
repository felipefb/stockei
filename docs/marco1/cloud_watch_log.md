# Log de Monitoramento — Paridade do Claude na GCP/Vertex

*Acompanhamento do gatilho #2 do [ADR-001](cloud_decision_aws_vs_gcp.md): a decisão pela AWS
se apoia na integração completa com o Claude. Se o Vertex AI (GCP) alcançar paridade, revisar.*

Recursos monitorados (ausentes no Vertex em jul/2026, presentes no Claude Platform on AWS):
web fetch · code execution · Message Batches · cache automático de prompt · web search completo · Managed Agents.

| Data | Verificado por | Estado no Vertex (GCP) | Paridade? | Ação |
|---|---|---|---|---|
| 2026-07-21 | CTO Agent | Lacunas confirmadas (todos os 6 recursos ausentes/limitados) | Não | Manter AWS |

**Próxima verificação:** 2026-10-21 (trimestral).
**Como verificar:** consultar a documentação de disponibilidade por plataforma da Anthropic
(platform.claude.com) e comparar a coluna Vertex com a Claude Platform on AWS. Registrar a
linha acima. Se ≥ 4 dos 6 recursos passarem a estar disponíveis no Vertex, abrir issue
"Revisar ADR-001 — GCP atingiu paridade Claude".
