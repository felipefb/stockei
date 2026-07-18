# Stockei — Prompts Complementares (10–16) e Ordem Integrada de Execução

Complementam os Prompts 1–9 de `stockei_prompts_colaborativos_v2.pdf`. Foram desenhados
a partir dos módulos que apps de inventário consolidados oferecem (Conferência, Perdas,
Troca Interna, Transferência, Posição de Estoque, Configurações/Permissões) e das
lacunas atuais do produto — mantendo a visão "Sonho Grande": a câmera audita, a IA
decide, o lojista só aprova.

---

## PROMPT 10 — Conferência de Recebimento (NF-e vs Câmera)

**Agentes:** Backend Engineer Agent (execução) · Pricing/Data Agent (planejamento) · QA Agent (validação)

```
# STOCKEI — TAREFA: Conferência de Recebimento (NF-e vs Câmera)

## Contexto
O lojista recebe mercadoria e hoje confere item a item no papel. O Stockei
deve importar o XML da NF-e de entrada e transformar a conferência num
checklist vivo: a câmera lê os produtos chegando e o sistema marca
automaticamente o que bateu, o que faltou e o que veio a mais.
Reaproveita o nfe_parser.py do Prompt 5 (Smart Pricing).

## Planejamento (Pricing/Data Agent)
1. Especificar docs/receiving_spec.md: estados do item (pendente,
   conferido, divergente, excedente) e regras de fechamento da conferência.

## Execução (Backend Engineer Agent)
1. Modelo ReceivingSession + ReceivingItem (nfe_key, expected_qty, checked_qty).
2. POST /receiving/upload-xml → cria a sessão a partir da NF-e.
3. POST /receiving/{id}/check → dá baixa por EAN escaneado (câmera).
4. POST /receiving/{id}/close → gera movimentos de entrada + relatório
   de divergências; alimenta o Smart Pricing com os custos da nota.
5. Tela portal/receiving.html: checklist com progresso e divergências.

## Validação (QA Agent)
1. Testes: nota com 10 itens, conferir 8, 1 divergente, 1 excedente.
2. Critério: fechamento gera exatamente os movimentos corretos no estoque.

## Entregável
- Módulo de conferência completo + tela; commit "feat: conferencia de recebimento NF-e vs camera"
```

---

## PROMPT 11 — Gestão de Perdas e Quebras

**Agentes:** Backend Engineer Agent (execução) · CFO Agent (planejamento) · Compliance Agent (validação)

```
# STOCKEI — TAREFA: Gestão de Perdas e Quebras

## Contexto
Perda é o indicador que o dono mais sente no bolso. Hoje o Stockei alerta
validade, mas não registra a perda consumada nem seu motivo. Este módulo
fecha o ciclo: registrar perda com motivo, valorizar em R$ e alimentar o
dashboard com o índice de perdas (% do faturamento em estoque).

## Planejamento (CFO Agent)
1. Definir taxonomia de motivos: vencimento, avaria, furto, erro de
   cadastro, consumo interno. Meta de referência do varejo: perdas < 2%.

## Execução (Backend Engineer Agent)
1. Novo tipo de movimento "loss" com campo reason (enum) e note.
2. POST /losses → registra perda (baixa estoque + valoriza pelo preço).
3. GET /losses/report?period= → total por motivo, produto e loja.
4. Integração com validade: 1 clique "Registrar perda" nos itens VENCIDOS
   do dashboard. Painel "Perdas do mês" com R$ e % por motivo.

## Validação (Compliance Agent)
1. Perda exige usuário autenticado registrado no movimento (auditoria).
2. Testes de relatório por período e por motivo.

## Entregável
- Módulo de perdas + painel; commit "feat: gestao de perdas com motivos e relatorio"
```

---

## PROMPT 12 — Transferência entre Lojas e Troca Interna

**Agentes:** Backend Engineer Agent (execução) · Tech Architect Agent (planejamento) · QA Agent (validação)

```
# STOCKEI — TAREFA: Transferência entre Lojas e Troca Interna

## Contexto
O multi-loja já existe, mas mover estoque entre lojas hoje exige saída
manual numa e entrada manual na outra. O módulo cria a transferência como
operação atômica com rastreio: loja A envia, loja B confere na chegada
(pela câmera), e o sistema só efetiva o que foi conferido.

## Planejamento (Tech Architect Agent)
1. docs/transfer_spec.md: estados (rascunho, em trânsito, recebida,
   divergente) e o que acontece com o saldo em cada estado.

## Execução (Backend Engineer Agent)
1. Modelo Transfer + TransferItem (from_store, to_store, qty_sent, qty_received).
2. POST /transfers → cria e reserva o saldo na origem.
3. POST /transfers/{id}/receive → baixa por EAN escaneado no destino.
4. POST /transfers/{id}/close → efetiva entradas/saídas; divergências viram
   alerta (ligação futura com o Robô de Conciliação do Prompt 4).
5. Tela portal/transfers.html com os dois lados do fluxo.

## Validação (QA Agent)
1. Teste: transferir 10, receber 9 → origem -10, destino +9, 1 divergência.

## Entregável
- Módulo de transferências; commit "feat: transferencia entre lojas com conferencia por camera"
```

