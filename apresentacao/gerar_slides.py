"""
Gera o PDF de apresentação do case técnico EDEPE (9 slides, paisagem).
Mesmo conteúdo do deck HTML, versão estática pra imprimir/compartilhar
sem depender de navegador. Reprodutível: roda de novo, gera igual.
"""
import hashlib
import textwrap

# workaround: hashlib.md5 nesta build não aceita "usedforsecurity", e o
# reportlab usa isso internamente (PDFDocument) — mesmo bug do Desafio 2.
_md5_original = hashlib.md5
hashlib.md5 = lambda *a, **kw: _md5_original(*a)

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

W, H = landscape(A4)
MARGIN = 1.6 * 72 / 2.54  # ~1.6cm em pontos... simplificado abaixo
MARGIN = 42

INK = colors.HexColor("#16211E")
MUTED = colors.HexColor("#5B6B66")
ACCENT = colors.HexColor("#1F5C55")
ACCENT_SOFT = colors.HexColor("#DCE8E5")
LINE = colors.HexColor("#D8DAD3")
OK = colors.HexColor("#2F7D4F")
WARN = colors.HexColor("#A9720A")
BAD = colors.HexColor("#B5432E")
SURFACE2 = colors.HexColor("#F4F6F2")
TERM_BG = colors.HexColor("#121A1C")
TERM_FG = colors.HexColor("#E7EDE9")
TERM_ACCENT = colors.HexColor("#7FD9C9")

TOTAL_SLIDES = 9


