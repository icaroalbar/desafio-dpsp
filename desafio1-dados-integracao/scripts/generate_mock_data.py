"""
Gera os 3 arquivos mock do Desafio 1 (dados sujos de propósito):

  data/raw/participantes.csv     -> base de participantes (com duplicatas e incompletos)
  data/raw/api_matriculas.json   -> retorno de API de matrícula/conclusão (com registros órfãos)
  data/raw/powerbi_base.csv      -> extração "desatualizada" usada no Power BI (diverge do AVA)

Reprodutível: seed fixa. Rodar de novo gera exatamente os mesmos arquivos.
"""
import csv
import json
import random
import unicodedata
from datetime import date, timedelta

random.seed(42)

OUT_DIR = "data/raw"

PRIMEIROS_NOMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Elaine", "Fábio", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Leonardo", "Marina", "Nelson", "Otávio", "Patrícia",
    "Rafael", "Sabrina", "Thiago", "Vanessa", "William", "Yasmin", "Camila", "Diego",
    "Eduarda", "Felipe", "Giovanna", "Hugo", "Ingrid", "José", "Larissa", "Marcelo",
    "Natália", "Paulo", "Renata", "Sérgio", "Tatiane", "Vinícius", "Aline", "Bruna",
    "Caio", "Débora", "Ernesto", "Flávia", "Gustavo", "Helena", "Igor", "Juliana",
    "Kléber", "Luciana",
]
SOBRENOMES = [
    "Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Rodrigues", "Almeida",
    "Nascimento", "Lima", "Araújo", "Fernandes", "Carvalho", "Gomes", "Martins", "Rocha",
    "Ribeiro", "Alves", "Monteiro", "Cardoso", "Teixeira", "Correia", "Barbosa", "Pinto",
    "Moreira", "Cavalcanti", "Dias", "Castro", "Campos", "Freitas",
]

ORGAOS = [
    "Núcleo Especializado de Infância e Juventude",
    "Unidade de Atendimento - Santos",
    "Unidade de Atendimento - Campinas",
    "Núcleo de Cidadania e Direitos Humanos",
    "Núcleo Especializado da Mulher",
    "Assessoria de Tecnologia da Informação",
    "Escola da Defensoria Pública - EDEPE",
    "Núcleo de Habitação e Urbanismo",
    "Unidade de Atendimento - Sede",
    "Núcleo de Situação Carcerária",
]
CARGOS = [
    "Defensor Público", "Assistente Jurídico", "Analista de Sistemas",
    "Técnico Administrativo", "Assessor Jurídico", "Estagiário de Direito",
    "Analista de Dados", "Oficial de Defensoria",
]

CURSOS = [
    ("C01", "Onboarding Institucional EDEPE", 20),
    ("C02", "LGPD Aplicada ao Serviço Público", 12),
    ("C03", "Atendimento ao Público e Direitos Humanos", 16),
    ("C04", "Introdução ao Processo Judicial Eletrônico", 24),
    ("C05", "Ética e Conduta no Serviço Público", 8),
    ("C06", "Acessibilidade Digital", 10),
    ("C07", "Segurança da Informação Básica", 6),
]

STATUS_VARIANTES = {
    "concluido": ["Concluído", "concluido", "CONCLUIDO", "Concluido "],
    "andamento": ["Em andamento", "em andamento", "EM ANDAMENTO"],
    "cancelado": ["Cancelado", "cancelado", "CANCELADO"],
    "nao_iniciado": ["Não iniciado", "nao iniciado", "Não Iniciado"],
}


