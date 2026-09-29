"""
API do Desafio 1 — síncrona por enquanto.

POST /lotes/matriculas -> planilha única, 1 linha = aluno + curso desejado
(como um formulário). NÃO reseta o banco — cada chamada é um lote novo
empilhado sobre o que já existe (aluno já cadastrado? já matriculado nesse
curso? diverge? tudo checado contra o estado atual). Ao final, gera .xlsx
com o que não foi processado e manda por e-mail.
"""
import csv
import io
import os
import subprocess

import psycopg2
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from api.email_sender import enviar_relatorio
from api.report import gerar_relatorio_xlsx

app = FastAPI(title="EDEPE - Matrículas em lote (demo)")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


load_env()


def get_conn():
    return psycopg2.connect(
        host="localhost",
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )


@app.post("/lotes/matriculas")
async def processar_lote_form(
    planilha: UploadFile = File(...),
    email_destino: str = Form("pedagogico@edepe.sp.gov.br"),
):
    """Formulário real: 1 planilha, 1 linha = aluno + curso que ele quer fazer.
    Ao final, gera .xlsx com o que não foi processado e manda por e-mail."""
    rows = list(csv.DictReader(io.StringIO((await planilha.read()).decode("utf-8"))))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # marca o "antes" pra depois pegar só o que ESTE lote gerou
            cur.execute("SELECT coalesce(max(id), 0) FROM core.linha_rejeitada")
            id_rejeitada_antes = cur.fetchone()[0]
            cur.execute("SELECT coalesce(max(id), 0) FROM core.pendencia_cadastro")
            id_pendencia_antes = cur.fetchone()[0]

            cur.execute("TRUNCATE staging.stg_lote_matriculas;")
            cur.executemany(
                """INSERT INTO staging.stg_lote_matriculas
                   (cpf, nome, email, data_nascimento, orgao_lotacao, cargo,
                    data_admissao, curso_id, curso_nome, data_inicio_desejada, arquivo_origem)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [
                    (r["cpf"], r["nome"], r["email"] or None, r["data_nascimento"] or None,
                     r["orgao_lotacao"] or None, r["cargo"] or None, r["data_admissao"] or None,
                     r["curso_id"], r["curso_nome"], r["data_inicio_desejada"] or None,
                     planilha.filename)
                    for r in rows
                ],
            )
        conn.commit()
    finally:
        conn.close()

    sql_comparativo = open(os.path.join(BASE_DIR, "sql", "005_comparativo_lote.sql")).read()
    resultado = subprocess.run(
        ["docker", "exec", "-i", "edepe_postgres", "psql", "-v", "ON_ERROR_STOP=1",
         "-U", os.environ["POSTGRES_USER"], "-d", os.environ["POSTGRES_DB"]],
        input=sql_comparativo, capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        return JSONResponse(status_code=500, content={"erro": resultado.stderr})

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM core.alunos")
            total_alunos = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM core.matricula")
            total_matriculas = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM core.pendencia_cadastro WHERE status='pendente'")
            total_pendencias = cur.fetchone()[0]

            cur.execute("""
                SELECT motivo, count(*) FROM core.linha_rejeitada
                WHERE origem = 'stg_lote_matriculas' AND id > %s
                GROUP BY motivo ORDER BY 2 DESC
            """, (id_rejeitada_antes,))
            eventos_deste_lote = cur.fetchall()

            cur.execute("""
                SELECT motivo, linha_bruta FROM core.linha_rejeitada
                WHERE origem = 'stg_lote_matriculas' AND id > %s
            """, (id_rejeitada_antes,))
            rejeitados_deste_lote = cur.fetchall()

            cur.execute("""
                SELECT p.cpf, a.nome, a.email, p.campo_divergente, p.valor_atual, p.valor_novo
                FROM core.pendencia_cadastro p
                JOIN core.alunos a ON a.cpf = p.cpf
                WHERE p.id > %s
            """, (id_pendencia_antes,))
            pendencias_deste_lote = cur.fetchall()
    finally:
        conn.close()

    email_enviado = False
    erro_email = None
    total_nao_processado = len(rejeitados_deste_lote) + len(pendencias_deste_lote)
    if total_nao_processado > 0:
        xlsx_bytes = gerar_relatorio_xlsx(rejeitados_deste_lote, pendencias_deste_lote)
        try:
            enviar_relatorio(
                destinatario=email_destino,
                assunto=f"EDEPE - Lote de matrículas processado ({total_nao_processado} pendência(s))",
                corpo=(
                    f"Lote '{planilha.filename}' processado.\n"
                    f"{len(rows)} linha(s) recebida(s), {total_nao_processado} não processada(s) "
                    f"(ver planilha em anexo com o motivo de cada uma).\n"
                ),
                anexo_bytes=xlsx_bytes,
                anexo_nome="relatorio_nao_processados.xlsx",
            )
            email_enviado = True
        except Exception as e:  # noqa: BLE001 - reporta qualquer falha de SMTP no JSON
            erro_email = str(e)

    return {
        "total_linhas_recebidas": len(rows),
        "total_alunos_cadastrados_no_banco": total_alunos,
        "total_matriculas_ativas_no_banco": total_matriculas,
        "total_pendencias_em_aberto": total_pendencias,
        "eventos_deste_lote": [{"motivo": m, "quantidade": q} for m, q in eventos_deste_lote],
        "relatorio_email": {
            "enviado": email_enviado,
            "destinatario": email_destino if total_nao_processado > 0 else None,
            "erro": erro_email,
        },
    }
