# Desafio 1 — Dados e integração (EDEPE)

Protótipo funcional construído para o case técnico do processo seletivo EDEPE
(Assessor/a Técnico/a de Tecnologia Educacional e Plataformas Digitais).
Demonstra, com dados 100% mockados, a abordagem para tratar inconsistências
de dados acadêmicos e estruturar uma integração entre sistemas.

Uma API só: **matrícula em lote**. Recebe uma planilha (como um formulário —
1 linha = 1 pessoa + o curso que ela quer fazer), valida contra o banco já
existente, cadastra o que está certo, e devolve por e-mail um relatório do
que não pôde ser processado e por quê.

## Cenário reproduzido

**`planilha_lote_matriculas.csv`** — 1 linha = aluno + curso desejado, com
casos reais de sobreposição contra o banco já populado:

- gente nova (cadastra aluno + matrícula);
- aluno já cadastrado pedindo curso novo;
- aluno com dado divergente na planilha (testa pendência de cadastro);
- aluno pedindo curso que já cursa (testa "já matriculado");
- curso inexistente;
- e-mail ausente;
- nome incompleto (1 palavra só);
- duplicata no mesmo lote (mesma pessoa enviada 2x).

O gerador (`scripts/generate_lote_mock.py`) lê o estado atual do banco pra
criar essa sobreposição de propósito — por isso ele só produz casos
realistas de "aluno já existe" depois que já existe alguém no banco (ver
"Como rodar local" abaixo).

## Arquitetura

```
planilha_lote_matriculas.csv
        │
        ▼
staging.stg_lote_matriculas (Postgres, sem constraint, aceita qualquer lixo)
        │
        ▼  SQL comparativo (sql/005_comparativo_lote.sql)
        │
        ▼
core.alunos / core.matricula / core.pendencia_cadastro / core.linha_rejeitada
        │
        ▼
.xlsx (motivo + célula destacada) ──► e-mail via SMTP (Mailpit / SES)
```

- **staging**: zona de pouso do dado bruto, tudo `TEXT`, sem regra.
- **core**: destino limpo, com `UNIQUE`/`CHECK`/`FK` travando o problema de
  voltar a acontecer (parte "preventiva" da resposta do case).
- **API** (`api/main.py`, FastAPI, síncrona por enquanto): `POST
  /lotes/matriculas` — **não reseta nada**, cada chamada é um lote novo
  empilhado sobre o que já existe no banco.
- **Mailpit**: servidor SMTP fake local + UI web, pra testar envio de
  e-mail sem depender de credencial real da AWS SES (token expirado neste
  ambiente — troca de host/porta/credencial via `.env` quando houver acesso).

Regras de negócio (`sql/005_comparativo_lote.sql`):

1. Dedupe da própria planilha por (CPF, curso) — 2ª submissão da mesma
   pessoa/curso no mesmo lote é descartada, mantendo a linha mais completa.
2. Curso que não existe → rejeita a linha, não segue adiante.
3. E-mail ausente e aluno ainda não cadastrado → rejeita (não dá pra criar
   cadastro sem contato).
4. **Nome incompleto** (1 palavra só, ex: sobrenome cortado) e aluno ainda
   não cadastrado → rejeita. `NOT NULL` não é o mesmo que "nome completo" —
   bug real que aconteceu aqui: um nome truncado passava direto e virava
   aluno válido, só apareceu quando um relatório mostrou "fulano" com
   matrícula ativa e nome de uma palavra só.
5. Aluno já cadastrado com nome/e-mail divergente → vai pra
   `pendencia_cadastro`, **não atualiza sozinho** e não processa a
   matrícula dessa linha até alguém resolver.
6. Aluno novo (CPF não existe, e-mail e nome completo ok) → cadastra.
7. Aluno já tem matrícula **ativa** nesse curso → avisa "já matriculado",
   ignora (não duplica). Índice único parcial garante isso mesmo se a
   checagem em SQL falhar.

## Estrutura de pastas

```
desafio1-dados-integracao/
├── docker-compose.yml            # Postgres 16 + Mailpit
├── .env.example                  # copiar para .env
├── sql/
│   ├── 001_schema.sql            # DDL: schemas staging + core
│   ├── 002_seed_curso.sql        # 7 cursos de exemplo
│   ├── 004_add_staging_lote.sql  # staging da planilha única (formulário)
│   └── 005_comparativo_lote.sql  # dedupe/validação/match/pendência
├── scripts/
│   └── generate_lote_mock.py     # gera a planilha (lê o banco pra criar
│                                    sobreposição realista)
├── api/
│   ├── main.py                   # FastAPI: POST /lotes/matriculas
│   ├── report.py                 # gera o .xlsx (motivo + célula destacada)
│   └── email_sender.py           # envia o .xlsx por SMTP (Mailpit/SES)
└── data/raw/                     # planilha gerada (script versionado, dado gerado não)
```

## Como rodar local