def wrap(text, font, size, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def frame(c):
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.rect(MARGIN * 0.5, MARGIN * 0.5, W - MARGIN, H - MARGIN, fill=0, stroke=1)


def header(c, tag, title_line, n):
    x = MARGIN
    y = H - MARGIN - 6
    # eyebrow tag
    c.setFont("Helvetica-Bold", 8)
    tag_w = stringWidth(tag.upper(), "Helvetica-Bold", 8) + 14
    c.setFillColor(ACCENT_SOFT)
    c.roundRect(x, y - 4, tag_w, 16, 3, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.drawString(x + 7, y, tag.upper())

    # protocolo
    proto = f"PROTOCOLO {n:02d}/{TOTAL_SLIDES:02d}"
    c.setFont("Courier", 8)
    c.setFillColor(MUTED)
    c.drawRightString(W - MARGIN, y, proto)

    c.setFont("Helvetica-Bold", 6.5)
    c.setFillColor(MUTED)
    c.drawString(x, H - MARGIN + 12, "CASE TÉCNICO — EDEPE · ASSESSOR(A) DE TECNOLOGIA EDUCACIONAL")

    # title
    c.setFont("Helvetica-Bold", 19)
    c.setFillColor(INK)
    ty = y - 30
    for line in wrap(title_line, "Helvetica-Bold", 19, W - 2 * MARGIN):
        c.drawString(x, ty, line)
        ty -= 23
    return ty - 8


def footer(c):
    c.setFont("Courier", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, MARGIN * 0.5 - 14, "Icaro Albar  —  case técnico EDEPE")


def bullets(c, items, x, y, width, size=10.5, gap=14, leading=13):
    c.setFont("Helvetica", size)
    for item in items:
        bold_part = None
        rest = item
        if isinstance(item, tuple):
            bold_part, rest = item
        c.setFillColor(ACCENT)
        c.drawString(x, y, "–")
        tx = x + 12
        if bold_part:
            c.setFont("Helvetica-Bold", size)
            c.setFillColor(INK)
            c.drawString(tx, y, bold_part)
            tx_after = tx + stringWidth(bold_part + " ", "Helvetica-Bold", size)
            c.setFont("Helvetica", size)
            lines = wrap(rest, "Helvetica", size, width - (tx_after - x))
            if lines:
                c.setFillColor(INK)
                c.drawString(tx_after, y, lines[0])
                y -= leading
                for extra in lines[1:]:
                    c.drawString(tx, y, extra)
                    y -= leading
            else:
                y -= leading
        else:
            c.setFillColor(INK)
            lines = wrap(rest, "Helvetica", size, width - 12)
            for li in lines:
                c.drawString(tx, y, li)
                y -= leading
        y -= (gap - leading)
    return y


def numbered_steps(c, items, x, y, width, size=10.5, leading=13, gap=16):
    for i, (label, rest) in enumerate(items, start=1):
        c.setFillColor(ACCENT_SOFT)
        c.roundRect(x, y - 10, 16, 14, 3, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(x + 8, y - 6, str(i))
        tx = x + 22
        c.setFont("Helvetica-Bold", size)
        c.setFillColor(INK)
        c.drawString(tx, y, label)
        c.setFont("Helvetica", size)
        c.setFillColor(MUTED)
        lines = wrap(rest, "Helvetica", size, width - 22)
        yy = y - leading
        for li in lines:
            c.drawString(tx, yy, li)
            yy -= leading
        y = yy - (gap - leading)
    return y


def card(c, x, y, w, h, title=None):
    c.setFillColor(SURFACE2)
    c.setStrokeColor(LINE)
    c.roundRect(x, y - h, w, h, 6, fill=1, stroke=1)
    ty = y - 16
    if title:
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(MUTED)
        c.drawString(x + 12, ty, title.upper())
        ty -= 16
    return ty


def chip_row(c, chips, x, y, size=8):
    c.setFont("Helvetica", size)
    cx = x
    for chip in chips:
        w = stringWidth(chip, "Helvetica", size) + 12
        if cx + w > W - MARGIN - 20:
            cx = x
            y -= 18
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.roundRect(cx, y - 10, w, 15, 3, fill=1, stroke=1)
        c.setFillColor(MUTED)
        c.drawString(cx + 6, y - 6, chip)
        cx += w + 6
    return y - 20


def table(c, x, y, col_widths, rows, header_row=True, size=9):
    row_h = 20
    cx = x
    for i, row in enumerate(rows):
        cx = x
        is_header = header_row and i == 0
        if not is_header:
            c.setStrokeColor(LINE)
            c.line(x, y - row_h + 6, x + sum(col_widths), y - row_h + 6)
        for j, cell in enumerate(row):
            if is_header:
                c.setFont("Helvetica-Bold", size - 1)
                c.setFillColor(MUTED)
                c.drawString(cx, y - 6, cell.upper())
            else:
                c.setFont("Helvetica", size)
                c.setFillColor(INK)
                for k, li in enumerate(wrap(cell, "Helvetica", size, col_widths[j] - 8)):
                    c.drawString(cx, y - 6 - k * 11, li)
            cx += col_widths[j]
        y -= row_h if is_header else max(row_h, 11 * max(1, len(wrap(rows[i][0], "Helvetica", size, col_widths[0] - 8))) + 8)
    return y


def pill(c, text, x, y, color):
    w = stringWidth(text, "Helvetica-Bold", 7.5) + 12
    c.setFillColor(color)
    c.roundRect(x, y - 9, w, 13, 6, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 6, y - 5, text)
    return x + w + 6


def terminal(c, x, y, w, h, lines):
    c.setFillColor(TERM_BG)
    c.roundRect(x, y - h, w, h, 6, fill=1, stroke=0)
    for i, dotc in enumerate([colors.HexColor("#e0705a"), colors.HexColor("#e0ae57"), colors.HexColor("#5cc088")]):
        c.setFillColor(dotc)
        c.circle(x + 12 + i * 12, y - 12, 3, fill=1, stroke=0)
    ty = y - 30
    for line, kind in lines:
        c.setFont("Courier", 8)
        c.setFillColor(TERM_ACCENT if kind == "cmd" else (MUTED if kind == "cmt" else TERM_FG))
        for li in textwrap.wrap(line, width=int((w - 24) / 4.9)) or [""]:
            c.drawString(x + 12, ty, li)
            ty -= 11
    return ty


def callout(c, x, y, w, text, title="Nota"):
    lines = wrap(text, "Helvetica", 9.5, w - 24)
    h = 20 + len(lines) * 13
    c.setFillColor(ACCENT_SOFT)
    c.rect(x, y - h, w, h, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(x, y - h, 3, h, fill=1, stroke=0)
    ty = y - 16
    c.setFont("Helvetica", 9.5)
    c.setFillColor(INK)
    for li in lines:
        c.drawString(x + 14, ty, li)
        ty -= 13
    return ty


# ---------------------------------------------------------------- slides --

def slide_trajetoria(c):
    frame(c)
    y = header(c, "Antes do case", "Icaro Albar — Coordenador de Inovação e Inteligência Artificial", 1)

    # avatar circle with initials
    c.setFillColor(ACCENT)
    c.circle(MARGIN + 28, y + 6, 26, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(MARGIN + 28, y - 1, "IA")
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(MARGIN + 66, y + 2, "Niterói, RJ — Brasil")

    y -= 46
    col_w = (W - 2 * MARGIN - 24) / 2
    left_x = MARGIN
    right_x = MARGIN + col_w + 24

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED)
    c.drawString(left_x, y, "TRAJETÓRIA")
    ty = y - 16
    trajetoria = [
        ("abr/2026–atual · Defensoria Pública do RJ (DPGE)",
         "Coordenador de Inovação e IA — roteiro estratégico de IA para digitalização de processos jurídicos, governança ética, discovery → PoC → piloto → escala."),
        ("jun/2023–abr/2026 · Galgtec",
         "Full Stack Sênior — arquitetura AWS de alta disponibilidade, React/TypeScript + Node.js, DevOps de deploy contínuo."),
        ("mar/2025–mar/2026 · Cloud Treinamentos",
         "Arquiteto de Soluções — AWS serverless/containers, IA com Bedrock, SageMaker e Textract."),
        ("mar/2019–dez/2022 · Grupo HP",
         "Full Stack Pleno — React, TypeScript e Node.js integrados a serviços AWS."),
    ]
    for quando, desc in trajetoria:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(ACCENT)
        for li in wrap(quando, "Helvetica-Bold", 9, col_w):
            c.drawString(left_x, ty, li)
            ty -= 11
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        for li in wrap(desc, "Helvetica", 9, col_w):
            c.drawString(left_x, ty, li)
            ty -= 11
        ty -= 8

    ty2 = card(c, right_x, y + 16, col_w, 62, "Formação")
    c.setFont("Helvetica", 9)
    c.setFillColor(INK)
    for li in wrap("MBA USP/Esalq — Engenharia de Software (em andamento)", "Helvetica", 9, col_w - 24):
        c.drawString(right_x + 12, ty2, li); ty2 -= 12
    for li in wrap("Bacharelado — Análise de Sistemas, Unigranrio (2019–2023)", "Helvetica", 9, col_w - 24):
        c.drawString(right_x + 12, ty2, li); ty2 -= 12

    stack_top = y + 16 - 62 - 14
    ty3 = card(c, right_x, stack_top, col_w, 58, "Stack")
    chip_row(c, ["Python", "Node.js/TS", "React", "AWS", "Docker", "API REST", "SQL", "Terraform"], right_x + 12, ty3 - 2)

    call_top = stack_top - 58 - 14
    callout(c, right_x, call_top, col_w,
            "Já atuo dentro de uma Defensoria Pública, liderando IA e automação em serviço público jurídico — "
            "entendo a cultura institucional e o ritmo de adoção tecnológica de um órgão público, e trago isso pra "
            "tecnologia educacional.")
    footer(c)


def slide_abertura(c):
    frame(c)
    y = header(c, "Case técnico", "Inconsistência nos dados, demanda pedagógica pendente, divergência entre painéis.", 2)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    for li in wrap("A EDEPE amplia o Programa de Educação Corporativa e estrutura o Programa de Dados. Os três "
                   "desafios a seguir foram construídos com código real, banco de dados real, testado — não só discurso.",
                   "Helvetica", 10.5, W - 2 * MARGIN):
        c.drawString(MARGIN, y, li); y -= 14
    y -= 14

    col_w = (W - 2 * MARGIN - 24) / 2
    numbered_steps(c, [
        ("Dados e integração", "duplicata, incompleto, divergência AVA × Power BI, integração com outro sistema."),
        ("Evolução do Programa de Educação Corporativa", "trilha de onboarding: requisito → parametrização → teste → homologação → acompanhamento."),
        ("Programa de Dados", "três painéis, três números: investigação e reconciliação real."),
    ], MARGIN, y, col_w)

    ty = card(c, MARGIN + col_w + 24, y, col_w, 100, "O que sustenta a apresentação")
    bullets(c, [
        "Postgres + Docker rodando com dado mockado realista",
        "2 APIs em FastAPI (matrícula em lote, trilha de onboarding)",
        "Relatório .xlsx e certificado .pdf gerados de verdade",
        "Reconciliação de dados rodada contra o banco, não hipotética",
    ], MARGIN + col_w + 36, ty, col_w - 24, size=9, gap=12, leading=11)
    footer(c)


def slide_d1_diagnostico(c):
    frame(c)
    y = header(c, "Desafio 1", "Diagnóstico antes do tratamento — medir, não chutar.", 3)
    col_w = (W - 2 * MARGIN - 24) / 2
    ty = card(c, MARGIN, y, col_w, 150, "Sujeira encontrada (mock controlado)")
    bullets(c, [
        "Duplicata exata + variante de grafia (acento/caixa/espaço)",
        ("Nome incompleto ", "e e-mail ausente — bug real: nome passava a validação por engano"),
        "Status de matrícula grafado de formas diferentes",
        "Matrícula \"órfã\" — CPF que só existe na API, não no cadastro local",
        "Conclusão registrada antes do início (dado inconsistente)",
    ], MARGIN + 12, ty, col_w - 24, size=9, gap=13, leading=11)
    chip_row(c, ["Python", "PostgreSQL 16", "Docker", "FastAPI"], MARGIN, y - 160)

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, 150, "Arquitetura")
    steps = ["staging — sem regra, aceita qualquer dado",
             "SQL comparativo — dedupe, validação, match, pendência",
             "core — UNIQUE/CHECK/FK travando repetição",
             ".xlsx + e-mail — motivo por linha, célula destacada"]
    yy = ty2
    for s in steps:
        c.setFillColor(ACCENT_SOFT); c.roundRect(rx + 12, yy - 12, col_w - 24, 20, 4, fill=1, stroke=0)
        c.setFillColor(INK); c.setFont("Helvetica", 8.5)
        c.drawString(rx + 20, yy - 6, s)
        yy -= 28
        if s != steps[-1]:
            c.setFillColor(MUTED); c.setFont("Helvetica", 9)
            c.drawCentredString(rx + col_w / 2, yy + 12, "↓")
    footer(c)


def slide_d1_demo(c):
    frame(c)
    y = header(c, "Desafio 1 · Ao vivo", "1 planilha → cadastro validado → relatório por e-mail.", 4)
    col_w = (W - 2 * MARGIN - 24) / 2
    numbered_steps(c, [
        ("Sobe planilha", "(aluno + curso desejado) pro endpoint de matrícula em lote."),
        ("SQL comparativo roda", "dedupe, valida nome/e-mail, checa curso e matrícula ativa."),
        ("Linha que não processa", "vira .xlsx com coluna motivo e célula destacada."),
        ("Relatório chega por e-mail", "Mailpit em dev, SES em produção."),
    ], MARGIN, y, col_w, size=9.5, leading=11, gap=14)
    callout(c, MARGIN, y - 170, col_w,
            "Regra central: matrícula só é criada se aluno tem nome completo, e-mail e não está já matriculado "
            "ativo no mesmo curso.")

    rx = MARGIN + col_w + 24
    terminal(c, rx, y, col_w, 190, [
        ("# envia a planilha pra API", "cmt"),
        ("curl -X POST http://localhost:8000/lotes/matriculas \\", "cmd"),
        ("  -F \"planilha=@planilha_lote_matriculas.csv\" \\", "txt"),
        ("  -F \"email_destino=pedagogico@edepe.sp.gov.br\"", "txt"),
        ("", "txt"),
        ("# resposta: contagem + eventos do lote", "cmt"),
        ('{"total_alunos_cadastrados_no_banco": 178,', "txt"),
        ('  "total_matriculas_ativas_no_banco": 315,', "txt"),
        ('  "eventos_deste_lote": [', "txt"),
        ('    {"motivo":"ja_matriculado_no_curso","quantidade":7}]}', "txt"),
    ])
    footer(c)


def slide_d2_requisito(c):
    frame(c)
    y = header(c, "Desafio 2", "“Trilha de onboarding, 3 cursos, 60 dias, nota 70%, certificado automático.”", 5)
    c.setFont("Helvetica", 10)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, "Da frase solta do pedagógico até a regra formalizada.")
    y -= 26
    rows = [
        ["Regra", "Definição fechada"],
        ["Matrícula", "Automática nos 3 cursos, no instante do cadastro do servidor"],
        ["Aprovação", "Nota mínima 7,0 em CADA curso — não é média da trilha"],
        ["Recuperação", "Nota <7 abre 3 dias corridos pra refazer; recuperação vale sobre a nota original"],
        ["Prazo geral", "60 dias corridos a partir do cadastro pra concluir os 3"],
        ["Estourou o prazo", "Reprova automático + fila de espera da próxima turma"],
    ]
    table(c, MARGIN, y, [130, W - 2 * MARGIN - 130], rows)
    footer(c)


def slide_d2_demo(c):
    frame(c)
    y = header(c, "Desafio 2 · Ao vivo", "Cadastro → situação calculada na hora → certificado em PDF.", 6)
    col_w = (W - 2 * MARGIN - 24) / 2
    numbered_steps(c, [
        ("POST /alunos", "cadastra e já matricula nos 3 cursos obrigatórios."),
        ("GET /trilha", "situação de cada curso calculada na consulta (sem job em background)."),
        ("GET /certificado", "bloqueia com 409 se pendente; gera PDF idempotente se concluído."),
    ], MARGIN, y, col_w, size=9.5, leading=11, gap=16)
    px = pill(c, "APROVADO", MARGIN, y - 130, OK)
    px = pill(c, "EM RECUPERAÇÃO", px, y - 130, WARN)
    pill(c, "REPROVADO", px, y - 130, BAD)

    rx = MARGIN + col_w + 24
    terminal(c, rx, y, col_w, 190, [
        ("# situação da trilha, calculada na hora", "cmt"),
        ("curl http://localhost:8001/alunos/182/trilha", "cmd"),
        ("", "txt"),
        ('{"status_global":"concluido",', "txt"),
        ('  "media_notas_atual": 8.33,', "txt"),
        ('  "cursos":[{"nota":9.0,"situacao":"aprovado"}]}', "txt"),
        ("", "txt"),
        ("# emite certificado (PDF, idempotente)", "cmt"),
        ("curl http://localhost:8001/alunos/182/certificado \\", "cmd"),
        ("  -o certificado.pdf", "txt"),
    ])
    footer(c)


def slide_d2_processo(c):
    frame(c)
    y = header(c, "Desafio 2", "16 casos de teste rodados — não é só “funciona na minha máquina”.", 7)
    col_w = (W - 2 * MARGIN - 24) / 2
    ty = card(c, MARGIN, y, col_w, 150, "Amostra do plano de teste")
    rows = [
        ["Caso", "Esperado"],
        ["Nota 8,5 na 1ª tentativa", "aprovado"],
        ["Nota 5,2, refaz em 2 dias com 7,5", "aprovado (vale a recuperação)"],
        ["Nota 5,2, não refaz em 3 dias", "reprovado — nota_abaixo_da_media"],
        ["60 dias sem concluir", "reprovado — prazo_expirado + fila"],
    ]
    table(c, MARGIN + 12, ty, [140, col_w - 140 - 24], rows, size=8.5)

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, 150, "Homologação → implantação → acompanhamento")
    bullets(c, [
        "Ambiente espelho + pedagógico valida os textos de motivo/orientação",
        "Regra vale só pra novos cadastros — retroativo é decisão separada",
        "Dashboard pós-implantação: % no prazo, taxa de reprovação, fila de espera",
        "Alerta automático de prazo — próxima rotina agendada a construir",
    ], rx + 12, ty2, col_w - 24, size=9, gap=12, leading=11)
    footer(c)


def slide_d3_metodo(c):
    frame(c)
    y = header(c, "Desafio 3", "Power BI diz 1.200. Pedagógico diz 1.050. AVA diz 1.180. Qual está certo?", 8)
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, "Não é resolver o número — é mostrar o método de investigação.")
    y -= 26
    numbered_steps(c, [
        ("Perguntas", "“inscrição” significa o mesmo nos 3 lugares? Mesmo período, mesmo corte de data?"),
        ("Fontes", "AVA é a fonte primária; Power BI e pedagógico são cópias/derivações."),
        ("Indicador", "ficha formal: campo de data, o que conta, fonte oficial, dono, frequência."),
        ("Origem", "reconciliar por dimensão (por curso), não ficar em “acho que é isso”."),
        ("Prevenção", "fonte única de verdade + reconciliação automática com alerta."),
    ], MARGIN, y, W - 2 * MARGIN, size=10, leading=12, gap=14)
    footer(c)


