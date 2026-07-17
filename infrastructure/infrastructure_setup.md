# Stockei — Setup de Infraestrutura AWS
*Autor: DevOps Agent · Data: 17/07/2026*

> **Status:** Código IaC pronto (`terraform/`). A aplicação real depende de conta AWS ativa —
> passos manuais marcados como [MANUAL] devem ser feitos pelo proprietário da conta.

## 1. Conta e Organização
- [MANUAL] Criar conta AWS e ativar MFA no usuário root
- [MANUAL] Criar billing alert (Budget de $600/mês para MVP)
- [MANUAL] Criar usuário IAM `stockei-admin` (sem uso do root) e role `stockei-deploy` para CI/CD (OIDC GitHub Actions)

## 2. Provisionamento (Terraform)
```bash
cd infrastructure/terraform
terraform init
terraform plan  -var db_username=stockei -var db_password=<SECRET>
terraform apply -var db_username=stockei -var db_password=<SECRET>
```

Recursos criados:
| Recurso | Detalhe |
|---|---|
| VPC | 10.0.0.0/16, 2 subnets públicas + 2 privadas, NAT Gateway |
| Security Groups | ALB (443) → app (8000) → db (5432), least-privilege |
| RDS PostgreSQL 15 | db.t4g.medium, Multi-AZ, backup 30 dias |
| ECS Cluster | Container Insights habilitado |
| ECR | 3 repositórios (api-core, stream-gateway, inference-service) |
| ALB | público, HTTPS |
| S3 | bucket de assets (frames, datasets, modelos) |
| CloudWatch | log group /stockei/app (30d) + alarme CPU RDS > 80% |

## 3. CI/CD
Pipeline em [ci_cd_pipeline.yaml](ci_cd_pipeline.yaml) (GitHub Actions):
`push main` → testes pytest → build Docker → push ECR → deploy ECS.
- [MANUAL] Configurar secret `AWS_DEPLOY_ROLE` no GitHub e copiar o workflow para `.github/workflows/`.

## 4. Monitoramento
- Logs de todas as tasks ECS → CloudWatch `/stockei/app`
- Alarme: CPU RDS > 80% por 10min
- Dashboard: criar em CloudWatch após primeiro deploy (URL será registrada em `monitoring_dashboard.url`)

## Critérios de Sucesso
- [x] IaC completo e versionado
- [x] Pipeline CI/CD definido
- [x] Monitoramento definido (logs + alarms)
- [ ] `terraform apply` executado (aguarda conta AWS) [MANUAL]
