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

# badges (pill) ficam com cor fixa, sempre escuras o bastante pra texto branco,
# independente do tema — não são "texto sobre a página", são selo sólido.
OK = colors.HexColor("#2F7D4F")
WARN = colors.HexColor("#A9720A")
BAD = colors.HexColor("#B5432E")

PALETTES = {
    "light": dict(
        BG="#FFFFFF", INK="#16211E", MUTED="#5B6B66", ACCENT="#1F5C55",
        ACCENT_SOFT="#DCE8E5", LINE="#D8DAD3", ON_ACCENT="#FFFFFF",
        SURFACE2="#F4F6F2", CHIP_BG="#FFFFFF",
        TERM_BG="#121A1C", TERM_FG="#E7EDE9", TERM_ACCENT="#7FD9C9",
    ),
    "dark": dict(
        BG="#10171A", INK="#E8EEEB", MUTED="#93A29C", ACCENT="#6CC4B5",
        ACCENT_SOFT="#1E3A37", LINE="#2A3336", ON_ACCENT="#0F1618",
        SURFACE2="#1C2628", CHIP_BG="#1C2628",
        TERM_BG="#0A1012", TERM_FG="#E7EDE9", TERM_ACCENT="#7FD9C9",
    ),
}


def set_theme(name):
    """Troca a paleta global de cores antes de gerar as páginas."""
    global BG, INK, MUTED, ACCENT, ACCENT_SOFT, LINE, ON_ACCENT
    global SURFACE2, CHIP_BG, TERM_BG, TERM_FG, TERM_ACCENT
    p = PALETTES[name]
    BG = colors.HexColor(p["BG"]); INK = colors.HexColor(p["INK"])
    MUTED = colors.HexColor(p["MUTED"]); ACCENT = colors.HexColor(p["ACCENT"])
    ACCENT_SOFT = colors.HexColor(p["ACCENT_SOFT"]); LINE = colors.HexColor(p["LINE"])
    ON_ACCENT = colors.HexColor(p["ON_ACCENT"])
    SURFACE2 = colors.HexColor(p["SURFACE2"]); CHIP_BG = colors.HexColor(p["CHIP_BG"])
    TERM_BG = colors.HexColor(p["TERM_BG"]); TERM_FG = colors.HexColor(p["TERM_FG"])
    TERM_ACCENT = colors.HexColor(p["TERM_ACCENT"])


