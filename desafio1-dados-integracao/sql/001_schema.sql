-- ============================================================
-- Desafio 1 — EDEPE — Modelagem do banco (staging + core)
-- Postgres. Arquivo só de definição (DDL) — não é rodado ainda.
-- ============================================================

-- ------------------------------------------------------------
-- STAGING: zona de pouso do dado bruto. Espelha o arquivo (CSV/
-- JSON) exatamente como chega. Tudo TEXT, sem constraint —
-- se colocar regra aqui, a carga trava antes de você conseguir
-- nem diagnosticar o problema.
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE staging.stg_participantes (
    id_participante   TEXT,
    cpf               TEXT,
    nome              TEXT,
    email             TEXT,
    data_nascimento   TEXT,
    orgao_lotacao     TEXT,
    cargo             TEXT,
    data_admissao     TEXT,
    arquivo_origem    TEXT,
    carregado_em      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE staging.stg_matriculas (
    id_matricula      TEXT,
    cpf               TEXT,
    curso_id          TEXT,
    curso_nome        TEXT,
    carga_horaria     TEXT,
    status            TEXT,
    nota_final        TEXT,
    data_matricula    TEXT,
    data_inicio       TEXT,
    data_conclusao    TEXT,
    arquivo_origem    TEXT,
    carregado_em      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE staging.stg_powerbi_base (
    mes_referencia            TEXT,
    curso_id                  TEXT,
    curso_nome                TEXT,
    total_inscritos_powerbi   TEXT,
    total_concluidos_powerbi  TEXT,
    extraido_em               TEXT,
    arquivo_origem            TEXT,
    carregado_em              TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- CORE: destino limpo. Constraint trava o dado ruim de entrar
-- de novo (parte "preventiva" da resposta do case).
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS core;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

CREATE TABLE core.curso (
    id_curso        VARCHAR(10) PRIMARY KEY,
    nome            TEXT NOT NULL,
    carga_horaria   INTEGER NOT NULL CHECK (carga_horaria > 0)
);

CREATE TABLE core.alunos (
    id_aluno          SERIAL PRIMARY KEY,
    cpf               VARCHAR(14) NOT NULL UNIQUE
                        CHECK (cpf ~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$'),
    nome              TEXT NOT NULL,
    email             TEXT NOT NULL,
    data_nascimento   DATE,
    orgao_lotacao     TEXT,
    cargo             TEXT,
    data_admissao     DATE,
    criado_em         TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE core.matricula (
    id_matricula      SERIAL PRIMARY KEY,
    id_aluno          INTEGER NOT NULL REFERENCES core.alunos(id_aluno),
    id_curso          VARCHAR(10) NOT NULL REFERENCES core.curso(id_curso),
    status            VARCHAR(20) NOT NULL
                        CHECK (status IN ('em_andamento','concluido','cancelado','nao_iniciado')),
    nota_final        NUMERIC(5,2)
                        CHECK (nota_final IS NULL OR nota_final BETWEEN 0 AND 100),
    data_matricula    DATE NOT NULL,
    data_inicio       DATE NOT NULL,
    data_conclusao    DATE
                        CHECK (data_conclusao IS NULL OR data_conclusao >= data_inicio),
    criado_em         TIMESTAMP NOT NULL DEFAULT now()
);

-- só pode ter 1 matrícula "em_andamento" por (aluno, curso) ao mesmo tempo.
-- depois de concluída/cancelada, libera nova matrícula no mesmo curso.
CREATE UNIQUE INDEX uq_matricula_ativa
    ON core.matricula (id_aluno, id_curso)
    WHERE status = 'em_andamento';

-- ------------------------------------------------------------
-- Filas de exceção: nada é descartado silenciosamente.
-- ------------------------------------------------------------

-- CPF já cadastrado, mas algum campo da planilha nova diverge do
-- cadastro. Decisão do negócio: NÃO atualiza sozinho, fica pendente.
CREATE TABLE core.pendencia_cadastro (
    id                  SERIAL PRIMARY KEY,
    cpf                 VARCHAR(14) NOT NULL,
    campo_divergente    TEXT NOT NULL,
    valor_atual         TEXT,
    valor_novo          TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'pendente'
                          CHECK (status IN ('pendente','resolvido')),
    criado_em           TIMESTAMP NOT NULL DEFAULT now()
);

-- Linha rejeitada por dado obrigatório faltando ou curso inexistente.
-- Guarda a linha bruta inteira (JSONB) pra dar pra investigar depois.
CREATE TABLE core.linha_rejeitada (
    id              SERIAL PRIMARY KEY,
    origem          TEXT NOT NULL,   -- 'stg_participantes' | 'stg_matriculas'
    identificador   TEXT,            -- cpf ou id bruto, o que tiver
    motivo          TEXT NOT NULL,   -- 'cpf_ausente' | 'curso_inexistente' | ...
    linha_bruta     JSONB,
    criado_em       TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- Controle do lote assíncrono (API recebe -> enfileira -> worker
-- processa -> manda e-mail). 1 linha por upload de planilha.
-- ------------------------------------------------------------
CREATE TABLE core.lote_processamento (
    protocolo           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_destino        TEXT NOT NULL,
    arquivo_origem        TEXT NOT NULL,
    status                VARCHAR(20) NOT NULL DEFAULT 'recebido'
                            CHECK (status IN ('recebido','processando','concluido','erro')),
    total_recebido        INTEGER,
    total_matriculado     INTEGER,
    total_rejeitado       INTEGER,
    mensagem_erro         TEXT,
    criado_em             TIMESTAMP NOT NULL DEFAULT now(),
    concluido_em          TIMESTAMP
);
