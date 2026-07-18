# Stockei — Treinar o YOLOv8 de graça no Google Colab

O treino do modelo 1:N precisa de GPU. Sem pagar AWS, o caminho é o Colab
(GPU T4 gratuita, sessões de ~3h — suficiente para o dataset do piloto).

## Passo a passo (~30 min de trabalho + 1-2h de treino)

### 1. Montar o dataset no PC
```bash
# jogue fotos de PRATELEIRAS (não produtos isolados) em:
#   ml/dataset/raw/medicamentos/  ml/dataset/raw/higiene/
#   ml/dataset/raw/bebidas/       ml/dataset/raw/mercearia/
python ml/dataset_builder.py     # organiza, divide train/val, gera stockei.yaml
python ml/annotator.py           # gera labels automáticos (ponto de partida)
```
Meta do Prompt 1: **50 fotos por categoria (200 no total)**, celular na horizontal,
1–2 m da gôndola, iluminação variada.

### 2. Revisar as anotações (importante!)
As caixas automáticas vêm do detector genérico — revise no [Roboflow](https://roboflow.com)
(grátis): crie um projeto, suba `ml/dataset/images` + `ml/dataset/labels`, corrija as
caixas e **anote as rupturas** (classe `ruptura`) manualmente. Exporte como "YOLOv8".

### 3. Treinar no Colab
1. Abra https://colab.research.google.com → novo notebook → Ambiente de execução →
   **Alterar tipo → GPU (T4)**.
2. Compacte e suba o dataset (`ml/dataset/` → `dataset.zip`) para o Colab (ou Drive).
3. Cole e rode:
```python
!pip -q install ultralytics
!unzip -q dataset.zip -d /content/dataset

from ultralytics import YOLO
model = YOLO("yolov8m.pt")
results = model.train(
    data="/content/dataset/stockei.yaml",
    epochs=100, imgsz=640, batch=16, lr0=0.001,
    project="/content/runs", name="stockei_v1",
)
print(results.box.map50, results.box.mp, results.box.mr)  # metas: >0.80 / >0.90 / >0.85
```
4. Baixe `/content/runs/stockei_v1/weights/best.pt` → salve como
   **`models/stockei_v1.pt`** no repositório.

### 4. Ativar no Stockei
```bash
pip install ultralytics pillow
# no .env:
STOCKEI_MODEL_PATH=models/stockei_v1.pt
```
Reinicie o servidor — `load_detector()` troca o mock pelo modelo real
automaticamente, e os testes de estresse (`ml/stress_tests.py`) passam a
validar o modelo de verdade.

### 5. Validar
```bash
python -m pytest ml/stress_tests.py -v
```
Critérios do Prompt 1: mAP > 0.80 · densidade 15+ itens · ruptura detectada ·
oclusão tolerada · OCR simultâneo.
