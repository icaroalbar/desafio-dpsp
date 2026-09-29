-- Registro de emissão de certificado. Idempotente por aluno+trilha: emite
-- uma vez, consultas seguintes reaproveitam o mesmo protocolo/data.
CREATE TABLE IF NOT EXISTS core.certificado (
    id              SERIAL PRIMARY KEY,
    id_aluno        INTEGER NOT NULL REFERENCES core.alunos(id_aluno),
    trilha          TEXT NOT NULL,
    protocolo       UUID NOT NULL DEFAULT gen_random_uuid(),
    carga_horaria   INTEGER NOT NULL,
    data_conclusao  DATE NOT NULL,
    emitido_em      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (id_aluno, trilha)
);
