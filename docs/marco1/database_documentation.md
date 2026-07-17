# Stockei — Documentação do Banco de Dados
*Autor: Backend Engineer Agent · PostgreSQL 15 (SQLite em dev/testes)*

## Diagrama ER (ASCII)

```
customers 1--N stores 1--N cameras
                 |1--N products 1--1 inventory
                 |               1--N movements N--1 users
                 |1--N people
movements 1--N movement_tracking N--1 people
```

## Entidades

| Tabela | Propósito | Índices principais |
|---|---|---|
| users | Autenticação e autoria de movimentações | email (unique) |
| customers | Clientes (empresas) | cnpj (unique) |
| stores | Lojas por cliente | customer_id |
| cameras | Câmeras por loja, status/last_seen | store_id |
| products | Catálogo por loja | (store_id, sku) unique, name |
| inventory | Estoque atual por produto | product_id (unique) |
| movements | Entradas/saídas/ajustes | (product_id, timestamp), timestamp |
| people | Funcionários + face encoding | store_id |
| movement_tracking | Quem movimentou o quê (confiança da IA) | movement_id, timestamp |

## Decisões
- **Fonte de verdade:** `backend/models.py` (SQLAlchemy 2.0) + migrations Alembic em `backend/migrations/`.
- **Índices:** todas as FKs indexadas; `movements` composto (product_id, timestamp) para consultas de histórico; `products` unique (store_id, sku).
- **Constraints:** unique em email, cnpj, inventory.product_id; FKs com integridade referencial.
- **Particionamento futuro:** `movements` por mês quando ultrapassar 10M linhas.

## Migrations
```bash
# Aplicar
alembic -c backend/alembic.ini upgrade head
# Rollback
alembic -c backend/alembic.ini downgrade -1
```

## Backup (produção AWS)
- RDS backup automático diário, retenção 30 dias (configurado no Terraform)
- Teste de restore trimestral documentado no runbook de DevOps
