import logging
import os
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.policy import SMTP
from urllib.parse import urlencode
from app.models import AuditLog

def send_action_mail(settings, email: str, token: str, purpose: str):
    route = "/verify-email" if purpose == "verify" else "/reset-password"
    title = "SCNU PICK 이메일 확인" if purpose == "verify" else "SCNU PICK 비밀번호 재설정"
    # Fragment does not travel to a web server as a query string; frontend submits token by POST.
    link = settings.frontend_url.rstrip("/") + route + "#" + urlencode({"token": token})
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = title, settings.mail_from, email
    content = f"{title}\n\n{link}\n\n본인이 요청하지 않았다면 이 메일을 무시해주세요.\n"
    if settings.mail_backend == "file":
        content += f"\n개발 중 Swagger 입력용 token:\n{token}\n"
    msg.set_content(content)
    if settings.mail_backend == "file":
        settings.mail_directory.mkdir(parents=True, exist_ok=True)
        path = settings.mail_directory / f"{uuid.uuid4()}.eml"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(msg.as_bytes(policy=SMTP))
        logging.getLogger("scnu_pick").info("Development mail saved locally; use the mail CLI.")
        return
    context = ssl.create_default_context()
    if settings.smtp_tls == "ssl":
        smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=context)
    else:
        smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with smtp:
        smtp.ehlo()
        if settings.smtp_tls == "starttls":
            smtp.starttls(context=context)
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)

def deliver_or_record(request, user_id: str, email: str, token: str, purpose: str):
    try:
        send_action_mail(request.app.state.settings, email, token, purpose)
    except Exception as exc:
        # No token, recipient, provider response, or password is written to logs.
        logging.getLogger("scnu_pick").error("mail_delivery_failed error_type=%s", type(exc).__name__)
        with request.app.state.sessions() as db:
            db.add(AuditLog(actor_id=user_id, action="mail_delivery_failed",
                           details={"purpose": purpose, "error_type": type(exc).__name__}))
            db.commit()