set_theme("light")

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
    c.setFillColor(BG)
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
    badge_w = 14 + size
    badge_font = 7 + size * 0.28
    for i, (label, rest) in enumerate(items, start=1):
        c.setFillColor(ACCENT_SOFT)
        c.roundRect(x, y - badge_w * 0.68, badge_w, badge_w * 0.9, 3, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", badge_font)
        c.drawCentredString(x + badge_w / 2, y - badge_w * 0.42, str(i))
        tx = x + badge_w + 6
        c.setFont("Helvetica-Bold", size)
        c.setFillColor(INK)
        c.drawString(tx, y, label)
        c.setFont("Helvetica", size)
        c.setFillColor(MUTED)
        lines = wrap(rest, "Helvetica", size, width - (badge_w + 6))
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
        c.setFillColor(CHIP_BG)
        c.setStrokeColor(LINE)
        c.roundRect(cx, y - 10, w, 15, 3, fill=1, stroke=1)
        c.setFillColor(MUTED)
        c.drawString(cx + 6, y - 6, chip)
        cx += w + 6
    return y - 20


def table(c, x, y, col_widths, rows, header_row=True, size=9, row_h=20):
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
    ty = y - 36
    for line, kind in lines:
        c.setFont("Courier", 9.5)
        c.setFillColor(TERM_ACCENT if kind == "cmd" else (MUTED if kind == "cmt" else TERM_FG))
        for li in textwrap.wrap(line, width=int((w - 24) / 5.7)) or [""]:
            c.drawString(x + 12, ty, li)
            ty -= 15
    return ty


def callout(c, x, y, w, text, title="Nota", size=11.5, leading=16):
    lines = wrap(text, "Helvetica", size, w - 28)
    h = 28 + len(lines) * leading
    c.setFillColor(ACCENT_SOFT)
    c.rect(x, y - h, w, h, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(x, y - h, 4, h, fill=1, stroke=0)
    ty = y - 20
    c.setFont("Helvetica", size)
    c.setFillColor(INK)
    for li in lines:
        c.drawString(x + 16, ty, li)
        ty -= leading
    return ty


# ---------------------------------------------------------------- slides --

def slide_trajetoria(c):
    frame(c)
    y = header(c, "Antes do case", "Icaro Albar — Coordenador de Inovação e Inteligência Artificial", 1)

    y -= 14
    col_w = (W - 2 * MARGIN - 24) / 2
    left_x = MARGIN
    right_x = MARGIN + col_w + 24

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(MUTED)
    c.drawString(left_x, y, "TRAJETÓRIA")
    ty = y - 24
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
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(ACCENT)
        for li in wrap(quando, "Helvetica-Bold", 12, col_w):
            c.drawString(left_x, ty, li)
            ty -= 16
        c.setFont("Helvetica", 11.5)
        c.setFillColor(MUTED)
        for li in wrap(desc, "Helvetica", 11.5, col_w):
            c.drawString(left_x, ty, li)
            ty -= 16
        ty -= 32

    ty2 = card(c, right_x, y + 16, col_w, 110, "Formação")
    c.setFont("Helvetica", 11)
    c.setFillColor(INK)
    for li in wrap("MBA USP/Esalq — Engenharia de Software (em andamento)", "Helvetica", 11, col_w - 24):
        c.drawString(right_x + 12, ty2, li); ty2 -= 16
    ty2 -= 12
    for li in wrap("Bacharelado — Análise de Sistemas, Unigranrio (2019–2023)", "Helvetica", 11, col_w - 24):
        c.drawString(right_x + 12, ty2, li); ty2 -= 16

    stack_top = y + 16 - 110 - 24
    ty3 = card(c, right_x, stack_top, col_w, 110, "Stack")
    chip_row(c, ["Python", "Node.js/TS", "React", "AWS", "Docker", "API REST", "SQL", "Terraform"],
             right_x + 12, ty3 - 2, size=10)

    call_top = stack_top - 110 - 24
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
    ], MARGIN, y, col_w, size=13.5, leading=17, gap=58)

    ty = card(c, MARGIN + col_w + 24, y, col_w, 340, "O que sustenta a apresentação")
    bullets(c, [
        "Postgres + Docker rodando com dado mockado realista",
        "2 APIs em FastAPI (matrícula em lote, trilha de onboarding)",
        "Relatório .xlsx e certificado .pdf gerados de verdade",
        "Reconciliação de dados rodada contra o banco, não hipotética",
    ], MARGIN + col_w + 36, ty - 4, col_w - 24, size=12, gap=36, leading=15)
    footer(c)


def slide_d1_diagnostico(c):
    frame(c)
    y = header(c, "Desafio 1", "Diagnóstico antes do tratamento — medir, não chutar.", 3)
    col_w = (W - 2 * MARGIN - 24) / 2
    card_h = 300
    ty = card(c, MARGIN, y, col_w, card_h, "Problemas encontrados nos dados de teste")
    bullets(c, [
        "Mesma pessoa cadastrada duas vezes, com o nome escrito de formas diferentes",
        ("Cadastro incompleto ", "— faltando nome completo ou e-mail, algo que passava despercebido"),
        "Situação da matrícula escrita de jeitos diferentes (ex: \"Concluído\" e \"concluido\")",
        "Matrícula de gente que nunca foi cadastrada — sinal de que falta integrar com outro sistema",
        "Data de conclusão do curso anterior à data em que ele começou",
    ], MARGIN + 12, ty - 6, col_w - 24, size=10.5, gap=24, leading=13)
    chip_row(c, ["Python", "PostgreSQL 16", "Docker", "FastAPI"], MARGIN, y - card_h - 20)

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, card_h, "Como o dado é tratado")
    steps = ["1. O dado bruto chega e é aceito do jeito que vier",
             "2. O sistema confere, limpa duplicidade e valida cada campo",
             "3. Só entra no cadastro oficial o que está correto",
             "4. Quem não passou recebe um relatório explicando o motivo"]
    yy = ty2 - 6
    for s in steps:
        c.setFillColor(ACCENT_SOFT); c.roundRect(rx + 12, yy - 15, col_w - 24, 26, 5, fill=1, stroke=0)
        c.setFillColor(INK); c.setFont("Helvetica", 10)
        c.drawString(rx + 20, yy - 7, s)
        yy -= 40
        if s != steps[-1]:
            c.setFillColor(MUTED); c.setFont("Helvetica", 11)
            c.drawCentredString(rx + col_w / 2, yy + 14, "↓")
    footer(c)


