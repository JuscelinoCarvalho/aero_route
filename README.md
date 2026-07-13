# AeroRoute ✈

Calculadora de **rotas, tempo e combustível de voo**. Informe origem e destino
(código ICAO/IATA ou cidade), escolha a aeronave e veja distância great-circle,
rumo, tempo estimado e consumo de combustível — com a rota desenhada no mapa.

Feito com **Python + FastAPI**. Dados de aeroportos: [OurAirports](https://ourairports.com/data/) (domínio público).

## Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
# abra http://127.0.0.1:8000
```

## Estrutura

```
app/
  main.py       API FastAPI + serve o frontend
  calc.py       distância, rumo, tempo, combustível (funções puras)
  aircraft.py   perfis de aeronaves (velocidade/consumo) — fácil de refinar
  airports.py   carga e busca na base de aeroportos
  seo.py        gera as páginas SEO por rota (pt/en/es) + tag GA4/CMP no <head>
  i18n.py       traduções e localização das páginas estáticas
  data/airports.csv
static/
  index.html, style.css, app.js   frontend (mapa Leaflet + autocomplete)
  vendor/leaflet/                  Leaflet auto-hospedado (JS/CSS/imagens)
```

> O Leaflet é servido localmente (não via CDN) de propósito: o autoblocking do
> CMP bloqueia scripts de terceiros até o consentimento, e isso deixava `L`
> indefinido e quebrava o mapa. Como primeira-parte, ele carrega sempre. Os
> **tiles** (`basemaps.cartocdn.com`) seguem externos — precisam ser marcados como
> funcionais/essenciais no painel do consentmanager, senão o mapa fica vazio.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | status e nº de aeroportos carregados |
| GET | `/api/aircraft` | lista de aeronaves disponíveis |
| GET | `/api/airports/search?q=` | busca por código/nome/cidade |
| GET | `/api/route?origin=&dest=&aircraft=` | cálculo completo da rota |

## Monetização

- **AdSense**: descomente o script no `<head>` do `index.html` e preencha o bloco `.ad-slot` após aprovação.
- **Afiliados**: troque os links em `.affiliates` por seus links reais.

## Analytics e consentimento (GA4 + CMP)

Toda página envia dados ao **Google Analytics 4** (`G-7C0B22Z8EC`) com dimensões que
permitem **segmentar receita por idioma e por rota**. Um **Consent Manager (CMP)**
carrega antes da tag do Google para atender GDPR/ePrivacy (usuários do EEE).

### Onde fica a tag

A tag é injetada em **dois** lugares — não há milhares de HTMLs para editar:

- **Páginas geradas por rota** (`/rota/...`, `/voo/...`, `/tempo/...`, etc.): em
  `app/seo.py` — constante `CMP` (banner) + função `gtag_block(lang, content_group, route)`.
  Cada geradora passa seu contexto, então pt/en/es da **mesma rota** compartilham o
  mesmo `page_route`.
- **7 páginas estáticas do app** (`static/*.html`): CMP + gtag no `<head>`, com
  `content_group` fixo por página e `page_language` lido de `document.documentElement.lang`.

Ordem obrigatória no `<head>`: **CMP → gtag** (o autoblocking precisa carregar antes
para bloquear o rastreamento até o consentimento).

### Dimensões enviadas

| Parâmetro | O que é | No GA4 |
|-----------|---------|--------|
| `content_group` | Seção da página (`rota`, `voo`, `tempo`, `app-home`…) | Dimensão **nativa** "Grupo de conteúdo" — funciona sem registrar |
| `page_language` | Idioma do **conteúdo** (`pt`/`en`/`es`) | Dimensão personalizada — **precisa registrar** |
| `page_route` | Slug da rota / ICAO (unifica os 3 idiomas) | Dimensão personalizada — **precisa registrar** |

### Configuração manual no painel (uma vez)

1. **Registrar as dimensões**: GA4 → Administrador → Definições personalizadas →
   Criar dimensão. `page_language` → "Idioma da página"; `page_route` → "Rota";
   ambas escopo **Evento**. Não é retroativo — registre antes de querer os dados.
2. **Consent Mode v2**: ative o **Google Consent Mode** no painel do
   consentmanager.net. O script sozinho só bloqueia; o Consent Mode é o que libera
   anúncios do AdSense no EEE. Não codar `gtag('consent','default',...)` na mão —
   conflita com o que o CMP injeta.
3. **Vincular AdSense ↔ GA4**: Administrador → Vinculações de produtos, para a
   métrica de receita aparecer nos relatórios.

Depois disso, em **Explorar** cruze **Rota × Idioma da página × Receita**.

> Ao trocar a propriedade GA4 ou o ID do CMP, atualize `GTAG_ID`/`CMP` em
> `app/seo.py` e o `<head>` dos `static/*.html`.

## Avisos

As estimativas de tempo e combustível são **didáticas** (cruzeiro padrão, sem
vento, sem peso/altitude reais). **Não usar para planejamento operacional.**

## Próximos passos (ideias)

- Considerar vento e fusos horários (hora de chegada local)
- Mais aeronaves e perfis validados por piloto
- Plano "pro": exportar PDF, rotas em lote, API com chave
- Cache da base e busca por proximidade no mapa
