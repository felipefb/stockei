# Stockei — Relatório de Treino do Modelo Customizado
*Autor: ML/AI Engineer Agent · Status: PIPELINE PRONTO — treino real pendente de dataset*

## Pipeline implementado (`train_custom_model.py`)
1. **Dataset** — formato YOLO, split 70/20/10, `build_dataset_yaml()` gera a config.
2. **Anotação** — recomendado Roboflow (export "YOLOv8"), alternativa LabelImg.
3. **Treino** — YOLOv8m, 100 epochs, lr 0.001, batch 16, GPU, augmentation (HSV, flip, mosaic, scale).
4. **Validação** — mAP50/precision/recall extraídos automaticamente; gate de aprovação:
   mAP > 0.85, Recall > 0.85, Precision > 0.90.
5. **Export** — melhor checkpoint → `models/custom_model.pt` (a `detection_api` usa via
   `STOCKEI_MODEL_PATH=models/custom_model.pt`).

## Pendências (dependem de coleta física)
- [ ] Coletar 1000+ imagens de produtos (ângulos, iluminações, câmeras diferentes)
- [ ] Anotar bounding boxes + classes no Roboflow
- [ ] Executar treino em GPU (g4dn.xlarge ~2-4h para 100 epochs)
- [ ] Registrar métricas reais em `metrics.json`

## Comando de execução
```bash
pip install ultralytics
python ml/train_custom_model.py --data ml/dataset/stockei.yaml --epochs 100
```
