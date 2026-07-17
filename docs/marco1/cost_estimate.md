# Stockei — Estimativa de Custos AWS (mensal)
*Autor: CTO Agent · Região: sa-east-1 · Fase MVP (5 clientes piloto)*

| Serviço | Configuração | Custo estimado (USD/mês) |
|---|---|---|
| ECS Fargate (api-core) | 2 tasks × 0.5 vCPU / 1GB | ~$35 |
| ECS Fargate (stream-gateway) | 2 tasks × 0.5 vCPU / 1GB | ~$35 |
| EC2 g4dn.xlarge (inference) | 1 instância, 12h/dia | ~$190 |
| RDS PostgreSQL | db.t4g.medium Multi-AZ + 50GB | ~$130 |
| ElastiCache Redis | cache.t4g.micro | ~$15 |
| ALB | 1 ALB + tráfego | ~$25 |
| S3 | 100GB + requests | ~$5 |
| ECR / CloudWatch / NAT | — | ~$70 |
| **Total MVP** | | **~$505/mês (~R$ 2.800)** |

## Escala (100 clientes beta)
- 3× g4dn.xlarge com auto-scaling: ~$1.400
- RDS db.r6g.large: ~$350
- Total estimado: **~$2.300/mês (~R$ 12.800)**

## Otimizações planejadas
1. Savings Plans (1 ano) → -30% em compute
2. Export TensorRT → 2-3× mais frames por GPU
3. Processar 3 FPS (não 30) → 90% menos inferência
4. Spot instances para treino de modelos
