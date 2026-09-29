"""Gera o PDF do certificado de conclusão da trilha."""
import hashlib
import io

# workaround: nesta build do Python/OpenSSL, hashlib.md5 não aceita o
# kwarg "usedforsecurity" que o reportlab usa internamente (PDFDocument).
# Sem isso, Canvas() quebra com TypeError na hora de gerar o PDF.
_md5_original = hashlib.md5
hashlib.md5 = lambda *a, **kw: _md5_original(*a)

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def gerar_certificado_pdf(aluno_nome, aluno_cpf, trilha_nome, cursos,
                           carga_horaria_total, data_conclusao, protocolo):
    """
    cursos: lista de dicts {curso_nome, nota, carga_horaria}
    """
    buffer = io.BytesIO()
    largura, altura = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    c.setStrokeColor(colors.HexColor("#4472C4"))
    c.setLineWidth(3)
    c.rect(1 * cm, 1 * cm, largura - 2 * cm, altura - 2 * cm)

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#4472C4"))
    c.drawCentredString(largura / 2, altura - 2.5 * cm,
                         "ESCOLA DA DEFENSORIA PÚBLICA DO ESTADO DE SÃO PAULO — EDEPE")

    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.black)
    c.drawCentredString(largura / 2, altura - 4.5 * cm, "CERTIFICADO DE CONCLUSÃO")

    c.setFont("Helvetica", 13)
    c.drawCentredString(largura / 2, altura - 6.2 * cm, "Certificamos que")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(largura / 2, altura - 7.3 * cm, aluno_nome)

    c.setFont("Helvetica", 11)
    c.drawCentredString(largura / 2, altura - 7.9 * cm, f"CPF {aluno_cpf}")

    c.setFont("Helvetica", 13)
    c.drawCentredString(
        largura / 2, altura - 9.2 * cm,
        f"concluiu a trilha \"{trilha_nome}\", com carga horária total de "
        f"{carga_horaria_total}h, em {data_conclusao.strftime('%d/%m/%Y')}."
    )

    y = altura - 11 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(3 * cm, y, "Curso")
    c.drawString(largura - 8 * cm, y, "Carga horária")
    c.drawString(largura - 4.5 * cm, y, "Nota final")
    c.line(3 * cm, y - 0.2 * cm, largura - 3 * cm, y - 0.2 * cm)

    c.setFont("Helvetica", 11)
    for curso in cursos:
        y -= 0.8 * cm
        c.drawString(3 * cm, y, curso["curso_nome"])
        c.drawString(largura - 8 * cm, y, f"{curso['carga_horaria']}h")
        c.drawString(largura - 4.5 * cm, y, f"{curso['nota']:.1f}")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawCentredString(largura / 2, 1.8 * cm, f"Protocolo de verificação: {protocolo}")

    c.showPage()
    c.save()
    return buffer.getvalue()
