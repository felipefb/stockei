# Stockei — Relatório de Rastreamento de Objetos
*Autor: ML/AI Engineer Agent*

## Implementado
- **`tracking_engine.py`** — tracker por associação IoU (núcleo do SORT): IDs estáveis
  entre frames, associação greedy por classe, tolerância a oclusão (10 frames),
  expiração de tracks que saem do quadro.
- **`counting_logic.py`** — contagem única por sessão: cada track_id conta uma vez,
  filtro `min_age=3` elimina falsos positivos de 1-2 frames.
- **Testes** — 11 casos em `tracking_tests.py`: estabilidade de ID, oclusão, saída de
  quadro, câmera em movimento, sem contagem duplicada, latência O(n·m) por frame (<1ms
  para dezenas de objetos).

## Upgrade para DeepSORT (produção/GPU)
`pip install deep-sort-realtime` → substituir `ObjectTracker` mantendo a interface
`update(detections)`. Ganho: re-identificação por aparência em oclusões longas e
cruzamento de objetos. Recomendado quando houver GPU no inference-service.

## Critérios de sucesso
- [x] Tracking com IDs estáveis
- [x] Contagem sem duplicação (testes de 10 frames do mesmo objeto → 1 contagem)
- [x] Funciona com movimento gradual de câmera
- [x] Latência < 100ms (tracker puro Python: <1ms/frame para o volume do MVP)
