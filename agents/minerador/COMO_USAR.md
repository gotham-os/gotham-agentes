# Gotham Opportunity Researcher

Agente local para minerar oportunidades de oferta digital escalavel com evidencia, score, MVP minimo e teste de Meta Ads.

## O que ele aceita

Prioridade total para entrega digital:

- SaaS, micro-SaaS, API, automacao e agentes
- auditoria digital e servico productizado
- template, planilha, relatorio, data product
- ebook, curso, comunidade, newsletter
- MVP manual primeiro, software depois

Ele deve rejeitar produto fisico, estoque, logistica, operacao presencial e qualquer ideia que nao tenha comprador claro ou teste plausivel via Meta Ads.

## Fluxo diario simples

1. Jogue sinais em `data/seeds/first-test-signals.json` ou crie outro JSON no mesmo formato.
2. Rode o radar:

```powershell
python -m opportunity_researcher.cli run --input data/seeds/first-test-signals.json --out data/reports/first-test.md --json-out data/opportunities/first-test.json --kanban-out data/reports/first-test-kanban.html
```

Se voce estiver usando o runtime embutido que foi baixado neste projeto:

```powershell
.\.runtime\python\python.exe gotham_radar.py run --input data/seeds/first-test-signals.json --out data/reports/first-test.md --json-out data/opportunities/first-test.json --kanban-out data/reports/first-test-kanban.html
```

3. Abra o Kanban visual:

```powershell
Start-Process data/reports/first-test-kanban.html
```

Ou de dois cliques no arquivo `data/reports/first-test-kanban.html`.

4. Se quiser ver o relatorio em texto:

```powershell
Get-Content data/reports/first-test.md
```

5. Para cada oportunidade com `TESTAR AGORA`, crie um card no seu Kanban definitivo com:

- promessa
- publico
- provas
- MVP minimo
- criativos Meta Ads
- budget
- criterio de matar
- criterio de escalar

## Coletar trends

Quando Python estiver disponivel:

```powershell
python -m opportunity_researcher.cli collect-trends --geo BR --out data/raw/google-trends-br.json
```

Com o runtime local:

```powershell
.\.runtime\python\python.exe gotham_radar.py collect-trends --geo BR --out data/raw/google-trends-br.json
```

Isso coleta o RSS diario do Google Trends. Ele ainda nao transforma trend solta em oportunidade automaticamente; use como materia-prima para uma seed.

## Coletar Meta Ads Library com Playwright

Instale as dependencias Node uma vez:

```powershell
npm install
```

Rodada completa com Meta Ads:

```powershell
.\.runtime\python\python.exe gotham_radar.py round-with-meta-ads --seed data/seeds/live-round-2026-05-13.json --queries-file data/meta_ads_queries.json --out data/raw/meta-ads-live.json --merged-seed-out data/seeds/live-round-with-meta-ads.json --report-out data/reports/live-round-with-meta-ads.md --json-out data/opportunities/live-round-with-meta-ads.json --kanban-out data/reports/live-round-with-meta-ads-kanban.html
```

Durante a execucao, o terminal imprime logs assim:

```text
[radar] rodada completa com Meta Ads iniciada
[radar] etapa 1/6: coletar anuncios e sinais de distribuicao
[meta-ads] lendo queries: data/meta_ads_queries.json
[meta-ads] coleta real iniciada: 6 query(s), pais BR, max 12 ads/query
[meta-ads] [1/6] abrindo Meta Ads Library: "gestao de trafego" (...)
[meta-ads] [1/6] extraidos 8 cards, 8 ativos, 8 paginas, escala high
[meta-ads] inteligencia global: 3 grupo(s) de duplicacao/escala detectados
[radar] etapa 5/6: pontuando oportunidades
[radar] war room salvo: data/reports/live-round-with-meta-ads-war-room.html
```

Isso serve para voce saber se ele esta travado, qual query esta sendo pesquisada, quantos anuncios vieram, se achou duplicacao/escala e onde os arquivos finais foram salvos.

Por padrao, fontes criticas suspeitas nao sao puladas em silencio. Se a Meta Ads Library travar, der erro em todas as queries ou vier completamente vazia, o agente para e pergunta no terminal:

```text
[radar] Meta Ads Library travou ou veio vazio. O que fazer?
[r] tentar de novo com navegador visivel
[c] continuar a rodada marcando essa lacuna
[a] abortar para voce ajustar login/cookies/queries
```

Se voce estiver rodando em automacao sem terminal interativo, escolha a politica:

```powershell
--blocked-source-policy ask       # padrao: pergunta quando possivel
--blocked-source-policy stop      # aborta quando fonte critica travar
--blocked-source-policy continue  # continua, mas registra a lacuna nos logs
```

Abrir o Kanban:

```powershell
Start-Process data/reports/live-round-with-meta-ads-kanban.html
```

