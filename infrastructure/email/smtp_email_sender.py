import os
import smtplib
import ssl
from email.message import EmailMessage

from application.ports.email_sender import EmailDeliveryUnavailable


class SmtpEmailSender:
    def send_verification(self, email: str, token: str) -> None:
        self._send(email, "Confirme seu e-mail no RoomFlow", token, "cadastro")

    def send_password_reset(self, email: str, token: str) -> None:
        self._send(email, "Redefina sua senha no RoomFlow", token, "recuperação")

    @staticmethod
    def _send(email: str, subject: str, token: str, flow: str) -> None:
        host = os.getenv("ROOMFLOW_SMTP_HOST")
        sender = os.getenv("ROOMFLOW_SMTP_FROM")
        if not host or not sender:
            raise EmailDeliveryUnavailable("Configure o envio de e-mail para o cadastro de membros.")

        message = EmailMessage()
        message["From"] = sender
        message["To"] = email
        message["Subject"] = subject
        message.set_content(
            f"Cole o código abaixo na tela de {flow} do RoomFlow. Ele é válido por 20 minutos.\n\n" + token
        )
        try:
            port = int(os.getenv("ROOMFLOW_SMTP_PORT", "465"))
            with smtplib.SMTP_SSL(host, port, timeout=10, context=ssl.create_default_context()) as client:
                if username := os.getenv("ROOMFLOW_SMTP_USERNAME"):
                    client.login(username, os.environ["ROOMFLOW_SMTP_PASSWORD"])
                client.send_message(message)
        except (OSError, ValueError, KeyError) as exc:
            raise EmailDeliveryUnavailable("O e-mail de confirmação não pôde ser enviado.") from exc
