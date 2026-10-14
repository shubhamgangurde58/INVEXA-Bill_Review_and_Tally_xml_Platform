"""
Tiny email wrapper. Reads SMTP settings from Config. When SMTP is
not configured (which is the normal state during development), it
prints the email to the server console with a [DEV MAIL] prefix
so the CA or client can still click the link.

Nothing here ever raises. A failed email must never break signup
or password reset — the account is still created either way.
"""

import smtplib
from email.mime.text import MIMEText


# Return True if the config has enough SMTP settings to actually
# send. Any missing value means we fall back to console mode.
def _smtp_configured():
    try:
        from config import Config
    except Exception:
        return False
    return all([
        getattr(Config, "SMTP_HOST", ""),
        getattr(Config, "SMTP_USER", ""),
        getattr(Config, "SMTP_PASS", ""),
    ])


# Real send path. Uses STARTTLS on port 587 by default.
def _send_via_smtp(to, subject, body):
    from config import Config

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM or Config.SMTP_USER
    msg["To"] = to

    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASS)
        server.sendmail(msg["From"], [to], msg.as_string())


# The only function the rest of the app calls.
# Wrapped in try/except so a broken SMTP server cannot take the
# whole signup flow down with it.
def send_mail(to, subject, body):
    if not to:
        return False

    if _smtp_configured():
        try:
            _send_via_smtp(to, subject, body)
            print(f"[MAIL] sent to {to}")
            return True
        except Exception as exc:
            print(f"[MAIL] SMTP failed ({exc}); falling back to console")

    # Development fallback. Same shape as utils.auth_tokens.print_dev_link.
    print("")
    print("[DEV MAIL] ----------------------------------------")
    print(f"[DEV MAIL] To:      {to}")
    print(f"[DEV MAIL] Subject: {subject}")
    print(f"[DEV MAIL] Body:    {body}")
    print("[DEV MAIL] ----------------------------------------")
    print("")
    return True