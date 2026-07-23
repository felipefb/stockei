# ADR-001 — Provedor de Cloud: AWS vs GCP (vs Azure)

*Status: **ACEITO** · Data: 2026-07-21 · Decisores: CTO Agent, CFO Agent, felipefb*
*Consolida a justificativa que estava partida entre [tech_stack_decision.md](tech_stack_decision.md) §3 e [scripts/cloud_cost_analysis.py](../../scripts/cloud_cost_analysis.py).*

---

## Contexto

O MVP do Stockei precisa de infraestrutura para três cargas distintas:

1. **Inferência com GPU** (YOLOv8 1:N para detecção de produtos na prateleira) — o custo dominante.
2. **PostgreSQL gerenciado** (inventário, movimentações, sessões).
3. **API + fila + estáticos** (FastAPI, Redis, portal).

Além disso, o produto usa o **Claude** (Anthropic) para a identificação multimodal de embalagens. Precisamos decidir em qual provedor rodar antes de aplicar o Terraform já escrito no Marco 1.

## Opções avaliadas

Comparação de custo mensal estimada para o MVP (5 lojas piloto, ~12h/dia de GPU T4, região Brasil), rodada pelos agentes CTO e CFO em jul/2026:

| Provedor | Custo/mês (USD) | GPU T4 em região BR | IaC pronto | Integração Claude |
|---|---|---|---|---|
| **GCP** (southamerica-east1) | **~$450** (−10%) | Sim | Não | Vertex AI — **com lacunas** |
| **AWS** (sa-east-1) | ~$505 (baseline) | Sim | **Sim (Terraform Marco 1)** | Claude Platform on AWS — **paridade total** |
| **Azure** (Brazil South) | ~$520 | **Não** (GPU T4 fora da região) | Não | Foundry — maioria em beta |

Preços de referência (on-demand): GPU T4 ≈ $0.53/h nos três; a GCP aplica desconto automático de uso contínuo (~30%), o que a torna a mais barata no uso real.

## Trade-offs

- **Custo** → vantagem **GCP** (~$55/mês no MVP; a diferença cresce para ~$200+/mês em escala de 100+ clientes).
- **GPU em São Paulo** → empate AWS/GCP; Azure eliminada (T4 indisponível em Brazil South, obrigaria inferência fora do país = mais latência/custo).
- **IaC pronto** → vantagem **AWS** (VPC, ECS, RDS, ALB, CloudWatch, CI/CD já escritos em Terraform no Marco 1; migrar para GCP seria retrabalho).
- **Integração com o Claude** → vantagem **AWS**. Hoje o Stockei chama a API da Anthropic direto (chave → `api.anthropic.com`), o que é **indiferente ao provedor**. Mas, para consumo *nativo pela cloud* (billing/IAM/residência de dados), o **Claude Platform on AWS** oferece paridade total de recursos, enquanto o **Vertex AI (GCP)** tem lacunas: sem web fetch, sem code execution, sem Message Batches, sem cache automático de prompt, web search só básico, sem Managed Agents. Isso importa se/quando adotarmos recursos avançados de servidor.

## Decisão

**Adotar AWS (sa-east-1).**

Motivos, em ordem:
1. **Integração completa com o Claude** (Claude Platform on AWS = paridade), preservando o caminho para recursos avançados sem troca de provedor no futuro.
2. **GPU T4 em São Paulo** (baixa latência para as câmeras).
3. **Terraform já escrito** — go-live mais rápido, sem retrabalho de IaC.

Aceitamos o **prêmio de custo de ~10% (~$55/mês no MVP)** como preço da maturidade da integração e da prontidão da infraestrutura. O custo do Claude em si **não pesou** na decisão (chave direta funciona em qualquer cloud) — apenas o cenário de consumo nativo futuro.

## Quando revisar esta decisão

Reabrir o ADR se **qualquer** um ocorrer:

1. **Escala** — ao passar de ~100 lojas, a economia da GCP ultrapassa ~$200/mês. Alternativa antes de migrar: Savings Plans na AWS (−30%), que anula a vantagem de preço da GCP.
2. **Paridade Claude na GCP** — se o **Vertex AI** passar a oferecer os recursos hoje ausentes (web fetch, code execution, batches, cache automático, Managed Agents), o principal argumento a favor da AWS enfraquece. → **monitoramento contínuo pelos agentes** (ver abaixo).

## Monitoramento (agentes)

O CTO Agent acompanha trimestralmente a evolução da paridade de recursos do Claude na GCP/Vertex, comparando a documentação de disponibilidade por plataforma da Anthropic. Registro do acompanhamento em [cloud_watch_log.md](cloud_watch_log.md). Um salto de paridade dispara a revisão deste ADR (gatilho #2 acima).
