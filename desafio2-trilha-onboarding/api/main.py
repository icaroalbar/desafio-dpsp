"""
API do Desafio 2 — trilha de onboarding.

POST /alunos             -> cadastra aluno, matricula automático nos 3
                            cursos obrigatórios da trilha.
GET  /alunos/{id}/trilha -> detalhe da trilha do aluno: status de cada
                            curso, nota, recuperação, prazo, motivo de
                            reprovação e situação global. Tudo calculado
                            na hora — nenhum status fica "congelado" no
                            banco esperando um job passar pra atualizar.

Reaproveita core.alunos/core.curso/core.matricula do Desafio 1 (mesmo
Postgres). Regras de negócio (confirmadas na conversa com o "pedagógico"):

- Matrícula automática nos 3 cursos da trilha assim que o aluno é cadastrado.
- Prazo de 60 dias corridos (a partir do cadastro) pra concluir os 3.
- Nota mínima 7,0 em CADA curso, independente (não é média pra aprovar).
- Nota < 7 na 1ª tentativa -> 3 dias de recuperação. Recuperação >= 7 aprova
  (nota que vale é a da recuperação). Recuperação < 7 ou não fez a tempo -> reprovado.
- Estourou os 60 dias sem concluir um curso -> reprovado (motivo prazo_expirado)
  e entra na fila de espera desse curso pra próxima turma.
"""
import os
from datetime import date, timedelta
from typing import Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from api.certificado import gerar_certificado_pdf

app = FastAPI(title="EDEPE - Trilha de Onboarding (demo)")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BASE_DIR)

TRILHA_NOME = "Onboarding Institucional"
TRILHA_CURSOS = ["C01", "C02", "C05"]  # Onboarding, LGPD, Ética
PRAZO_TRILHA_DIAS = 60
PRAZO_RECUPERACAO_DIAS = 3
NOTA_CORTE = 7.0


def load_env():
    # o .env com credencial do Postgres já existe no Desafio 1 — reaproveita
    env_path = os.path.join(REPO_ROOT, "desafio1-dados-integracao", ".env")
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


class AlunoIn(BaseModel):
    cpf: str
    nome: str
    email: str
    data_nascimento: Optional[date] = None
    orgao_lotacao: Optional[str] = None
    cargo: Optional[str] = None
    data_admissao: Optional[date] = None


@app.post("/alunos", status_code=201)
def cadastrar_aluno(aluno: AlunoIn):
    nome = aluno.nome.strip()
    if len(nome.split()) < 2:
        raise HTTPException(400, "nome incompleto: informe nome completo (nome + sobrenome)")
    if not aluno.email.strip():
        raise HTTPException(400, "email é obrigatório")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id_aluno FROM core.alunos WHERE cpf = %s", (aluno.cpf,))
            if cur.fetchone():
                raise HTTPException(409, f"já existe aluno cadastrado com cpf {aluno.cpf}")

            cur.execute(
                """INSERT INTO core.alunos (cpf, nome, email, data_nascimento,
                       orgao_lotacao, cargo, data_admissao)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_aluno""",
                (aluno.cpf, nome, aluno.email.strip().lower(), aluno.data_nascimento,
                 aluno.orgao_lotacao, aluno.cargo, aluno.data_admissao),
            )
            id_aluno = cur.fetchone()[0]

            hoje = date.today()
            matriculas_criadas = []
            for curso_id in TRILHA_CURSOS:
                cur.execute(
                    """INSERT INTO core.matricula (id_aluno, id_curso, status, data_matricula, data_inicio)
                       VALUES (%s,%s,'em_andamento',%s,%s) RETURNING id_matricula""",
                    (id_aluno, curso_id, hoje, hoje),
                )
                matriculas_criadas.append({"id_matricula": cur.fetchone()[0], "curso_id": curso_id})
        conn.commit()
    finally:
        conn.close()

    return {
        "id_aluno": id_aluno,
        "cpf": aluno.cpf,
        "nome": nome,
        "trilha": TRILHA_NOME,
        "matriculado_em": [m["curso_id"] for m in matriculas_criadas],
        "prazo_final": (hoje + timedelta(days=PRAZO_TRILHA_DIAS)).isoformat(),
    }


