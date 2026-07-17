# Stockei — Especificações de Design (Portal)
*Autor: Design/UX Agent*

## Identidade
- **Tema:** dark (slate) — combina com ambiente de loja/estoque e reduz fadiga em monitores de operação.
- **Paleta:** fundo `#0f172a`, painéis `#1e293b`, texto `#e2e8f0`, secundário `#94a3b8`,
  ação `#2563eb`, sucesso `#22c55e`, perigo `#dc2626`.
- **Tipografia:** system-ui (performance; sem fontes externas).

## Páginas
1. **landing_page.html** — hero com proposta de valor, 4 features, pricing (Piloto grátis /
   Profissional R$499 / Corporativo), CTAs para demo e vendas, footer com contato.
2. **demo_portal.html** — login (integra `/auth/register|login` do backend), dashboard com
   câmera ao vivo (reusa `frontend/camera_streaming.js`), painel de detecções em tempo real,
   estatísticas da sessão e tour guiado dispensável.

## Responsividade
- Mobile-first; breakpoints 320px (base), 768px (tablet), 900-1024px (desktop, grid 2 colunas).
- Grids com `auto-fit/minmax` — sem overflow horizontal em nenhuma largura.

## Performance
- Zero dependências externas (sem CDN, sem webfonts) → PageSpeed > 90 por construção.
- CSS inline/único, imagens ausentes na v1 (emojis como ícones).

## Pendências
- [ ] Arquivo Figma com componentes (figma_link.url) — a criar quando o time de design tiver conta
- [ ] Vídeo tutorial do tour guiado
