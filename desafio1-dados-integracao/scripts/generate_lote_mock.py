"""
Gera data/raw/planilha_lote_matriculas.csv — UMA planilha só, 1 linha =
1 pessoa + 1 curso que ela quer se matricular (como um formulário).

Puxa alunos/matrículas JÁ existentes no banco (core.alunos/core.matricula)
pra montar casos realistas de sobreposição: gente nova, gente que já é
aluno pedindo curso novo, gente com dado divergente (testa pendência),
gente pedindo curso que já está cursando (testa "já matriculado").

Requer o banco já populado (rodar depois do fluxo do Desafio 1 histórico).
"""
import csv
import os
import random
import unicodedata
from datetime import date, timedelta

import psycopg2

random.seed(7)

OUT_DIR = "data/raw"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRIMEIROS_NOMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Elaine", "Fábio", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Leonardo", "Marina", "Nelson", "Otávio", "Patrícia",
    "Rafael", "Sabrina", "Thiago", "Vanessa", "William", "Yasmin", "Camila", "Diego",
]
SOBRENOMES = [
    "Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Rodrigues", "Almeida",
    "Nascimento", "Lima", "Araújo", "Fernandes", "Carvalho", "Gomes", "Martins", "Rocha",
]
ORGAOS = [
    "Núcleo Especializado de Infância e Juventude", "Unidade de Atendimento - Santos",
    "Núcleo de Cidadania e Direitos Humanos", "Assessoria de Tecnologia da Informação",
]
CARGOS = ["Defensor Público", "Assistente Jurídico", "Analista de Sistemas", "Técnico Administrativo"]
CURSOS = {
    "C01": "Onboarding Institucional EDEPE",
    "C02": "LGPD Aplicada ao Serviço Público",
    "C03": "Atendimento ao Público e Direitos Humanos",
    "C04": "Introdução ao Processo Judicial Eletrônico",
    "C05": "Ética e Conduta no Serviço Público",
    "C06": "Acessibilidade Digital",
    "C07": "Segurança da Informação Básica",
}
CURSOS_VALIDOS = list(CURSOS.keys())


def escolher_curso():
    curso_id = random.choice(CURSOS_VALIDOS)
    return curso_id, CURSOS[curso_id]


def data_inicio_desejada():
    return (date(2026, 9, 1) + timedelta(days=random.randint(0, 60))).isoformat()


def strip_accents(txt):
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def gen_cpf(i):
    n = f"{i:09d}"
    return f"{n[0:3]}.{n[3:6]}.{n[6:9]}-{random.randint(10, 99)}"


def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


