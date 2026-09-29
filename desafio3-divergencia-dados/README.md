# Desafio 3 — Programa de Dados: divergência de números (EDEPE)

Cenário do case: a Diretoria vê 3 números diferentes pra "inscrições do
mês" — Power BI diz **1.200**, a área pedagógica diz **1.050**, o Programa
de Educação Corporativa (AVA) diz **1.180**. Quer saber qual está certo.

Aqui não tem sistema novo pra construir — o exercício é **método de
investigação**. Mas em vez de ficar só no discurso, reconciliamos com dado
real do próprio repo: `core.matricula` (a verdade do AVA, populada nos
Desafios 1/2) contra `staging.stg_powerbi_base` (extração mockada com
defasagem, criada no Desafio 1, nunca usada até agora).

## Passo 1 — Perguntas antes de tocar em qualquer dado

1. "Inscrição" significa a mesma coisa nos 3 lugares? (clicou pra entrar?
   confirmou matrícula? pagou, se for pago?)
2. Os 3 estão olhando o **mesmo período**, com o **mesmo corte de data**?
3. Cancelado/duplicado entra na conta em algum deles?
4. Quando cada número foi tirado? (uma "foto" de ontem já explica parte
   da diferença pra um sistema em tempo real)
5. De onde exatamente veio o número do pedagógico — consulta a sistema,
   ou planilha/contagem manual?

Essas 5 perguntas já eliminam a maior parte dos casos de "número
diferente" sem abrir uma linha de dado.

## Passo 2 — Fontes, em ordem de confiança

1. **Banco do Programa de Educação Corporativa (AVA)** — a tabela de
   matrícula em si, no banco operacional. **Fonte primária**: onde a
   inscrição é gravada no momento que acontece. Neste repo: `core.matricula`.
2. **Extração que alimenta o Power BI** — não é fonte independente, é uma
   **cópia** do AVA tirada por algum processo (query agendada, dataflow,
   export manual). Pergunta chave: de onde puxa, com que frequência
   atualiza, que filtro aplica. Neste repo: `staging.stg_powerbi_base`.
3. **Número do pedagógico** — provavelmente planilha/contagem manual, não
   sistema. Pergunta literal: "abriu o quê, contou como?"

A lógica: o AVA manda. Power BI e pedagógico são derivações — a pergunta
não é "qual dos 3 tá certo", é "quanto cada cópia se afastou da fonte, e
por quê".

## Passo 3 — Definição formal do indicador

| Campo | Valor |
|---|---|
| **Nome** | Total de Inscrições do Mês |
| **Definição** | Matrículas registradas no AVA dentro do mês de referência |
| **Campo de data usado** | `data_matricula` (não `data_inicio`, não `data_conclusao`) |
| **O que conta** | Todo status, **exceto** `cancelado` |
| **Fonte oficial** | `core.matricula` (banco do AVA) — nunca a extração do Power BI |
| **Dono do indicador** | Programa de Dados (pessoa nomeada, não "a área") |
| **Frequência de atualização** | Tempo real (é o banco); extrações derivadas citam de qual corte partiram |

```sql
SELECT count(*)
FROM core.matricula
WHERE data_matricula BETWEEN '2026-08-01' AND '2026-08-31'
  AND status <> 'cancelado';
```

Documentar isso resolve a causa raiz da ambiguidade: sem essa ficha, cada
sistema podia estar usando campo de data diferente ou incluindo/excluindo
cancelado sem ninguém ter decidido isso formalmente.

## Passo 4 — Reconciliação (dado real, não hipotético)

Query em `sql/001_reconciliacao.sql`, rodada contra o banco deste repo:

| Curso | Power BI | AVA (real) | Diferença |
|---|---|---|---|
| C01 — Onboarding Institucional | 49 | 58 | -9 |
| C02 — LGPD Aplicada | 36 | 45 | -9 |
| C03 — Atendimento ao Público | 38 | 45 | -7 |
| C04 — Processo Judicial Eletrônico | 53 | 56 | -3 |
| C05 — Ética e Conduta | 28 | 39 | -11 |
| C06 — Acessibilidade Digital | 40 | 42 | -2 |
| C07 — Segurança da Informação | 47 | 51 | -4 |