def _nota_vigente(nota, nota_recuperacao):
    return nota_recuperacao if nota_recuperacao is not None else nota


def _avaliar_curso(row, hoje, data_final_trilha):
    (curso_id, curso_nome, carga_horaria, status_matricula, nota, data_conclusao,
     nota_recuperacao, data_conclusao_recuperacao) = row

    base = {
        "curso_id": curso_id,
        "curso_nome": curso_nome,
        "carga_horaria": carga_horaria,
        "nota": float(nota) if nota is not None else None,
        "data_conclusao": data_conclusao.isoformat() if data_conclusao else None,
        "nota_recuperacao": float(nota_recuperacao) if nota_recuperacao is not None else None,
        "data_segunda_prova": data_conclusao_recuperacao.isoformat() if data_conclusao_recuperacao else None,
        "data_limite_recuperacao": None,
        "motivo": None,
        "orientacao": None,
    }

    if data_conclusao is None:
        if hoje > data_final_trilha:
            base.update(status="concluido", situacao="reprovado", motivo="prazo_expirado",
                        orientacao=("Prazo de 60 dias esgotado. Procure a coordenação do curso "
                                    "— você foi colocado na fila de espera da próxima turma."))
        else:
            base.update(status="em_andamento", situacao="cursando")
        return base

    vigente = _nota_vigente(nota, nota_recuperacao)

    if vigente is not None and float(vigente) >= NOTA_CORTE:
        base.update(status="concluido", situacao="aprovado")
        return base

    if nota_recuperacao is not None:
        base.update(status="concluido", situacao="reprovado", motivo="nota_abaixo_da_media")
        return base

    data_limite_recuperacao = data_conclusao + timedelta(days=PRAZO_RECUPERACAO_DIAS)
    base["data_limite_recuperacao"] = data_limite_recuperacao.isoformat()
    if hoje <= data_limite_recuperacao:
        base.update(status="em_andamento", situacao="em_recuperacao")
    else:
        base.update(status="concluido", situacao="reprovado", motivo="nota_abaixo_da_media")
    return base


def _montar_trilha(conn, id_aluno):
    """Monta o retorno de /trilha. Levanta HTTPException 404 se não achar
    aluno/matrícula. Usado tanto pela consulta quanto pelo certificado —
    lógica de avaliação mora só aqui."""
    with conn.cursor() as cur:
        cur.execute("SELECT id_aluno, nome, cpf FROM core.alunos WHERE id_aluno = %s", (id_aluno,))
        aluno_row = cur.fetchone()
        if not aluno_row:
            raise HTTPException(404, "aluno não encontrado")

        cur.execute(
            """SELECT c.id_curso, c.nome, c.carga_horaria, m.status, m.nota_final,
                      m.data_conclusao, m.nota_recuperacao, m.data_conclusao_recuperacao,
                      m.data_inicio, m.id_matricula
               FROM core.matricula m
               JOIN core.curso c ON c.id_curso = m.id_curso
               WHERE m.id_aluno = %s AND m.id_curso = ANY(%s)
               ORDER BY m.id_matricula DESC""",
            (id_aluno, TRILHA_CURSOS),
        )
        todas = cur.fetchall()

    # pega só a matrícula mais recente por curso (defensivo, caso exista mais de uma)
    por_curso = {}
    for r in todas:
        if r[0] not in por_curso:
            por_curso[r[0]] = r
    if not por_curso:
        raise HTTPException(404, "aluno não está matriculado na trilha de onboarding")

    hoje = date.today()
    data_inicio = min(r[8] for r in por_curso.values())
    data_final = data_inicio + timedelta(days=PRAZO_TRILHA_DIAS)

    cursos_avaliados = [
        _avaliar_curso(r[:8], hoje, data_final) for r in por_curso.values()
    ]

    # efeito colateral: reprovado por prazo entra na fila de espera (idempotente)
    with conn.cursor() as cur:
        for c in cursos_avaliados:
            if c["motivo"] == "prazo_expirado":
                cur.execute(
                    """INSERT INTO core.fila_espera (id_aluno, id_curso, motivo)
                       VALUES (%s,%s,'prazo_expirado')
                       ON CONFLICT (id_aluno, id_curso, status) DO NOTHING""",
                    (id_aluno, c["curso_id"]),
                )
        conn.commit()

    situacoes = [c["situacao"] for c in cursos_avaliados]
    if "reprovado" in situacoes:
        status_global = "reprovado"
    elif all(s == "aprovado" for s in situacoes):
        status_global = "concluido"
    else:
        status_global = "em_andamento"

    notas_fechadas = [
        _nota_vigente(c["nota"], c["nota_recuperacao"])
        for c in cursos_avaliados if c["situacao"] in ("aprovado", "reprovado")
    ]
    # reprovado por prazo_expirado não tem nota nenhuma lançada -> não entra na média
    notas_fechadas = [n for n in notas_fechadas if n is not None]
    media_notas_atual = round(sum(notas_fechadas) / len(notas_fechadas), 2) if notas_fechadas else None

    return {
        "aluno": {"id_aluno": aluno_row[0], "nome": aluno_row[1], "cpf": aluno_row[2]},
        "trilha": TRILHA_NOME,
        "data_inicio": data_inicio.isoformat(),
        "data_final": data_final.isoformat(),
        "status_global": status_global,
        "media_notas_atual": media_notas_atual,
        "cursos": cursos_avaliados,
    }