def fetch_existentes():
    load_env()
    conn = psycopg2.connect(
        host="localhost", port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB"), user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )
    with conn.cursor() as cur:
        cur.execute("SELECT cpf, nome, email FROM core.alunos ORDER BY random() LIMIT 30")
        alunos = cur.fetchall()
        cur.execute("""
            SELECT a.cpf, a.nome, a.email, m.id_curso
            FROM core.alunos a JOIN core.matricula m ON m.id_aluno = a.id_aluno
            WHERE m.status = 'em_andamento' ORDER BY random() LIMIT 15
        """)
        ativos = cur.fetchall()
    conn.close()
    return alunos, ativos


def novo_nome():
    return f"{random.choice(PRIMEIROS_NOMES)} {random.choice(SOBRENOMES)} {random.choice(SOBRENOMES)}"


def main():
    alunos, ativos = fetch_existentes()
    linhas = []

    # 1) gente nova pedindo curso (caso comum: cadastra aluno + matricula)
    for i in range(40):
        nome = novo_nome()
        cpf = gen_cpf(50000 + i)
        curso_id, curso_nome = escolher_curso()
        linhas.append({
            "cpf": cpf, "nome": nome,
            "email": f"{strip_accents(nome).lower().replace(' ', '.')}@edepe.sp.gov.br",
            "data_nascimento": date(1985, 1, 1).isoformat(),
            "orgao_lotacao": random.choice(ORGAOS), "cargo": random.choice(CARGOS),
            "data_admissao": date(2022, 3, 1).isoformat(),
            "curso_id": curso_id, "curso_nome": curso_nome,
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 2) aluno já existe, dado bate, pede curso NOVO (não é o que já tem ativo)
    ativos_cpfs = {a[0] for a in ativos}
    ja_aluno_sem_conflito = [a for a in alunos if a[0] not in ativos_cpfs][:10]
    for cpf, nome, email in ja_aluno_sem_conflito:
        curso_id, curso_nome = escolher_curso()
        linhas.append({
            "cpf": cpf, "nome": nome, "email": email,
            "data_nascimento": "", "orgao_lotacao": "", "cargo": "", "data_admissao": "",
            "curso_id": curso_id, "curso_nome": curso_nome,
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 3) aluno já existe, mas dado DIVERGE (nome/email diferente) -> pendência
    for cpf, nome, email in alunos[10:18]:
        curso_id, curso_nome = escolher_curso()
        linhas.append({
            "cpf": cpf, "nome": nome.upper(),  # diverge de propósito
            "email": "outro." + email,          # diverge de propósito
            "data_nascimento": "", "orgao_lotacao": "", "cargo": "", "data_admissao": "",
            "curso_id": curso_id, "curso_nome": curso_nome,
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 4) aluno pede curso que JÁ tem ativo -> "já matriculado", ignora
    for cpf, nome, email, curso_id in ativos[:8]:
        linhas.append({
            "cpf": cpf, "nome": nome, "email": email,
            "data_nascimento": "", "orgao_lotacao": "", "cargo": "", "data_admissao": "",
            "curso_id": curso_id, "curso_nome": CURSOS[curso_id],
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 5) curso que não existe -> rejeita
    for i in range(5):
        nome = novo_nome()
        cpf = gen_cpf(60000 + i)
        linhas.append({
            "cpf": cpf, "nome": nome,
            "email": f"{strip_accents(nome).lower().replace(' ', '.')}@edepe.sp.gov.br",
            "data_nascimento": "", "orgao_lotacao": "", "cargo": "", "data_admissao": "",
            "curso_id": "C99", "curso_nome": "Curso Descontinuado",
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 6) e-mail faltando -> rejeita (obrigatório ausente)
    for i in range(5):
        nome = novo_nome()
        cpf = gen_cpf(61000 + i)
        curso_id, curso_nome = escolher_curso()
        linhas.append({
            "cpf": cpf, "nome": nome, "email": "",
            "data_nascimento": "", "orgao_lotacao": "", "cargo": "", "data_admissao": "",
            "curso_id": curso_id, "curso_nome": curso_nome,
            "data_inicio_desejada": data_inicio_desejada(),
        })

    # 7) mesma pessoa enviada 2x no mesmo lote (erro de preenchimento duplicado)
    for i in range(4):
        nome = novo_nome()
        cpf = gen_cpf(62000 + i)
        curso_id, curso_nome = escolher_curso()
        base = {
            "cpf": cpf, "nome": nome,
            "email": f"{strip_accents(nome).lower().replace(' ', '.')}@edepe.sp.gov.br",
            "data_nascimento": date(1990, 5, 5).isoformat(), "orgao_lotacao": random.choice(ORGAOS),
            "cargo": random.choice(CARGOS), "data_admissao": date(2023, 1, 1).isoformat(),
            "curso_id": curso_id, "curso_nome": curso_nome,
            "data_inicio_desejada": data_inicio_desejada(),
        }
        linhas.append(dict(base))
        duplicata = dict(base)
        duplicata["email"] = ""  # a repetição vem incompleta (cenário comum: 2ª tentativa mal preenchida)
        linhas.append(duplicata)

    random.shuffle(linhas)

    with open(f"{OUT_DIR}/planilha_lote_matriculas.csv", "w", newline="", encoding="utf-8") as f:
        campos = ["cpf", "nome", "email", "data_nascimento", "orgao_lotacao",
                  "cargo", "data_admissao", "curso_id", "curso_nome", "data_inicio_desejada"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)

    print(f"planilha_lote_matriculas.csv: {len(linhas)} linhas")
    print(f"  - {len(ja_aluno_sem_conflito)} aluno já existente pedindo curso novo")
    print(f"  - 8 divergência de cadastro (pendência esperada)")
    print(f"  - 8 já matriculado no curso (esperado ignorar)")
    print(f"  - 5 curso inexistente | 5 e-mail ausente | 4 duplicata no mesmo lote")


if __name__ == "__main__":
    main()