def slide_d3_achado(c):
    frame(c)
    y = header(c, "Desafio 3 · Reconciliação real", "Power BI mostra menos que o AVA em todos os 7 cursos. Não é ruído.", 9)
    col_w = (W - 2 * MARGIN - 24) / 2

    # mini bar chart
    data = [("C01", 49, 58), ("C02", 36, 45), ("C03", 38, 45), ("C04", 53, 56),
            ("C05", 28, 39), ("C06", 40, 42), ("C07", 47, 51)]
    chart_h = 170
    ty = card(c, MARGIN, y, col_w, chart_h, "")
    max_v = max(max(p, a) for _, p, a in data)
    row_h = (chart_h - 20) / len(data)
    scale_w = col_w - 70
    for i, (curso, pbi, ava) in enumerate(data):
        ry = ty - i * row_h
        c.setFont("Courier", 8); c.setFillColor(MUTED)
        c.drawString(MARGIN + 12, ry - 8, curso)
        bx = MARGIN + 44
        bw1 = (pbi / max_v) * scale_w
        bw2 = (ava / max_v) * scale_w
        c.setFillColor(MUTED)
        c.rect(bx, ry - 6, bw1, 5, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.rect(bx, ry - 13, bw2, 5, fill=1, stroke=0)
        c.setFont("Courier", 7); c.setFillColor(INK)
        c.drawString(bx + bw1 + 3, ry - 6, str(pbi))
        c.drawString(bx + bw2 + 3, ry - 13, str(ava))
    legend_y = ty - len(data) * row_h - 6
    c.setFillColor(MUTED); c.rect(MARGIN + 12, legend_y, 8, 8, fill=1, stroke=0)
    c.setFont("Helvetica", 8); c.setFillColor(MUTED)
    c.drawString(MARGIN + 24, legend_y + 1, "Power BI")
    c.setFillColor(ACCENT); c.rect(MARGIN + 90, legend_y, 8, 8, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.drawString(MARGIN + 102, legend_y + 1, "AVA (real)")

    note_y = y - chart_h - 16
    c.setFont("Helvetica", 8.5); c.setFillColor(MUTED)
    for li in wrap("Diferença consistentemente negativa (-2 a -11) -> padrão sistemático: extração do "
                   "Power BI desatualizada, não erro pontual.", "Helvetica", 8.5, col_w):
        c.drawString(MARGIN, note_y, li)
        note_y -= 11

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, 90, "Diferenciais técnicos usados nos 3 desafios")
    chip_row(c, ["Docker", "PostgreSQL", "FastAPI", "SQL avançado", "Python", "reportlab", "openpyxl", "SMTP/Mailpit"],
             rx + 12, ty2 - 2)
    callout(c, rx, y - 90 - 14, col_w,
            "Próximos passos honestos: processamento assíncrono (Celery), testes automatizados em pytest, "
            "certificado por evento (não sob consulta), integração real com RH.")
    footer(c)


def main():
    out_path = "case_tecnico_edepe.pdf"
    c = canvas.Canvas(out_path, pagesize=landscape(A4))
    for fn in [slide_trajetoria, slide_abertura, slide_d1_diagnostico, slide_d1_demo,
               slide_d2_requisito, slide_d2_demo, slide_d2_processo,
               slide_d3_metodo, slide_d3_achado]:
        fn(c)
        c.showPage()
    c.save()
    print(f"gerado: {out_path}")


if __name__ == "__main__":
    main()