def slide_d1_demo(c):
    frame(c)
    y = header(c, "Desafio 1 · Ao vivo", "1 planilha → cadastro validado → relatório por e-mail.", 4)
    col_w = (W - 2 * MARGIN - 24) / 2
    y2 = numbered_steps(c, [
        ("Envio da planilha", "uma linha por pessoa, com o curso que ela quer fazer."),
        ("Conferência automática", "confirma nome, e-mail, curso e se já não está matriculada."),
        ("Quem não passa", "recebe um relatório em Excel explicando o motivo, célula marcada em vermelho."),
        ("Relatório chega por e-mail", "automaticamente, sem precisar pedir."),
    ], MARGIN, y, col_w, size=12, leading=15, gap=38)
    callout(c, MARGIN, y2 - 16, col_w,
            "Regra central: só entra no cadastro quem tem nome completo, e-mail, e ainda não está matriculado "
            "naquele curso. Se qualquer uma dessas condições falhar, a linha vai pro relatório de pendências "
            "em vez de travar o restante do lote.", size=12.5, leading=17)

    rx = MARGIN + col_w + 24
    terminal(c, rx, y, col_w, 300, [
        ("# envia a planilha com os novos cadastros", "cmt"),
        ("$ enviar planilha_lote_matriculas.csv", "cmd"),
        ("", "txt"),
        ("resultado:", "cmt"),
        ("✓ 178 pessoas cadastradas com sucesso", "txt"),
        ("✓ 315 matrículas confirmadas no total", "txt"),
        ("! 7 já estavam matriculadas nesse curso", "txt"),
        ("! 5 informaram um curso que não existe", "txt"),
        ("", "txt"),
        ("→ relatório enviado por e-mail", "cmt"),
        ("", "txt"),
        ("(ver a planilha real no e-mail, com a", "cmt"),
        (" célula do erro destacada em vermelho)", "cmt"),
    ])
    footer(c)


def slide_d2_requisito(c):
    frame(c)
    y = header(c, "Desafio 2", "“Trilha de onboarding, 3 cursos, 60 dias, nota 70%, certificado automático.”", 5)
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, "Da frase solta do pedagógico até a regra formalizada.")
    y -= 40
    rows = [
        ["Regra", "Definição fechada"],
        ["Matrícula", "Automática nos 3 cursos, no instante do cadastro do servidor"],
        ["Aprovação", "Nota mínima 7,0 em CADA curso — não é média da trilha"],
        ["Recuperação", "Nota <7 abre 3 dias corridos pra refazer; recuperação vale sobre a nota original"],
        ["Prazo geral", "60 dias corridos a partir do cadastro pra concluir os 3"],
        ["Estourou o prazo", "Reprova automático + fila de espera da próxima turma"],
    ]
    y2 = table(c, MARGIN, y, [150, W - 2 * MARGIN - 150], rows, size=11.5, row_h=38)
    callout(c, MARGIN, y2 - 18, W - 2 * MARGIN,
            "As 3 perguntas que ficaram em aberto no pedido original — quando o prazo conta, se pode refazer "
            "prova e o que acontece ao estourar o prazo — foram fechadas nesta tabela antes de configurar "
            "qualquer coisa na plataforma.", size=13, leading=18)
    footer(c)


