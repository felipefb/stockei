# Stockei — Decisão de Stack Técnico
*Autor: CTO Agent · Data: 17/07/2026 · Status: APROVADO*

## 1. Framework Web: **FastAPI** ✅

| Critério | FastAPI | Django | Flask |
|---|---|---|---|
| Performance (async) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Validação nativa (Pydantic) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| OpenAPI automático | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| WebSocket nativo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Curva de aprendizado | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Justificativa:** Stockei processa frames de vídeo em tempo real (3-5 FPS por câmera). FastAPI oferece async nativo para I/O intensivo, WebSockets para resultados em tempo real, validação automática via Pydantic e documentação OpenAPI gratuita. Django traria ORM/admin que não precisamos no serviço de inferência; Flask exigiria montar tudo manualmente.

**Contras aceitos:** ecossistema menor que Django; sem admin pronto (mitigado pelo portal próprio).

## 2. Banco de Dados: **PostgreSQL** ✅

**Justificativa:** Dados do Stockei são fortemente relacionais (clientes → lojas → câmeras → produtos → inventário → movimentações). Precisamos de transações ACID para contagens de estoque, `JSONB` para payloads de detecção flexíveis, e extensões (`pgvector` futuro para face encodings). MongoDB perderia integridade referencial e joins eficientes.

**Escalabilidade:** particionamento de `movements` por data; read replicas para dashboards; RDS Multi-AZ.

## 3. Cloud Provider: **AWS** ✅

**Justificativa:** maior maturidade no Brasil (região sa-east-1 São Paulo → latência baixa para câmeras), ECS/ECR maduros, RDS PostgreSQL gerenciado, instâncias GPU (g4dn) para inferência YOLOv8, SageMaker opcional para treino.

**Serviços:** VPC, ECS Fargate + EC2 g4dn (inferência), ECR, RDS PostgreSQL, S3 (frames/datasets), ALB, CloudWatch, CodePipeline, ElastiCache Redis (fila/cache).

Estimativa de custo: ver [cost_estimate.md](cost_estimate.md).

## 4. Arquitetura: **Microserviços (moderados)** ✅

3 serviços — não nano-serviços:

1. **api-core** — auth, CRUD, inventário (FastAPI + PostgreSQL)
2. **inference-service** — YOLOv8 + OCR + tracking (FastAPI + GPU)
3. **stream-gateway** — WebSocket, fila de frames (FastAPI + Redis)

**Justificativa:** a inferência tem perfil de recurso (GPU, memória) totalmente diferente do CRUD; separá-la permite escalar GPUs independentemente. Comunicação: REST interno + Redis queue; eventos via Redis pub/sub.

## 5. IA/ML: **PyTorch + YOLOv8 (Ultralytics)** ✅

- **PyTorch** sobre TensorFlow: Ultralytics YOLOv8 é PyTorch-nativo, comunidade maior em detecção, export para ONNX/TensorRT.
- **Deployment:** modelo carregado no boot do inference-service; export TensorRT em produção para latência < 100ms.
- **GPU:** desenvolvimento CPU (YOLOv8n), produção g4dn.xlarge (T4). OCR: Tesseract + OpenCV. Tracking: DeepSORT.

## Decisão Final

| Camada | Escolha |
|---|---|
| Web framework | FastAPI |
| Banco | PostgreSQL 15 (SQLite em dev/testes) |
| ORM / Migrations | SQLAlchemy 2 / Alembic |
| Cloud | AWS (sa-east-1) |
| Arquitetura | 3 microserviços |
| ML | PyTorch + YOLOv8 + Tesseract + DeepSORT |
| Cache/Fila | Redis |
| Frontend | Vue.js 3 + WebRTC |