def strip_accents(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def gen_cpf(i: int) -> str:
    n = f"{i:09d}"
    return f"{n[0:3]}.{n[3:6]}.{n[6:9]}-{random.randint(10, 99)}"


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def build_participantes(n=150):
    participantes = []
    for i in range(1, n + 1):
        nome = f"{random.choice(PRIMEIROS_NOMES)} {random.choice(SOBRENOMES)} {random.choice(SOBRENOMES)}"
        cpf = gen_cpf(i)
        email = f"{strip_accents(nome).lower().replace(' ', '.')}@edepe.sp.gov.br"
        nascimento = random_date(date(1970, 1, 1), date(2003, 12, 31))
        participantes.append({
            "id_participante": f"P{i:04d}",
            "cpf": cpf,
            "nome": nome,
            "email": email,
            "data_nascimento": nascimento.isoformat(),
            "orgao_lotacao": random.choice(ORGAOS),
            "cargo": random.choice(CARGOS),
            "data_admissao": random_date(date(2015, 1, 1), date(2026, 8, 1)).isoformat(),
        })
    return participantes


def inject_duplicatas(participantes, n_exatas=8, n_variantes=12):
    linhas = list(participantes)

    for p in random.sample(participantes, n_exatas):
        linhas.append(dict(p))

    for p in random.sample(participantes, n_variantes):
        variante = dict(p)
        variante["id_participante"] = variante["id_participante"] + "-DUP"
        estilo = random.choice(["upper", "sem_acento", "espacos"])
        if estilo == "upper":
            variante["nome"] = variante["nome"].upper()
            variante["email"] = variante["email"].upper()
        elif estilo == "sem_acento":
            variante["nome"] = strip_accents(variante["nome"])
        else:
            variante["nome"] = "  " + variante["nome"] + "  "
        linhas.append(variante)

    random.shuffle(linhas)
    return linhas


def inject_incompletos(linhas, n=20):
    alvos = random.sample(linhas, n)
    for row in alvos:
        campo = random.choice(["email", "data_nascimento", "orgao_lotacao", "nome"])
        if campo == "nome":
            partes = row["nome"].split()
            row["nome"] = partes[0] if partes else ""
        else:
            row[campo] = ""
    return linhas


def build_matriculas(participantes, n_orfaos=25):
    matriculas = []
    mid = 1

    def novo_registro(cpf):
        nonlocal mid
        curso_id, curso_nome, carga = random.choice(CURSOS)
        status_grupo = random.choices(
            ["concluido", "andamento", "cancelado", "nao_iniciado"],
            weights=[45, 30, 10, 15],
        )[0]
        status = random.choice(STATUS_VARIANTES[status_grupo])

        data_inicio = random_date(date(2025, 1, 1), date(2026, 8, 1))
        data_matricula = data_inicio - timedelta(days=random.randint(0, 5))

        data_conclusao = None
        nota_final = None
        if status_grupo == "concluido":
            data_conclusao = data_inicio + timedelta(days=random.randint(5, 90))
            if random.random() > 0.10:
                nota_final = round(random.uniform(50, 100), 1)
            if random.random() < 0.05:
                data_conclusao = data_inicio - timedelta(days=random.randint(1, 10))

        registro = {
            "id_matricula": f"M{mid:05d}",
            "cpf": cpf,
            "curso_id": curso_id,
            "curso_nome": curso_nome,
            "carga_horaria": carga,
            "status": status,
            "nota_final": nota_final,
            "data_matricula": data_matricula.isoformat(),
            "data_inicio": data_inicio.isoformat(),
            "data_conclusao": data_conclusao.isoformat() if data_conclusao else None,
        }
        mid += 1
        return registro

    for p in participantes:
        for _ in range(random.randint(1, 3)):
            matriculas.append(novo_registro(p["cpf"]))

    for i in range(n_orfaos):
        cpf_externo = gen_cpf(9000 + i)
        matriculas.append(novo_registro(cpf_externo))

    random.shuffle(matriculas)
    return matriculas


def build_powerbi_base(matriculas, cpfs_validos):
    contagem_real = {}
    for m in matriculas:
        if m["cpf"] not in cpfs_validos:
            continue
        chave = m["curso_id"]
        contagem_real.setdefault(chave, {"inscritos": 0, "concluidos": 0})
        contagem_real[chave]["inscritos"] += 1
        if m["status"].strip().lower().startswith("conclu"):
            contagem_real[chave]["concluidos"] += 1

    linhas = []
    for curso_id, curso_nome, _ in CURSOS:
        real = contagem_real.get(curso_id, {"inscritos": 0, "concluidos": 0})
        defasagem_inscritos = random.randint(-8, 3)
        defasagem_concluidos = random.randint(-5, 5)
        linhas.append({
            "mes_referencia": "2026-08",
            "curso_id": curso_id,
            "curso_nome": curso_nome,
            "total_inscritos_poweBI": max(0, real["inscritos"] + defasagem_inscritos),
            "total_concluidos_powerBI": max(0, real["concluidos"] + defasagem_concluidos),
            "extraido_em": "2026-08-25T03:00:00",
        })
    return linhas


def main():
    participantes = build_participantes(n=150)
    linhas_participantes = inject_duplicatas(participantes, n_exatas=8, n_variantes=12)
    linhas_participantes = inject_incompletos(linhas_participantes, n=20)

    matriculas = build_matriculas(participantes, n_orfaos=25)
    cpfs_validos = {p["cpf"] for p in participantes}
    powerbi_base = build_powerbi_base(matriculas, cpfs_validos)

    with open(f"{OUT_DIR}/participantes.csv", "w", newline="", encoding="utf-8") as f:
        campos = ["id_participante", "cpf", "nome", "email", "data_nascimento",
                  "orgao_lotacao", "cargo", "data_admissao"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas_participantes)

    with open(f"{OUT_DIR}/api_matriculas.json", "w", encoding="utf-8") as f:
        json.dump(matriculas, f, ensure_ascii=False, indent=2)

    with open(f"{OUT_DIR}/powerbi_base.csv", "w", newline="", encoding="utf-8") as f:
        campos = ["mes_referencia", "curso_id", "curso_nome",
                  "total_inscritos_poweBI", "total_concluidos_powerBI", "extraido_em"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(powerbi_base)

    print(f"participantes.csv: {len(linhas_participantes)} linhas "
          f"({len(participantes)} pessoas únicas + duplicatas injetadas)")
    print(f"api_matriculas.json: {len(matriculas)} registros "
          f"(incluindo {25} órfãos sem participante correspondente)")
    print(f"powerbi_base.csv: {len(powerbi_base)} linhas (1 por curso)")


if __name__ == "__main__":
    main()
