-- Staging da planilha única de matrícula em lote (1 linha = aluno + curso desejado)
CREATE TABLE IF NOT EXISTS staging.stg_lote_matriculas (
    id                      BIGSERIAL,
    cpf                     TEXT,
    nome                    TEXT,
    email                   TEXT,
    data_nascimento         TEXT,
    orgao_lotacao           TEXT,
    cargo                   TEXT,
    data_admissao           TEXT,
    curso_id                TEXT,
    curso_nome              TEXT,
    data_inicio_desejada    TEXT,
    arquivo_origem          TEXT,
    carregado_em            TIMESTAMP NOT NULL DEFAULT now()
);
