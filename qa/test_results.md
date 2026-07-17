# Stockei — Resultados de Execução dos Testes
*Execução: 17/07/2026 · `python -m coverage run -m pytest`*

```
50 passed, 4 warnings in 10.00s
Cobertura (backend/* + ml/*): 91%
```

| Suíte | Arquivo | Testes |
|---|---|---|
| Agentes | tests/test_agents.py, tests/test_orchestration.py | 13 |
| APIs base | backend/tests/test_api.py | 8 |
| E2E frames | backend/tests/test_e2e_frames.py | 5 |
| Detecção | ml/detection_tests.py | 4 |
| OCR | ml/ocr_tests.py | 9 |
| Tracking | ml/tracking_tests.py | 11 |

Comando de reprodução:
```bash
python -m coverage run -m pytest
python -m coverage html --include="backend/*,ml/*" -d qa/coverage_report
```
