import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email(to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(message)


def send_test_email(to_email: str) -> None:
    send_email(
        to_email=to_email,
        subject="SafariDesk email test",
        body="If you can see this in Mailtrap, SafariDesk email is working.",
    )

