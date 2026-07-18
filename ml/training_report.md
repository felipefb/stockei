# Stockei — Relatório de Treino do Modelo Customizado (Visão 1:N)
*Autor: ML/AI Engineer Agent · Atualizado: Prompt 1 (dataset + testes de estresse)*

## Status: FERRAMENTAL COMPLETO — treino aguardando fotos reais + GPU (Colab)

## Pipeline pronto
| Etapa | Ferramenta | Status |
|---|---|---|
| Coleta/organização | `ml/dataset_builder.py` (valida, normaliza 1280px, split 80/20, YAML) | ✅ |
| Anotação automática | `ml/annotator.py` (detector → labels YOLO + OCR de validade em sidecar) | ✅ |
| Análise de gôndola | `ml/shelf_analysis.py` (rupturas por vão ≥ 80% da largura média) | ✅ |
| Prateleiras sintéticas | `ml/synthetic_shelf.py` (densidade/ruptura/oclusão/datas controladas) | ✅ |
| Testes de estresse | `ml/stress_tests.py` — 9 testes | ✅ passando |
| Treino | `ml/train_custom_model.py` local · `docs/treino_colab.md` GPU grátis | ✅ pronto |

## Os 4 Testes de Estresse (Prompt 1)
| Teste | Cenário | Resultado atual |
|---|---|---|
| Densidade | 15 e 25 itens numa foto | ✅ pipeline validado (ground truth sintético) |
| Ruptura | buraco de 2 slots; gôndola cheia; gôndola vazia | ✅ detector de vãos correto nos 3 casos |
| Oclusão | caixa sobreposta a 2 vizinhas | ✅ tolerância de perda ≤ 2 itens |
| OCR simultâneo | 6 produtos com "VAL 12/2027" | ✅ RapidOCR leu ≥ 2 datas reais na imagem |

> Sem GPU, os testes usam o ground truth sintético como detecções — validam o
> pipeline inteiro (dataset → análise → OCR). Assim que `models/stockei_v1.pt`
> existir com `ultralytics` instalado, os MESMOS testes passam a medir o modelo real.

## Pendências (dependem de ação física)
- [ ] 50 fotos de prateleira por categoria (medicamentos, higiene, bebidas, mercearia)
- [ ] Revisão das anotações + marcação de rupturas no Roboflow
- [ ] Treino no Colab T4 (roteiro completo em `docs/treino_colab.md`)
- [ ] Metas: mAP > 0.80 · Precision > 0.90 · Recall > 0.85 · latência < 60ms (T4)
