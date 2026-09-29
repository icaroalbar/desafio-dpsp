# Desafio 2 — Evolução do Programa de Educação Corporativa (EDEPE)

Protótipo da demanda do pedagógico: *"trilha de onboarding para novos
servidores, 3 cursos obrigatórios, prazo de 60 dias, avaliação mínima de
70% e emissão automática de certificado"*.

Reaproveita o banco do Desafio 1 (`core.alunos`, `core.curso`,
`core.matricula`, mesmo Postgres/Mailpit já rodando) — mostra que o
cadastro de aluno e o motor de matrícula são a mesma base, só a regra de
negócio em cima muda.

## Requisito levantado (a partir da frase solta do pedagógico)

- **Matrícula automática**: ao cadastrar um novo servidor, ele já entra
  matriculado nos 3 cursos obrigatórios da trilha — sem ação manual.
- **Prazo**: 60 dias corridos a partir do cadastro, pra concluir os 3.
- **Aprovação**: nota mínima 7,0 **em cada curso**, independente (não é
  média geral — cada curso vale por si).
- **Recuperação**: nota abaixo de 7 não reprova na hora — abre janela de
  3 dias corridos (a partir da conclusão) pra refazer a avaliação. Passou
  os 3 dias sem refazer, ou refez e continuou abaixo de 7 → reprovado.
- **Prazo estourado**: curso não concluído dentro dos 60 dias → reprovado
  automático (`motivo=prazo_expirado`) e o aluno entra na fila de espera
  desse curso pra próxima turma.

Perguntas fechadas com o "pedagógico" durante o levantamento (documentado
aqui porque numa entrevista real isso é o que se apresenta como evidência
de que o requisito foi de fato levantado, não assumido):

| Pergunta em aberto | Resposta |
|---|---|
| Nota é por curso ou média da trilha? | Por curso, cada um precisa 7 sozinho |
| Pode refazer avaliação? | Sim, 3 dias de recuperação |
| O que acontece se estourar o prazo? | Reprova + fila de espera da próxima turma |

## Trilha (parametrização assumida)

3 cursos fixos, reaproveitados do `core.curso` do Desafio 1:

| Curso | Nome |
|---|---|
| C01 | Onboarding Institucional EDEPE |
| C02 | LGPD Aplicada ao Serviço Público |
| C05 | Ética e Conduta no Serviço Público |

## Arquitetura

```
POST /alunos
  │  cadastra em core.alunos (nome completo + e-mail obrigatórios,
  │  mesma regra de qualidade do Desafio 1)
  ▼
  matricula automático nos 3 cursos (core.matricula, status=em_andamento)

GET /alunos/{id}/trilha
  │  lê core.matricula dos 3 cursos do aluno
  ▼
  calcula na hora (nada fica salvo como "status" fixo):
    situação de cada curso (cursando / aprovado / em_recuperacao / reprovado)
    status_global da trilha
    média das notas já fechadas
  │
  ▼  efeito colateral: reprovado por prazo → INSERT em core.fila_espera

GET /alunos/{id}/certificado
  │  reaproveita a mesma avaliação de /trilha
  ▼  status_global != concluido? → 409 + lista de pendências
  ▼  concluido → INSERT em core.certificado (idempotente, mesmo protocolo
     em consultas repetidas) → gera PDF (reportlab) com nome, CPF, cursos,
     carga horária total e protocolo de verificação
```

**Por que calcular na hora em vez de guardar status pronto:** evita
precisar de uma rotina rodando toda hora só pra "virar" o status de
`em_andamento` pra `reprovado` quando o prazo vence — o cálculo usa a
data de hoje no momento da consulta, então está sempre certo sem job
nenhum. Trade-off: se ninguém consultar, a linha na fila de espera
também não é criada até a primeira consulta depois do prazo vencido — pra
produção real, isso seria uma rotina agendada (Celery beat, por exemplo,
citada como diferencial no perfil da vaga) em vez de efeito colateral de
GET.

## Estrutura de pastas

```
desafio2-trilha-onboarding/
├── sql/
│   ├── 001_alter_matricula_trilha.sql   # +nota_recuperacao, +data_conclusao_recuperacao, +fila_espera
│   └── 002_certificado.sql              # tabela core.certificado (emissão idempotente)
├── api/
│   ├── main.py                          # FastAPI: POST /alunos, GET /trilha, GET /certificado
│   └── certificado.py                   # gera o PDF do certificado (reportlab)
└── README.md
```