def slide_d2_demo(c):
    frame(c)
    y = header(c, "Desafio 2 · Ao vivo", "Cadastro → situação calculada na hora → certificado em PDF.", 6)
    col_w = (W - 2 * MARGIN - 24) / 2
    y2 = numbered_steps(c, [
        ("Cadastra o servidor", "e ele já é matriculado automaticamente nos 3 cursos obrigatórios."),
        ("Consulta o progresso", "a situação de cada curso é calculada na hora, sempre atualizada."),
        ("Pede o certificado", "só é gerado se os 3 cursos estiverem aprovados — senão avisa o que falta."),
    ], MARGIN, y, col_w, size=12, leading=15, gap=40)
    px = pill(c, "APROVADO", MARGIN, y2 - 4, OK)
    px = pill(c, "EM RECUPERAÇÃO", px, y2 - 4, WARN)
    pill(c, "REPROVADO", px, y2 - 4, BAD)
    callout(c, MARGIN, y2 - 28, col_w,
            "Cada situação é recalculada a cada consulta, a partir da nota e do prazo — não existe um status "
            "salvo esperando um job passar pra atualizar. O certificado só sai depois que os 3 estão aprovados.",
            size=12.5, leading=17)

    rx = MARGIN + col_w + 24
    terminal(c, rx, y, col_w, 300, [
        ("# consulta o progresso do servidor", "cmt"),
        ("$ ver situação do aluno 182", "cmd"),
        ("", "txt"),
        ("resultado: aprovado nos 3 cursos", "txt"),
        ("média final: 8,3", "txt"),
        ("", "txt"),
        ("# pede o certificado", "cmt"),
        ("$ emitir certificado do aluno 182", "cmd"),
        ("", "txt"),
        ("→ certificado.pdf gerado", "txt"),
        ("", "txt"),
        ("(se algum curso ainda estiver pendente,", "cmt"),
        (" avisa o que falta em vez de gerar)", "cmt"),
    ])
    footer(c)


def slide_d2_processo(c):
    frame(c)
    y = header(c, "Desafio 2", "16 casos de teste rodados — não é só “funciona na minha máquina”.", 7)
    col_w = (W - 2 * MARGIN - 24) / 2
    card_h = 420
    ty = card(c, MARGIN, y, col_w, card_h, "Amostra do plano de teste")
    rows = [
        ["Caso", "Esperado"],
        ["Nota 8,5 na 1ª tentativa", "aprovado"],
        ["Nota 5,2, refaz em 2 dias com 7,5", "aprovado (vale a recuperação)"],
        ["Nota 5,2, não refaz em 3 dias", "reprovado — nota abaixo do mínimo"],
        ["60 dias sem concluir", "reprovado — perdeu o prazo, entra na fila de espera"],
    ]
    table(c, MARGIN + 12, ty - 6, [155, col_w - 155 - 24], rows, size=11, row_h=48)

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, card_h, "Homologação → implantação → acompanhamento")
    bullets(c, [
        "Ambiente espelho + pedagógico valida os textos de motivo/orientação",
        "Regra vale só pra novos cadastros — retroativo é decisão separada",
        "Dashboard pós-implantação: % no prazo, taxa de reprovação, fila de espera",
        "Alerta automático de prazo — próxima rotina agendada a construir",
    ], rx + 12, ty2 - 8, col_w - 24, size=12, gap=42, leading=16)
    footer(c)


def slide_d3_metodo(c):
    frame(c)
    y = header(c, "Desafio 3", "Power BI diz 1.200. Pedagógico diz 1.050. AVA diz 1.180. Qual está certo?", 8)
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, "Não é resolver o número — é mostrar o método de investigação.")
    y -= 34
    numbered_steps(c, [
        ("Perguntas", "“inscrição” significa o mesmo nos 3 lugares? Mesmo período, mesmo corte de data?"),
        ("Fontes", "AVA é a fonte primária; Power BI e pedagógico são cópias/derivações."),
        ("Indicador", "ficha formal: campo de data, o que conta, fonte oficial, dono, frequência."),
        ("Origem", "reconciliar por dimensão (por curso), não ficar em “acho que é isso”."),
        ("Prevenção", "fonte única de verdade + reconciliação automática com alerta."),
    ], MARGIN, y, W - 2 * MARGIN, size=14.5, leading=19, gap=68)
    footer(c)


