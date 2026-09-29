"""
Envio de e-mail com anexo via SMTP. Em dev aponta pro Mailpit
(localhost:1025, sem autenticação). Trocar por SES é só mudar
SMTP_HOST/PORT/USER/PASSWORD via variável de ambiente — o código não muda.
"""
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def enviar_relatorio(destinatario: str, assunto: str, corpo: str,
                      anexo_bytes: bytes, anexo_nome: str):
    msg = MIMEMultipart()
    msg["Subject"] = assunto
    msg["From"] = os.environ.get("SMTP_FROM", "edepe-plataforma@edepe.sp.gov.br")
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo, "plain"))

    parte_anexo = MIMEApplication(
        anexo_bytes,
        _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    parte_anexo.add_header("Content-Disposition", "attachment", filename=anexo_nome)
    msg.attach(parte_anexo)

    host = os.environ.get("SMTP_HOST", "localhost")
    port = int(os.environ.get("SMTP_PORT", "1025"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, port) as s:
        if user and password:
            s.starttls()
            s.login(user, password)
        s.send_message(msg)