## Como rodar local

Pré-requisito: Postgres do Desafio 1 já rodando (`docker compose up -d` na
pasta `desafio1-dados-integracao/`) — reaproveita o mesmo `.env` de lá.

```bash
cd desafio2-trilha-onboarding

# 1. aplica as migrações (colunas novas + fila_espera + certificado) em cima do banco do Desafio 1
docker exec -i edepe_postgres psql -v ON_ERROR_STOP=1 -U edepe -d edepe_dados < sql/001_alter_matricula_trilha.sql
docker exec -i edepe_postgres psql -v ON_ERROR_STOP=1 -U edepe -d edepe_dados < sql/002_certificado.sql

# 2. dependência extra (geração de PDF)
pip install reportlab

# 3. sobe a API numa porta diferente da do Desafio 1 (8000)
python3 -m uvicorn api.main:app --reload --port 8001
# Swagger em http://localhost:8001/docs
```

**Cadastrar aluno (matricula automático):**

```bash
curl -X POST http://localhost:8001/alunos \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "111.222.333-44",
    "nome": "Fulano da Silva Souza",
    "email": "fulano.silva@edepe.sp.gov.br"
  }'
```

**Consultar a trilha:**

```bash
curl http://localhost:8001/alunos/{id_aluno}/trilha
```

Resposta traz `status_global`, `media_notas_atual` e o detalhe dos 3
cursos (`situacao`, `nota`, `nota_recuperacao`, `data_segunda_prova`,
`motivo` quando reprovado, `orientacao` quando é caso de prazo estourado).

**Emitir certificado** (só funciona se `status_global=concluido`):

```bash
curl http://localhost:8001/alunos/{id_aluno}/certificado -o certificado.pdf
```

Se a trilha não estiver concluída, devolve `409` com a lista de cursos
pendentes/reprovados em vez do PDF. Emissão é idempotente — pedir de novo
devolve o mesmo protocolo (`core.certificado`, `UNIQUE (id_aluno, trilha)`),
não gera um segundo registro.

**Simular cenários** (útil pra demo — sem esperar 60 dias de verdade):

```bash
# aprova direto
docker exec -i edepe_postgres psql -U edepe -d edepe_dados -c "
UPDATE core.matricula SET nota_final=8.5, data_conclusao=current_date
WHERE id_aluno={id} AND id_curso='C01';"

# reprova por prazo (empurra o início pro passado)
docker exec -i edepe_postgres psql -U edepe -d edepe_dados -c "
UPDATE core.matricula SET data_matricula=current_date-70, data_inicio=current_date-70
WHERE id_aluno={id};"
```

## Plano de teste

Casos derivados direto das regras de negócio confirmadas no levantamento.
Executados manualmente durante a construção (ver histórico) — os T06 a T15
foram de fato rodados contra a API, não são só hipóteses no papel.

| # | Cenário | Pré-condição / entrada | Resultado esperado |
|---|---|---|---|
| T01 | Cadastro válido | `POST /alunos` com CPF novo, nome completo, e-mail | 201 · aluno criado · matriculado automático em C01/C02/C05, status `em_andamento` |
| T02 | Nome incompleto | `nome="Ana"` | 400 · rejeita, não cadastra |
| T03 | E-mail vazio | `email=""` | 400 · rejeita, não cadastra |
| T04 | CPF duplicado | CPF já cadastrado | 409 · conflito |
| T05 | Consulta logo após cadastro | `GET /alunos/{id}/trilha` | `status_global=em_andamento` · 3 cursos `cursando` · `media_notas_atual=null` |
| T06 | Aprovação direta | `nota_final=8.5`, `data_conclusao` preenchida | `situacao=aprovado` |
| T07 | Reprovação dentro da janela de recuperação | `nota_final=5.2`, concluído há 1 dia | `situacao=em_recuperacao`, `data_limite_recuperacao` = conclusão + 3 dias |
| T08 | Recuperação aprova | `nota_recuperacao=7.5` dentro do prazo | `situacao=aprovado`, nota usada na média é a da recuperação (não a original) |
| T09 | Recuperação também reprova | `nota_recuperacao=6.0` | `situacao=reprovado`, `motivo=nota_abaixo_da_media` |
| T10 | Perdeu o prazo de recuperação sem refazer | concluído há >3 dias, sem `nota_recuperacao` | `situacao=reprovado`, `motivo=nota_abaixo_da_media` |
| T11 | Estourou o prazo geral (60 dias) sem concluir | `data_inicio` há 70 dias, sem `data_conclusao` | `situacao=reprovado`, `motivo=prazo_expirado`, `orientacao` preenchida |
| T12 | Efeito colateral da fila de espera | logo após T11 | linha criada em `core.fila_espera` (`status=aguardando`) |
| T13 | Idempotência da fila de espera | consulta T11 de novo | **não** duplica linha (constraint `UNIQUE (id_aluno, id_curso, status)`) |
| T14 | Status global com 1 reprovado | 1 aprovado + 1 reprovado + 1 cursando | `status_global=reprovado` (qualquer reprovado reprova a trilha toda) |
| T15 | Status global concluído | os 3 aprovados | `status_global=concluido` |
| T16 | Média ignora curso ainda cursando | 2 fechados + 1 em andamento | `media_notas_atual` usa só os 2 fechados |

