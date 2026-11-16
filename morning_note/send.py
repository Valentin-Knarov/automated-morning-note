"""Envoi de la note par e-mail (SMTP). Identifiants lus dans les variables d'environnement, jamais dans le code.

Variables attendues :
    SMTP_HOST, SMTP_PORT (587 par défaut), SMTP_USER, SMTP_PASSWORD, MAIL_TO (adresses séparées par des virgules)
Pour Gmail : SMTP_HOST=smtp.gmail.com et un « mot de passe d'application » (pas le mot de passe du compte).
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

REQUIRED = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO")


def send_email(subject: str, html: str, text: str) -> list[str]:
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"Variables d'environnement manquantes pour l'envoi : {', '.join(missing)}")
    recipients = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = ", ".join(recipients)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)
    return recipients
