# Stockei — Relatório de OCR (datas de validade)
*Autor: ML/AI Engineer Agent*

## Implementado
- **Engine** (`ocr_engine.py`): Tesseract + pré-processamento OpenCV (ROI → cinza →
  CLAHE → denoise → Otsu) com whitelist numérica e `--psm 7`. Fallback MockOCR para dev.
- **Validação** (`date_validation.py`): formatos DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY, MM/YYYY;
  normalização de confusões de OCR (O→0, I/L→1, S→5, B→8); detecção de produto vencido e
  datas implausíveis (>10 anos); sugestões de correção dia↔mês.
- **Endpoint**: `POST /ocr/date` → `{valid, date, raw, error, confidence, latency_ms}`.
- **Testes**: 9 casos em `ocr_tests.py`, latência < 50ms.

## Pendências (dependem de dados reais)
- [ ] Coletar 500+ fotos de datas em embalagens reais
- [ ] Fine-tuning do Tesseract (treino LSTM) se acurácia < 95% no dataset real
- [ ] Medição de acurácia real em produção

## Como ativar OCR real
```bash
# instalar binário Tesseract (Windows: instalador UB Mannheim) e:
pip install pytesseract opencv-python numpy
```
