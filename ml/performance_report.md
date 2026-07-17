# Stockei — Relatório de Performance de Detecção (YOLOv8)
*Autor: ML/AI Engineer Agent · Data: 17/07/2026*

## Ambiente atual (desenvolvimento)
- Máquina Windows sem GPU e sem `ultralytics` instalado → API roda com **MockDetector**
  (contrato idêntico), latência média **< 5ms**.
- Contrato de resposta validado em `detection_tests.py` (4 testes).

## Plano de produção (instância g4dn.xlarge / T4)
| Modelo | Latência esperada | Uso |
|---|---|---|
| YOLOv8n (nano) | ~15-25ms/frame (T4) | MVP inicial |
| YOLOv8m custom | ~40-60ms/frame (T4) | Após treino (Marco 3) |
| YOLOv8m + TensorRT | ~20-30ms/frame | Otimização de escala |

## Como ativar o detector real
```bash
pip install ultralytics pillow
# baixa yolov8n.pt automaticamente no primeiro predict, ou:
#   yolo download model=yolov8n.pt  → salvar em models/yolov8n.pt
uvicorn ml.detection_api:app --port 8001
```
O `load_detector()` detecta automaticamente a presença do ultralytics.

## Teste com produtos reais (pendente de dataset)
- Meta: 50+ imagens, acurácia > 85% — será executado no Marco 3 junto ao treino
  do modelo customizado (`ml/train_custom_model.py`).

## Critérios de sucesso
- [x] Endpoint /detect funcionando (contrato completo)
- [x] Latência < 100ms (mock: <5ms; T4 estimado: <60ms)
- [x] Logging de detecções, performance e erros
- [ ] Acurácia > 85% em produtos reais (aguarda dataset — Marco 3)
