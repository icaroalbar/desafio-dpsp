# Desafio 1 — Dados e integração

Case técnico EDEPE. Demonstração prática (não é o sistema real, dados 100% mockados)
da abordagem pra investigar/tratar inconsistências e estruturar integração.

## Abordagem técnica

`participantes.csv` e `api_matriculas.json` são o que a EDEPE de fato recebe (export de
cadastro + retorno de API) — raramente se tem acesso direto ao banco de outro sistema,
então isso é realista como ponto de entrada. Mas a partir daí o pipeline carrega tudo num
banco (SQLite pra demo; seria SQL Server/Postgres na EDEPE) e faz profiling, dedupe e
reconciliação via **SQL** (não só pandas) — bate com o requisito forte de "SQL e
modelagem de dados" da vaga.

```
participantes.csv ─┐
                    ├─► load ─► SQLite (staging) ─► SQL: profiling/dedupe/join/reconciliação ─► modelo dimensional
api_matriculas.json ┘
```

## Status

- [x] Passo 1 — dados mock (CSV/JSON, ponto de entrada)
- [ ] Passo 2 — carga em SQLite (staging) + diagnóstico/profiling via SQL
- [ ] Passo 3 — tratamento via SQL (dedupe, completude, normalização)
- [ ] Passo 4 — validação de qualidade (schema, Pandera nas bordas + constraints no banco)
- [ ] Passo 5 — integração (join + fonte externa) via SQL
- [ ] Passo 6 — modelagem dimensional (star schema no SQLite)
- [ ] Passo 7 — rastreabilidade/auditoria
- [ ] Passo 8 — testes

## Passo 1 — Dados mock

Gerados por `scripts/generate_mock_data.py` (seed fixa = reprodutível).

- `data/raw/participantes.csv` — 150 pessoas únicas + duplicatas injetadas (170 linhas):
  - 8 duplicatas **exatas** (linha reimportada igual — erro clássico de carga em lote).
  - 12 duplicatas **variantes**: mesmo CPF, id novo, nome/e-mail com case, acento ou
    espaçamento diferente (simula recadastro manual da mesma pessoa).
  - ~20 alvos de incompletude: e-mail, data de nascimento, órgão de lotação ou nome vazios/truncados.
- `data/raw/api_matriculas.json` — 329 registros de matrícula/conclusão:
  - status com grafia inconsistente (`Concluído` / `concluido` / `CONCLUIDO`) — precisa normalizar antes de comparar.
  - ~10% dos concluídos sem `nota_final` lançada (falha de integração real).
  - ~5% dos concluídos com `data_conclusao` anterior à `data_inicio` (dado sujo de propósito).
  - 25 registros **órfãos**: CPF que não existe em `participantes.csv` — simula a necessidade
    de integrar com outro sistema institucional (ex: RH) que já matriculou gente não cadastrada localmente.
- `data/raw/powerbi_base.csv` — snapshot mensal por curso extraído em outro momento/critério,
  com contagem de inscritos/concluídos que **não bate** com o que dá pra apurar na API — reproduz
  a divergência AVA vs Power BI citada no case (e prepara terreno pro raciocínio do Desafio 3).

Reprodutibilidade:

```bash
python3 scripts/generate_mock_data.py
```
