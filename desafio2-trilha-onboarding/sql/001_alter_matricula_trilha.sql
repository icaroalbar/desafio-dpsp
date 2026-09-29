-- Desafio 2 — trilha de onboarding. Reaproveita core.alunos/core.curso/
-- core.matricula (já criados pelo Desafio 1, mesmo Postgres).

ALTER TABLE core.matricula
    ADD COLUMN IF NOT EXISTS nota_recuperacao NUMERIC(5,2)
        CHECK (nota_recuperacao IS NULL OR nota_recuperacao BETWEEN 0 AND 10),
    ADD COLUMN IF NOT EXISTS data_conclusao_recuperacao DATE;

-- fila de espera: aluno que estourou o prazo de 60 dias sem concluir um
-- curso da trilha entra aqui, pra próxima turma
CREATE TABLE IF NOT EXISTS core.fila_espera (
    id           SERIAL PRIMARY KEY,
    id_aluno     INTEGER NOT NULL REFERENCES core.alunos(id_aluno),
    id_curso     VARCHAR(10) NOT NULL REFERENCES core.curso(id_curso),
    motivo       TEXT NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'aguardando'
                   CHECK (status IN ('aguardando', 'atendido')),
    criado_em    TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (id_aluno, id_curso, status)
);
