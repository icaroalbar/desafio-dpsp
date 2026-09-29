-- Reconciliação AVA (fonte primária) vs Power BI (extração derivada),
-- por curso. Requer staging.stg_powerbi_base carregada (ver README) e
-- core.matricula populada (Desafios 1/2, mesmo Postgres).

SELECT
    p.curso_id,
    p.curso_nome,
    p.total_inscritos_powerbi::int                                   AS powerbi,
    count(m.id_matricula)                                            AS ava_total,
    count(m.id_matricula) FILTER (WHERE m.status <> 'cancelado')     AS ava_sem_cancelado,
    p.total_inscritos_powerbi::int - count(m.id_matricula)           AS diferenca
FROM staging.stg_powerbi_base p
LEFT JOIN core.matricula m ON m.id_curso = p.curso_id
GROUP BY p.curso_id, p.curso_nome, p.total_inscritos_powerbi
ORDER BY p.curso_id;
