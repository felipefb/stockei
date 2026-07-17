# Stockei — Plano de Iteração pós-Piloto
*Autor: Product Manager Agent · Janela: 2 semanas após coleta de feedback*

## Backlog priorizado (impacto × esforço — revisar com feedback real)
| # | Melhoria | Impacto | Esforço | Justificativa |
|---|---|---|---|---|
| 1 | Treinar modelo customizado com imagens dos pilotos | Alto | Alto | Acurácia real é o driver nº1 de conversão |
| 2 | Histórico de contagens no portal (lista + export CSV) | Alto | Baixo | Pedido esperado nº1 dos donos de loja |
| 3 | Alertas de validade por WhatsApp/e-mail | Alto | Médio | Valor percebido imediato; reduz perdas |
| 4 | Redis para fila/cache/rate-limit (multi-instância) | Médio | Médio | Pré-requisito de escala (Fase 2) |
| 5 | Importador de catálogo CSV no portal (self-service) | Médio | Baixo | Remove fricção do onboarding |

## Timeline proposta
- **Semana 1:** itens 2 e 5 (quick wins) + coleta de imagens para o item 1
- **Semana 2:** item 3 + início do treino (item 1) + item 4 em paralelo (DevOps)

## Milestones
- [ ] M1: portal com histórico + import CSV em produção (fim da semana 1)
- [ ] M2: alertas de validade ativos nos 5 pilotos (fim da semana 2)
- [ ] M3: modelo customizado v1 com mAP > 0.85 (Marco 5)

## Status da Fase 1
**MVP FUNCIONAL COMPLETO** ✅ — próximo marco: Integração com Sistemas Legados (Fase 2, semanas 9-12).