Abrir o War Room completo:

```powershell
Start-Process data/reports/live-round-with-meta-ads-war-room.html
```

## Super-run V2

O comando mais completo agora é:

```powershell
.\.runtime\python\python.exe gotham_radar.py super-run --blocked-source-policy ask
```

Ele tenta orquestrar:

- seed base de hipóteses e evidências;
- Meta Ads Library com filtro de relevância por oferta;
- Reddit com posts reais e métricas quando a fonte permitir;
- Google Trends RSS;
- scoring V2 com qualidade de fonte, densidade de provas e gates anti-viés;
- Markdown, JSON, Kanban e War Room.

Arquivos principais gerados:

```text
data/reports/super-run-v2-war-room.html
data/reports/super-run-v2.md
data/opportunities/super-run-v2.json
data/seeds/super-run-v2-seed.json
```

Se uma fonte crítica bloquear ou vier vazia, o agente deve perguntar o que fazer. Para rodar sem interação:

```powershell
.\.runtime\python\python.exe gotham_radar.py super-run --blocked-source-policy continue
```

### Regra V2 anti-dinheiro-queimado

Uma oportunidade só vira `TESTAR AGORA` se tiver evidência núcleo suficiente:

- dor real com métrica/post/review;
- distribuição relevante, não só cards aleatórios;
- prova de dinheiro ou demanda;
- qualidade média de evidência aceitável;
- densidade de provas de fontes diferentes.

Se a rodada vier fraca, o resultado correto é `NEEDS_MORE_EVIDENCE`, não uma lista bonita de ideias.

O mapa de fontes fica em `data/source_registry.json`. Ele separa fontes automatizadas, fontes assistidas/manual e limitações de cada uma.

Se a Meta bloquear, pedir login, captcha ou entregar DOM vazio, o coletor ainda salva status, screenshots/HTML em `data/raw/meta_ads_snapshots/` e gera sinal fraco. Isso evita falso positivo.

### O que ele entende como anuncio escalado/duplicado

O modulo Playwright agora procura provas em tres niveis:

- `scaled_duplicate_groups`: quando a propria Meta mostra algo como "3 anuncios usam esse criativo e esse texto".
- `cross_source_duplicate_groups`: quando a mesma copy normalizada aparece em paginas diferentes dentro da coleta.
- `global_duplicate_groups`: quando a mesma copy aparece em queries, clusters, paginas ou dominios diferentes na rodada inteira.

No relatorio e no Kanban, abra a secao `Escala/duplicados`. Ela mostra paginas, dominios, queries e IDs da biblioteca usados como prova. Isso nao prova lucro sozinho, mas e um sinal forte de distribuicao quando combinado com anuncios ativos, tempo de veiculacao, dor e oferta clara.

## Decisoes do score

- `TESTAR AGORA`: entra na esteira de LP + criativo + MVP minimo.
- `DEEPDIVE`: precisa mais evidencia antes de gastar verba.
- `RADAR`: guardar e observar.
- `DESCARTAR`: nao gastar energia agora.

## Quantas oportunidades por rodada?

Configurado em `agent.config.json`:

- minimo desejado: 5 oportunidades promissoras por rodada;
- maximo no ranking: 12 oportunidades;
- promissoras contam como `TESTAR AGORA`, `DEEPDIVE` ou `RADAR`.

Se a rodada trouxer menos de 5 promissoras, o relatorio marca `NEEDS_MORE_EVIDENCE`. Isso e intencional: melhor admitir que faltou garimpo do que inventar oportunidade fraca.

## Regra brutal

Uma oportunidade so entra na esteira se:

- for entrega digital escalavel;
- tiver comprador claro;
- tiver dor repetida;
- tiver alguma prova de dinheiro, demanda ou distribuicao;
- puder virar LP + criativos + entrega minima em ate 72h;
- puder ser testada com Meta Ads sem prometer milagre.

## Como criar uma nova seed

Copie `data/seeds/first-test-signals.json` para outro arquivo, por exemplo:

```powershell
Copy-Item data/seeds/first-test-signals.json data/seeds/2026-05-14.json
```

Depois edite:

- `opportunity_hypotheses`: suas teses agrupadas.
- `signals`: evidencias reais com links.

Cada sinal precisa ter `cluster_key` igual ao da oportunidade.

## Kanban recomendado

- Raw Signals
- Evidence Queue
- Scored Opportunities
- Red Team Passed
- Experiment Ready
- LP Built
- Ads Live
- Data In
- Killed
- Iterate
- Scale
- Goldmine

## Proximo passo natural

Depois que a V0 provar valor, evoluir para:

- Playwright para coleta assistida de Meta Ads Library/TikTok/AppSumo;
- DuckDB ou SQLite para historico;
- Agno para orquestracao, memoria, tools e rotinas recorrentes;
- integração com Notion/Trello/Linear para Kanban.
