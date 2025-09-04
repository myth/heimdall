"""Heimdall utils"""

from datetime import date, datetime
from email.message import EmailMessage
from enum import Enum
from logging import getLogger
from typing import Any

from aiosmtplib import SMTP

from heimdall.cfg import EMAIL_ADDRESS, EMAIL_RECIPIENT, EMAIL_SMTP_PORT, EMAIL_SMTP_SERVER, TZ

logger = getLogger(__name__)


def default_encoder(o: Any):
    if isinstance(o, datetime):
        return o.astimezone(TZ).isoformat()
    elif isinstance(o, date):
        return o.isoformat()
    elif isinstance(o, Enum):
        return o.value
    else:
        raise TypeError(f"Unserializable type: {type(o)}")


async def send_email(body, recipient: str = EMAIL_RECIPIENT, subject: str = "Ulv network service state change"):
    """
    Asynchronously send an email.

    :param body: The email body (string including newlines)
    :param recipient: Email formatted recipient (Name <mail>)
    :param subject: The subject of the email.
    """

    logger.info("Sending email to %s with subject '%s'", recipient, subject)

    try:
        async with SMTP(hostname=EMAIL_SMTP_SERVER, port=EMAIL_SMTP_PORT, use_tls=False) as smtp:
            mail = EmailMessage()
            mail["From"] = EMAIL_ADDRESS
            mail["To"] = EMAIL_RECIPIENT
            mail["Subject"] = subject
            mail.set_content(body)

            await smtp.send_message(mail)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