@app.get("/alunos/{id_aluno}/trilha")
def consultar_trilha(id_aluno: int):
    conn = get_conn()
    try:
        return _montar_trilha(conn, id_aluno)
    finally:
        conn.close()


@app.get("/alunos/{id_aluno}/certificado")
def emitir_certificado(id_aluno: int):
    conn = get_conn()
    try:
        trilha = _montar_trilha(conn, id_aluno)

        if trilha["status_global"] != "concluido":
            pendencias = [
                {"curso_id": c["curso_id"], "curso_nome": c["curso_nome"], "situacao": c["situacao"]}
                for c in trilha["cursos"] if c["situacao"] != "aprovado"
            ]
            raise HTTPException(409, {
                "erro": "trilha ainda não concluída, certificado não pode ser emitido",
                "status_global": trilha["status_global"],
                "pendencias": pendencias,
            })

        with conn.cursor() as cur:
            cur.execute(
                "SELECT protocolo, carga_horaria, data_conclusao FROM core.certificado "
                "WHERE id_aluno = %s AND trilha = %s",
                (id_aluno, TRILHA_NOME),
            )
            existente = cur.fetchone()

            if existente:
                protocolo, carga_horaria_total, data_conclusao_trilha = existente
            else:
                carga_horaria_total = sum(c["carga_horaria"] for c in trilha["cursos"])
                data_conclusao_trilha = max(
                    date.fromisoformat(c["data_segunda_prova"] if c["nota_recuperacao"] is not None
                                        else c["data_conclusao"])
                    for c in trilha["cursos"]
                )
                cur.execute(
                    """INSERT INTO core.certificado (id_aluno, trilha, carga_horaria, data_conclusao)
                       VALUES (%s,%s,%s,%s) RETURNING protocolo""",
                    (id_aluno, TRILHA_NOME, carga_horaria_total, data_conclusao_trilha),
                )
                protocolo = cur.fetchone()[0]
                conn.commit()

        cursos_pdf = [
            {
                "curso_nome": c["curso_nome"],
                "carga_horaria": c["carga_horaria"],
                "nota": _nota_vigente(c["nota"], c["nota_recuperacao"]),
            }
            for c in trilha["cursos"]
        ]

        pdf_bytes = gerar_certificado_pdf(
            aluno_nome=trilha["aluno"]["nome"],
            aluno_cpf=trilha["aluno"]["cpf"],
            trilha_nome=TRILHA_NOME,
            cursos=cursos_pdf,
            carga_horaria_total=carga_horaria_total,
            data_conclusao=data_conclusao_trilha,
            protocolo=protocolo,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="certificado_{id_aluno}.pdf"'},
        )
    finally:
        conn.close()