Regressão: qualquer mudança na função `_avaliar_curso` (motor de cálculo em
`api/main.py`) precisa rodar essa tabela inteira de novo antes de subir —
é pouca lógica mas concentrada, fácil de quebrar um caso ajustando outro.

## Homologação, implantação e acompanhamento

**Homologação**
- Ambiente espelho de produção (mesmo schema, dado de teste).
- Roteiro acima executado com participação do pedagógico — eles validam
  não só "funciona" mas se o **texto** de cada `motivo`/`orientacao` faz
  sentido pra quem vai ler (ex: a mensagem de fila de espera está clara?).
- Critério de aceite: T01–T16 passando + pedagógico confirmar por escrito
  que prazo/nota de corte/recuperação batem com o que foi pedido.

**Implantação**
- Janela fora de pico de matrícula (evita concorrência com cadastro em lote).
- Regra vale só pra **novos** cadastros a partir da data de corte — aplicar
  retroativamente a servidores já ativos é decisão de negócio separada,
  não automática.
- Mantém o fluxo de matrícula manual anterior disponível durante a
  transição, como rollback se a automação apresentar problema.
- Comunicado ao RH/pedagógico sobre a mudança de comportamento no cadastro.

**Acompanhamento pós-implantação**
- Dashboard Power BI: % concluído no prazo, taxa de reprovação por curso,
  quantos estão em recuperação, tamanho da fila de espera por curso.
- Alerta automático pro gestor quando um subordinado está a poucos dias do
  prazo sem concluir (rotina agendada — Celery beat, citado como
  diferencial no perfil da vaga; não implementado nesta demo).
- Revisão periódica de nota de corte/prazo com base no dado real: taxa de
  reprovação muito alta ou muito baixa indica critério descalibrado.

## Status

- [x] Levantamento de requisito (RF + perguntas fechadas com o pedagógico)
- [x] Parametrização assumida (3 cursos fixos da trilha)
- [x] `POST /alunos` com matrícula automática
- [x] `GET /alunos/{id}/trilha` com situação calculada (cursando/aprovado/em_recuperacao/reprovado)
- [x] Regra de recuperação (3 dias) e reprovação por prazo (fila de espera)
- [x] Testado manualmente os 5 cenários (aprovado, recuperação ok, reprovado por nota, reprovado por prazo)
- [x] Plano de teste formal (16 casos, T01–T16)
- [x] Roteiro de homologação, implantação e acompanhamento (texto)
- [x] `GET /alunos/{id}/certificado` — PDF, bloqueia se não concluído, emissão idempotente
- [ ] Integração com sistema de RH (evento de admissão disparando o cadastro)
- [ ] Testes automatizados (pytest) — plano existe, ainda não virou código

## Simplificações conscientes (para citar na entrevista, não esconder)

- **Situação calculada em tempo real, não persistida** — trade-off
  explicado acima (efeito colateral de GET em vez de rotina agendada).
- **Trilha com cursos fixos no código** (`TRILHA_CURSOS`), não parametrizável
  via banco/admin ainda — numa versão real isso seria uma tabela
  `trilha`/`trilha_curso` configurável, não uma constante Python.
- **Certificado emitido sob consulta, não por evento automático** — o PDF
  só é gerado quando alguém chama `GET /certificado`; uma versão real
  emitiria (e enviaria por e-mail) automaticamente no instante em que o
  3º curso é aprovado, sem esperar alguém pedir.