def slide_d3_achado(c):
    frame(c)
    y = header(c, "Desafio 3 · Reconciliação real", "Power BI mostra menos que o AVA em todos os 7 cursos. Não é ruído.", 9)
    col_w = (W - 2 * MARGIN - 24) / 2

    # mini bar chart
    data = [("C01", 49, 58), ("C02", 36, 45), ("C03", 38, 45), ("C04", 53, 56),
            ("C05", 28, 39), ("C06", 40, 42), ("C07", 47, 51)]
    chart_h = 300
    ty = card(c, MARGIN, y, col_w, chart_h, "")
    max_v = max(max(p, a) for _, p, a in data)
    row_h = (chart_h - 30) / len(data)
    scale_w = col_w - 78
    for i, (curso, pbi, ava) in enumerate(data):
        ry = ty - 6 - i * row_h
        c.setFont("Courier", 9.5); c.setFillColor(MUTED)
        c.drawString(MARGIN + 12, ry - 10, curso)
        bx = MARGIN + 48
        bw1 = (pbi / max_v) * scale_w
        bw2 = (ava / max_v) * scale_w
        c.setFillColor(MUTED)
        c.rect(bx, ry - 8, bw1, 7, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.rect(bx, ry - 18, bw2, 7, fill=1, stroke=0)
        c.setFont("Courier", 8.5); c.setFillColor(INK)
        c.drawString(bx + bw1 + 4, ry - 7, str(pbi))
        c.drawString(bx + bw2 + 4, ry - 17, str(ava))
    legend_y = ty - len(data) * row_h - 10
    c.setFillColor(MUTED); c.rect(MARGIN + 12, legend_y, 9, 9, fill=1, stroke=0)
    c.setFont("Helvetica", 9); c.setFillColor(MUTED)
    c.drawString(MARGIN + 25, legend_y + 1, "Power BI")
    c.setFillColor(ACCENT); c.rect(MARGIN + 95, legend_y, 9, 9, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.drawString(MARGIN + 108, legend_y + 1, "AVA (real)")

    note_y = y - chart_h - 20
    c.setFont("Helvetica", 9.5); c.setFillColor(MUTED)
    for li in wrap("Diferença consistentemente negativa (-2 a -11) -> padrão sistemático: extração do "
                   "Power BI desatualizada, não erro pontual.", "Helvetica", 9.5, col_w):
        c.drawString(MARGIN, note_y, li)
        note_y -= 13

    rx = MARGIN + col_w + 24
    ty2 = card(c, rx, y, col_w, 140, "Diferenciais técnicos usados nos 3 desafios")
    chip_row(c, ["Docker", "PostgreSQL", "FastAPI", "SQL avançado", "Python", "reportlab", "openpyxl", "SMTP/Mailpit"],
             rx + 12, ty2 - 4, size=9)
    callout(c, rx, y - 140 - 20, col_w,
            "Próximos passos honestos: processamento assíncrono (Celery), testes automatizados em pytest, "
            "certificado por evento (não sob consulta), integração real com RH.")
    footer(c)


SLIDES = [slide_trajetoria, slide_abertura, slide_d1_diagnostico, slide_d1_demo,
          slide_d2_requisito, slide_d2_demo, slide_d2_processo,
          slide_d3_metodo, slide_d3_achado]


def build(theme, out_path):
    set_theme(theme)
    c = canvas.Canvas(out_path, pagesize=landscape(A4))
    for fn in SLIDES:
        fn(c)
        c.showPage()
    c.save()
    print(f"gerado: {out_path}")


def main():
    build("light", "case_tecnico_edepe.pdf")
    build("dark", "case_tecnico_edepe_dark.pdf")


if __name__ == "__main__":
    main()
