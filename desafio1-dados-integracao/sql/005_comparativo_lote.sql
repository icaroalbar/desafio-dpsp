-- ============================================================
-- Comparativo da planilha única de matrícula em lote (formulário:
-- aluno + curso desejado numa linha só). NÃO reseta core — cada
-- chamada é um lote novo empilhado sobre o que já existe.
-- ============================================================

-- 1) dedupe da própria planilha por CPF (2ª submissão da mesma pessoa
--    no mesmo lote) — escolhe a linha mais completa, mesma regra de sempre.
CREATE TEMP TABLE tmp_lote_canonico AS
WITH scored AS (
    SELECT *,
        (CASE WHEN nullif(trim(email), '') IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN nullif(trim(data_nascimento), '') IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN nullif(trim(orgao_lotacao), '') IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN nullif(trim(cargo), '') IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN nullif(trim(data_admissao), '') IS NOT NULL THEN 1 ELSE 0 END
        ) AS completude
    FROM staging.stg_lote_matriculas
),
ranqueado AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY trim(cpf), curso_id ORDER BY completude DESC, id ASC
    ) AS rn
    FROM scored
)
SELECT * FROM ranqueado;

INSERT INTO core.linha_rejeitada (origem, identificador, motivo, linha_bruta)
SELECT 'stg_lote_matriculas', r.cpf,
       'duplicata_no_mesmo_lote', to_jsonb(r.*)
FROM tmp_lote_canonico r
WHERE r.rn > 1;

CREATE TEMP TABLE tmp_lote AS SELECT * FROM tmp_lote_canonico WHERE rn = 1;

-- 2) curso não existe -> rejeita, não segue pro resto da linha
INSERT INTO core.linha_rejeitada (origem, identificador, motivo, linha_bruta)
SELECT 'stg_lote_matriculas', cpf, 'curso_inexistente', to_jsonb(t.*)
FROM tmp_lote t
WHERE NOT EXISTS (SELECT 1 FROM core.curso c WHERE c.id_curso = t.curso_id);

CREATE TEMP TABLE tmp_lote_curso_ok AS
SELECT * FROM tmp_lote t
WHERE EXISTS (SELECT 1 FROM core.curso c WHERE c.id_curso = t.curso_id);

-- 3) e-mail obrigatório ausente E aluno ainda não existe -> não dá pra cadastrar
INSERT INTO core.linha_rejeitada (origem, identificador, motivo, linha_bruta)
SELECT 'stg_lote_matriculas', cpf, 'campo_obrigatorio_ausente:email', to_jsonb(t.*)
FROM tmp_lote_curso_ok t
WHERE nullif(trim(t.email), '') IS NULL
  AND NOT EXISTS (SELECT 1 FROM core.alunos a WHERE a.cpf = trim(t.cpf));

-- 3b) nome incompleto (só 1 palavra) E aluno ainda não existe -> não cadastra
INSERT INTO core.linha_rejeitada (origem, identificador, motivo, linha_bruta)
SELECT 'stg_lote_matriculas', cpf, 'nome_incompleto', to_jsonb(t.*)
FROM tmp_lote_curso_ok t
WHERE array_length(regexp_split_to_array(trim(t.nome), '\s+'), 1) < 2
  AND NOT EXISTS (SELECT 1 FROM core.alunos a WHERE a.cpf = trim(t.cpf));

-- 4) aluno já existe, dado diverge -> pendência, NÃO processa matrícula desta linha
--    (não duplica se já existe pendência igual em aberto pra esse cpf/campo)
INSERT INTO core.pendencia_cadastro (cpf, campo_divergente, valor_atual, valor_novo)
SELECT trim(t.cpf), 'nome', a.nome, trim(t.nome)
FROM tmp_lote_curso_ok t
JOIN core.alunos a ON a.cpf = trim(t.cpf)
WHERE a.nome <> trim(t.nome)
  AND NOT EXISTS (
      SELECT 1 FROM core.pendencia_cadastro p
      WHERE p.cpf = trim(t.cpf) AND p.campo_divergente = 'nome' AND p.status = 'pendente'
  )
UNION ALL
SELECT trim(t.cpf), 'email', a.email, lower(trim(t.email))
FROM tmp_lote_curso_ok t
JOIN core.alunos a ON a.cpf = trim(t.cpf)
WHERE nullif(trim(t.email), '') IS NOT NULL AND a.email <> lower(trim(t.email))
  AND NOT EXISTS (
      SELECT 1 FROM core.pendencia_cadastro p
      WHERE p.cpf = trim(t.cpf) AND p.campo_divergente = 'email' AND p.status = 'pendente'
  );

-- 5) aluno novo (não existe, tem e-mail e nome completo) -> cadastra
INSERT INTO core.alunos (cpf, nome, email, data_nascimento, orgao_lotacao, cargo, data_admissao)
SELECT trim(t.cpf), trim(t.nome), lower(trim(t.email)),
       nullif(t.data_nascimento, '')::date, nullif(t.orgao_lotacao, ''),
       nullif(t.cargo, ''), nullif(t.data_admissao, '')::date
FROM tmp_lote_curso_ok t
WHERE nullif(trim(t.email), '') IS NOT NULL
  AND array_length(regexp_split_to_array(trim(t.nome), '\s+'), 1) >= 2
  AND NOT EXISTS (SELECT 1 FROM core.alunos a WHERE a.cpf = trim(t.cpf));

-- 6) matrícula: só pra linha com aluno válido (novo ou existente SEM divergência)
--    e sem matrícula ativa nesse curso ainda.
CREATE TEMP TABLE tmp_lote_matricula AS
SELECT t.*, a.id_aluno
FROM tmp_lote_curso_ok t
JOIN core.alunos a ON a.cpf = trim(t.cpf)
WHERE NOT EXISTS (
    -- exclui linha cujo aluno ficou pendente de divergência nesta carga
    SELECT 1 FROM core.pendencia_cadastro p
    WHERE p.cpf = trim(t.cpf) AND p.status = 'pendente'
);

INSERT INTO core.linha_rejeitada (origem, identificador, motivo, linha_bruta)
SELECT 'stg_lote_matriculas', cpf, 'ja_matriculado_no_curso', to_jsonb(t.*)
FROM tmp_lote_matricula t
WHERE EXISTS (
    SELECT 1 FROM core.matricula m
    WHERE m.id_aluno = t.id_aluno AND m.id_curso = t.curso_id AND m.status = 'em_andamento'
);

INSERT INTO core.matricula (id_aluno, id_curso, status, data_matricula, data_inicio)
SELECT t.id_aluno, t.curso_id, 'em_andamento', current_date,
       coalesce(nullif(t.data_inicio_desejada, '')::date, current_date)
FROM tmp_lote_matricula t
WHERE NOT EXISTS (
    SELECT 1 FROM core.matricula m
    WHERE m.id_aluno = t.id_aluno AND m.id_curso = t.curso_id AND m.status = 'em_andamento'
)
ON CONFLICT (id_aluno, id_curso) WHERE status = 'em_andamento' DO NOTHING;

DROP TABLE tmp_lote_canonico;
DROP TABLE tmp_lote;
DROP TABLE tmp_lote_curso_ok;
DROP TABLE tmp_lote_matricula;
