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
  data/airports.csv
static/
  index.html, style.css, app.js   frontend (mapa Leaflet + autocomplete)
```

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

## Avisos

As estimativas de tempo e combustível são **didáticas** (cruzeiro padrão, sem
vento, sem peso/altitude reais). **Não usar para planejamento operacional.**

## Próximos passos (ideias)

- Considerar vento e fusos horários (hora de chegada local)
- Mais aeronaves e perfis validados por piloto
- Plano "pro": exportar PDF, rotas em lote, API com chave
- Cache da base e busca por proximidade no mapa