---

## PROMPT 13 — Papéis, Permissões e Auditoria (Configurações)

**Agentes:** Security Agent (planejamento) · Backend Engineer Agent (execução) · Compliance Agent (validação)

```
# STOCKEI — TAREFA: Papéis, Permissões e Auditoria

## Contexto
Hoje todo usuário pode tudo. Para operar com funcionários reais (e para a
rastreabilidade do Prompt 6 fazer sentido), precisamos de papéis: dono
(tudo), gerente (opera + relatórios), operador (só conta/confere). Toda
ação sensível deve ficar auditável: quem, o quê, quando.

## Planejamento (Security Agent)
1. Matriz de permissões por endpoint em docs/permissions_matrix.md.

## Execução (Backend Engineer Agent)
1. Usar o campo role existente em users (owner/manager/operator) com
   dependency require_role() nos endpoints sensíveis (preços, perdas,
   exclusões, configurações).
2. Tabela audit_log (user_id, action, entity, payload_resumo, timestamp)
   preenchida por middleware nas mutações.
3. Tela portal/settings.html: gestão de usuários da loja e papéis.
4. GET /audit?entity=&user=&period= para consulta.

## Validação (Compliance Agent)
1. Testes: operador tenta alterar preço → 403; ação sensível sempre gera
   registro de auditoria; LGPD: log não guarda dados pessoais além do necessário.

## Entregável
- RBAC + auditoria + tela de configurações; commit "feat: papeis, permissoes e trilha de auditoria"
```

---

## PROMPT 14 — PWA: Stockei Instalável no Celular

**Agentes:** Frontend Engineer Agent (execução) · Design/UX Agent (planejamento) · QA Agent (validação)

```
# STOCKEI — TAREFA: PWA instalável (o "app" do lojista)

## Contexto
O piloto roda no navegador do celular via túnel. Para parecer produto de
verdade (como os apps concorrentes de inventário), o portal deve ser um
PWA: ícone na tela inicial, tela cheia sem barra do navegador, e um menu
inicial em grade com os módulos (Inventário, Conferência, Perdas,
Transferências, Dashboard, Configurações) — estilo hub, um toque por tarefa.

## Planejamento (Design/UX Agent)
1. Desenhar o hub portal/index.html na identidade Scanner: cards em grade
   2 colunas, ícone + rótulo, badge de pendências (ex.: "3 vencendo").

## Execução (Frontend Engineer Agent)
1. manifest.json (nome, ícones 192/512, display: standalone, theme lima/grafite).
2. service worker mínimo: cache do shell estático (HTML/CSS/JS) — dados
   sempre online; tela offline amigável.
3. Hub portal/index.html com navegação para todos os módulos.
4. Meta tags iOS (apple-touch-icon, status bar) — Safari não instala via
   manifest sozinho.

## Validação (QA Agent)
1. Lighthouse PWA instalável; teste real de "Adicionar à Tela de Início"
   em iOS e Android; navegação completa em tela cheia.

## Entregável
- PWA instalável com hub de módulos; commit "feat: PWA instalavel com hub de modulos"
```

---

## PROMPT 15 — Alertas Proativos (WhatsApp/E-mail)

**Agentes:** Backend Engineer Agent (execução) · Customer Success Agent (planejamento) · QA Agent (validação)

```
# STOCKEI — TAREFA: Alertas proativos por WhatsApp/E-mail

## Contexto
O valor do Stockei é agir antes do prejuízo — mas hoje os alertas só
aparecem se o lojista abrir o dashboard. O sistema deve empurrar um
resumo diário e alertas críticos pelo canal onde o lojista vive: WhatsApp
(via Evolution API/Twilio) com fallback e-mail (SMTP).

## Planejamento (Customer Success Agent)
1. Definir os 3 alertas que importam (sem spam):
   - Diário 08h: "Bom dia! 3 itens vencem esta semana (R$ 142). 2 itens zerados."
   - Crítico: item VENCIDO com estoque > 0.
   - Ruptura: produto campeão de movimento zerou.

## Execução (Backend Engineer Agent)
1. backend/notifications/ com providers plugáveis (whatsapp, email, console).
2. Scheduler (APScheduler) para o resumo diário; triggers nos eventos críticos.
3. Preferências por usuário em /settings (canal, horário, tipos).
4. Template das mensagens com link direto para o painel relevante.

## Validação (QA Agent)
1. Testes com provider "console" (sem custo); simulação dos 3 cenários.
2. Critério: nenhum alerta duplicado no mesmo dia para o mesmo item.

## Entregável
- Módulo de notificações; commit "feat: alertas proativos whatsapp/email"
```

