# Stockei — Lista de Bugs
*Autor: Product Manager Agent · Priorização: P0 crítico · P1 alto · P2 médio · P3 baixo*

## Abertos
| ID | Descrição | Origem | Prioridade | Responsável | Status |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Corrigidos (histórico do desenvolvimento)
| ID | Descrição | Prioridade | Correção |
|---|---|---|---|
| BUG-001 | Fila de frames presa ao event loop antigo após reinício | P1 | `queue_manager.py`: fila recriada no startup |
| BUG-002 | camera_streaming.js quebrava fora do navegador (testes Node) | P3 | guardas `IS_BROWSER` |

## Processo
1. Reproduzir → registrar aqui com passos e logs
2. P0/P1: correção antes de qualquer feature nova
3. Toda correção acompanha teste de regressão na suíte pytest