**Achado:** em **todos os 7 cursos** o Power BI mostra menos que o AVA,
nunca mais. Não é ruído aleatório — é padrão sistemático. Isso descarta
duplicata/erro pontual e aponta pra causa estrutural: **a extração do
Power BI está desatualizada**, pegou uma foto antes das matrículas mais
recentes entrarem.

**Próximo passo real** (não simulável neste mock — os dados são
sintéticos, a defasagem foi gerada aleatória de propósito): abrir a
configuração/query do pipeline do Power BI e comparar contra a ficha do
passo 3 — mesmo campo de data? mesmo filtro de status? qual o agendamento
de atualização?

## Passo 5 — Como evitar que se repita

1. **Fonte única de verdade (SSOT)** — todo relatório consome do AVA (ou
   de uma camada validada em cima dele). Nada de contagem manual paralela
   — foi exatamente essa 3ª fonte solta que gerou o 1.050 sem explicação.
2. **Ficha do indicador publicada e visível** — não fica na cabeça de
   quem construiu o painel.
3. **Reconciliação automática, não investigação manual** — a query do
   passo 4 devia rodar sozinha (diária) e **alertar** se a diferença
   passar de um limite (ex: >5%). Mesma lógica de "rotina de alerta" já
   citada nos Desafios 1/2 (Celery beat), aplicada aqui a qualidade de
   indicador em vez de prazo de curso.
4. **Todo painel mostra "atualizado em"** visível na tela.
5. **Mudança de definição é versionada e comunicada**, nunca um ajuste
   silencioso que quebra comparação histórica.
6. **Dono nomeado do indicador**, não "a área" genérica.

## Como reproduzir a reconciliação

Requer o banco do Desafio 1 já rodando e populado.

```bash
cd desafio1-dados-integracao
docker cp data/raw/powerbi_base.csv edepe_postgres:/tmp/powerbi_base.csv
docker exec -i edepe_postgres psql -U edepe -d edepe_dados -c "TRUNCATE staging.stg_powerbi_base;"
docker exec -i edepe_postgres psql -U edepe -d edepe_dados -c "\copy staging.stg_powerbi_base(mes_referencia,curso_id,curso_nome,total_inscritos_powerbi,total_concluidos_powerbi,extraido_em) FROM '/tmp/powerbi_base.csv' WITH (FORMAT csv, HEADER true)"

cd ../desafio3-divergencia-dados
docker exec -i edepe_postgres psql -U edepe -d edepe_dados < sql/001_reconciliacao.sql
```

## Status

- [x] Passo 1–5 documentados (perguntas, fontes, indicador, reconciliação, prevenção)
- [x] Reconciliação rodada com dado real do repo (não só hipotético)
- [x] Achado: padrão sistemático de subcontagem no Power BI (não erro aleatório)
- [ ] Rotina automática de alerta de divergência (citada no passo 5, não implementada)
- [ ] Ficha de indicador formal publicada em ferramenta real (aqui é só este README)

## Simplificações conscientes (para citar na entrevista, não esconder)

- **Dado sintético**: a defasagem do `powerbi_base.csv` foi gerada
  aleatória (`random.randint(-8,3)` por curso) na criação do mock — o
  drill-down por data de extração não fecha exato porque não existe uma
  causa mecânica real por trás, só um número sorteado. O método de
  reconciliação (comparar por dimensão, confirmar padrão sistemático) é o
  que importa e é igual ao de uma investigação real.
- **Contaminação de dado entre desafios evitada por coincidência de
  data**: alunos de teste do Desafio 2 têm `data_matricula` fora de
  agosto/2026, então não entraram nessa reconciliação. Em um ambiente
  real isso seria um argumento a favor de **nunca misturar dado de teste
  com produção** — ponto que vale citar na entrevista.