---

## PROMPT 16 — Sessões de Inventário e Posição de Estoque

**Agentes:** Backend Engineer Agent (execução) · Product Manager Agent (planejamento) · QA Agent (validação)

```
# STOCKEI — TAREFA: Sessões de Inventário e Posição de Estoque

## Contexto
A contagem hoje atualiza o saldo direto. Falta o conceito de "inventário"
como evento auditável: abrir sessão, contar (câmera), comparar com o saldo
teórico, aprovar ajustes e guardar o histórico — a "Posição de Estoque"
que todo ERP espera receber.

## Planejamento (Product Manager Agent)
1. docs/inventory_session_spec.md: ciclo abrir → contar → revisar
   divergências → aprovar (gera ajustes) ou descartar; acuracidade (%
   de itens sem divergência) como métrica do evento.

## Execução (Backend Engineer Agent)
1. Modelo InventorySession + InventoryCount (expected, counted, diff).
2. POST /inventory/sessions → abre; POST .../counts → registra contagens
   da câmera; POST .../approve → gera movimentos de ajuste em lote.
3. GET /inventory/position?date= → fotografia do estoque em qualquer data
   (reconstruída pelos movimentos) com export CSV.
4. Tela portal/inventory.html: sessões, divergências e acuracidade.

## Validação (QA Agent)
1. Teste: sessão com 5 itens, 2 divergentes → aprovar gera exatamente 2
   ajustes; posição de estoque em data retroativa bate com os movimentos.

## Entregável
- Sessões de inventário + posição histórica; commit "feat: sessoes de inventario e posicao de estoque"
```

---

# Ordem Integrada de Execução (Prompts 1–16)

A lógica: primeiro o **diferencial** (visão 1:N) e a **validação com pilotos**; depois os
módulos que transformam a demo em **operação diária completa** (é o que os pilotos vão
pedir na semana 1); então **automação e dinheiro** (pricing, conciliação); por fim
**escala e defesa**.

| # | Prompt | Origem | Urgência | Por quê nesta posição |
|---|--------|--------|----------|----------------------|
| 1 | P1 — Dataset YOLOv8 (Visão 1:N) | v2 | 🔴 Imediata | O diferencial core; tudo se apoia nele |
| 2 | **P14 — PWA instalável** | novo | 🔴 Imediata | Pré-requisito do piloto no celular: sem "app", não há uso diário |
| 3 | P3 — Onboarding Pilotos | v2 | 🔴 Imediata | Validação do "Momento Uau" com o PWA na mão |
| 4 | **P16 — Sessões de Inventário** | novo | 🔴 Alta | O módulo nº 1 do lojista (o print de referência começa nele) |
| 5 | **P10 — Conferência de Recebimento** | novo | 🔴 Alta | 2º fluxo mais frequente da loja; gera custos p/ o pricing |
| 6 | **P11 — Perdas e Quebras** | novo | 🟡 Alta | Fecha o ciclo da validade que já existe; ROI visível |
| 7 | P5 — Precificação Inteligente | v2 | 🟡 Alta | Usa os custos capturados no P10; automação de margem |
| 8 | **P13 — Papéis e Auditoria** | novo | 🟡 Média | Necessário antes de funcionários reais usarem (P6 depende) |
| 9 | **P12 — Transferência entre Lojas** | novo | 🟡 Média | Completa o multi-loja; prepara a conciliação |
| 10 | P4 — StockeiConnect Autônomo | v2 | 🟡 Média | O "cérebro": conciliação ERP ↔ câmera (usa P10/P12/P16) |
| 11 | **P15 — Alertas Proativos** | novo | 🟡 Média | Com os módulos acima, os alertas têm o que avisar |
| 12 | P6 — Rastreabilidade de Pessoas | v2 | 🟡 Média | Exige P13 (identidade/papéis) e LGPD madura |
| 13 | P2 — Infraestrutura AWS | v2 | 🟡 Média | Produção real quando os pilotos validarem o produto |
| 14 | P7 — Design System | v2 | 🔵 Baixa | Refinamento contínuo sobre a identidade Scanner |
| 15 | P8 — Marketing Digital | v2 | 🔵 Baixa | Aquisição após prova com pilotos |
| 16 | P9 — Agentes Evolutivos | v2 | 🔵 Contínuo | Inteligência estratégica permanente |

**Regras de dependência (resumo):** P10 alimenta P5 (custos da NF-e) · P13 antecede P6
(identidade antes de rastrear pessoas) · P4 consome P10/P12/P16 (só concilia o que os
módulos registram) · P15 só faz sentido após P11/P16 (precisa de eventos para alertar).