Pré-requisitos: Docker Desktop (com integração WSL ligada, se for o caso),
Python 3.8+.

```bash
cd desafio1-dados-integracao

# 1. credenciais locais (nunca commitar o .env de verdade)
cp .env.example .env

# 2. sobe Postgres + Mailpit
docker compose up -d

# 3. aplica o schema, popula os cursos, cria a staging da planilha
docker exec -i edepe_postgres psql -v ON_ERROR_STOP=1 -U edepe -d edepe_dados < sql/001_schema.sql
docker exec -i edepe_postgres psql -v ON_ERROR_STOP=1 -U edepe -d edepe_dados < sql/002_seed_curso.sql
docker exec -i edepe_postgres psql -v ON_ERROR_STOP=1 -U edepe -d edepe_dados < sql/004_add_staging_lote.sql

# 4. dependências Python
pip install psycopg2-binary fastapi uvicorn python-multipart openpyxl

# 5. sobe a API
python3 -m uvicorn api.main:app --reload --port 8000
# Swagger em http://localhost:8000/docs
```

> **Nota:** sempre rodar `psql` com `-v ON_ERROR_STOP=1`. Sem essa flag,
> `psql` **engole erro no meio do script e sai com código 0** — um bug real
> que aconteceu aqui: um script quebrou no meio, `psql` "deu certo" mesmo
> assim, e só apareceu ao conferir os dados no banco.

**Banco começa vazio de aluno** (só os 7 cursos seedados) — então o gerador
não tem "aluno existente" pra criar sobreposição na primeira vez. Rode o
fluxo 2x:

```bash
# 1ª chamada: banco vazio, todo mundo "novo" (sem pendência/já-matriculado ainda)
python3 scripts/generate_lote_mock.py
curl -X POST http://localhost:8000/lotes/matriculas \
  -F "planilha=@data/raw/planilha_lote_matriculas.csv;type=text/csv" \
  -F "email_destino=pedagogico@edepe.sp.gov.br"

# 2ª chamada: agora tem aluno no banco -> gera os casos de sobreposição de verdade
python3 scripts/generate_lote_mock.py
curl -X POST http://localhost:8000/lotes/matriculas \
  -F "planilha=@data/raw/planilha_lote_matriculas.csv;type=text/csv" \
  -F "email_destino=pedagogico@edepe.sp.gov.br"
```

Resposta esperada (2ª chamada): soma de alunos/matrículas + detalhamento de
eventos do lote (já matriculado, pendência, rejeitado, nome incompleto) +
confirmação de envio do e-mail. Se houve qualquer linha não processada,
chega em `email_destino` um `.xlsx` anexado com a lista, ordenada por nome,
coluna "motivo" e a célula do campo problemático destacada em vermelho
(erro) ou amarelo (aviso, ex: "já matriculado"). Ver em `http://localhost:8025`.

**Conferir dados direto no banco:**

```bash
docker exec -i edepe_postgres psql -U edepe -d edepe_dados -c "
SELECT 'alunos', count(*) FROM core.alunos
UNION ALL SELECT 'matricula', count(*) FROM core.matricula
UNION ALL SELECT 'pendencia_cadastro', count(*) FROM core.pendencia_cadastro
UNION ALL SELECT 'linha_rejeitada', count(*) FROM core.linha_rejeitada;"
```

**Mailpit** (UI web pra ver e-mails enviados em dev): `http://localhost:8025`
— já plugado no `/lotes/matriculas`, mostra o `.xlsx` que a API manda.

## Status

- [x] Mock com sujeira controlada e sobreposição real contra o banco
- [x] Schema Postgres (staging + core) com constraints preventivas
- [x] SQL comparativo (dedupe, validação, match, pendência, rastreabilidade)
- [x] API síncrona testada ponta a ponta
- [x] Mailpit no ar, envio SMTP confirmado
- [x] Gerar `.xlsx` de saída (rejeitados + pendências + motivo + célula destacada)
- [x] Anexar `.xlsx` e enviar por e-mail via Mailpit (trocar por SES depois)
- [ ] Processamento assíncrono (Celery + Redis) — hoje a API é síncrona
- [ ] Reconciliação com `powerbi_base.csv` (Desafio 3)
- [ ] Testes automatizados (pytest)

## Simplificações conscientes (para citar na entrevista, não esconder)

- **Sem Celery ainda**: a API responde de forma síncrona. O desenho alvo é
  assíncrono (202 Accepted + processamento em worker + e-mail no fim).
- **Mailpit no lugar de SES**: não há credencial AWS válida disponível neste
  ambiente (token expirado). A troca é só variável de ambiente.
- **Banco nasce vazio de aluno**: não existe carga inicial/histórica nesta
  versão (endpoint de carga histórica foi removido por decisão de escopo —
  o foco da demo é a operação contínua, não a investigação retroativa).
  Por isso a sobreposição realista só aparece a partir da 2ª chamada.
