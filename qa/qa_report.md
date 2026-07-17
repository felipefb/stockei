# Stockei — Relatório de QA (Marco 3)
*Autor: QA Agent · Data: 17/07/2026*

## Resumo Executivo
**Veredito: APROVADO para MVP** — 50/50 testes automatizados passando (100%),
cobertura de código 91% (backend + ml), zero bugs críticos abertos.

## Escopo testado
| Componente | Testes | Resultado |
|---|---|---|
| Sistema de agentes (times, orquestração) | 13 | ✅ 100% |
| APIs base (auth JWT, CRUD, inventário, movimentações) | 8 | ✅ 100% |
| Fluxo de frames (fila, cache, WebSocket, e2e) | 5 | ✅ 100% |
| Detecção (contrato /detect, latência, determinismo) | 4 | ✅ 100% |
| OCR de datas (formatos, vencidos, confusões de OCR, endpoint) | 9 | ✅ 100% |
| Tracking + contagem única (oclusão, movimento, duplicação) | 11 | ✅ 100% |
| **Total** | **50** | **✅ 100%** |

## Métricas vs Critérios
| Critério | Meta | Medido | Status |
|---|---|---|---|
| Testes passando | ≥ 95% | 100% | ✅ |
| Latência detecção | < 100ms | < 5ms (mock) / < 60ms est. T4 | ✅ |
| Latência OCR | < 50ms | < 5ms (mock) | ✅ |
| Latência e2e frame | < 200ms | < 50ms | ✅ |
| Contagem sem duplicação | > 95% | 100% nos cenários de teste | ✅ |
| Cobertura de código | — | 91% | ✅ |

## Casos de teste
186 casos catalogados em [test_cases.xlsx](test_cases.xlsx): matriz Detecção/OCR/Tracking ×
iluminação (3) × ângulo (3) × visibilidade (2) × quantidade (3) + suítes de API/e2e.
Casos de campo com produtos reais ficam **pendentes do dataset** (Marco 3.1) — hoje cobertos
por mocks determinísticos com contrato idêntico ao de produção.

## Bugs encontrados e corrigidos durante o ciclo
1. **Fila presa ao event loop antigo** após reinício do serviço (asyncio.Queue) —
   corrigido recriando a fila no startup (`queue_manager.py`).
2. **camera_streaming.js quebrava fora do navegador** — guardas `IS_BROWSER` adicionadas.

## Riscos conhecidos (não bloqueantes)
- Acurácia real de detecção/OCR depende do modelo customizado (Marco 3.1) — mocks não medem acurácia de campo.
- Rate limiting e cache em memória: trocar por Redis antes de múltiplas instâncias.

## Artefatos
- [test_results.md](test_results.md) — saída da execução
- [coverage_report/index.html](coverage_report/index.html) — cobertura navegável
