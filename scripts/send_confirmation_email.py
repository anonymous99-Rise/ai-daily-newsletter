#!/usr/bin/env python3
"""Send subscription confirmation email via QQ SMTP.

Triggered by repository_dispatch (confirm-subscription) from Vercel.
Reads CONFIRM_EMAIL / CONFIRM_TOKEN / CONFIRM_ORIGIN from environment.
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.utils import formataddr


def build_html_email(confirm_url: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head>\n"
        "<body style='margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'>\n"
        "<div style='max-width:600px;margin:0 auto;padding:20px 16px;'>\n"
        "<div style='background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:16px 16px 0 0;padding:32px 24px;text-align:center;'>\n"
        "<div style='font-size:36px;margin-bottom:8px;'>&#129302;</div>\n"
        "<h1 style='color:#fff;font-size:22px;font-weight:800;margin:0 0 4px;'>AI Daily Newsletter</h1>\n"
        "<p style='color:#c7d2fe;font-size:13px;margin:0;'>Everyday AI and Agent Front Intelligence Feed</p>\n"
        "</div>\n"
        "<div style='background:#fff;border-radius:0 0 16px 16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);'>\n"
        "<div style='padding:32px 24px;text-align:center;'>\n"
        "<h2 style='color:#1e293b;font-size:18px;font-weight:700;margin:0 0 12px;'>Confirm your subscription</h2>\n"
        "<p style='color:#64748b;font-size:14px;margin:0 0 24px;'>Click the button below to confirm your subscription.<br>This link expires in 24 hours.</p>\n"
        f"<a href='{confirm_url}' style='display:inline-block;background:#4f46e5;color:#fff;padding:12px 32px;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;'>Confirm Subscription</a>\n"
        "</div>\n"
        "<div style='padding:16px 24px;text-align:center;border-top:1px solid #f1f5f9;'>\n"
        "<p style='font-size:12px;color:#94a3b8;margin:0;'>If you did not request this subscription, you can safely ignore this email.</p>\n"
        "</div></div></div></body></html>"
    )


def main() -> None:
    token = os.environ.get("QQ_EMAIL_TOKEN", "").strip()
    from_addr = os.environ.get("QQ_EMAIL_ADDR", "").strip()
    to_email = os.environ.get("CONFIRM_EMAIL", "").strip()
    confirm_token = os.environ.get("CONFIRM_TOKEN", "").strip()
    origin = os.environ.get("CONFIRM_ORIGIN", "").rstrip("/")

    if not (token and from_addr and to_email and confirm_token and origin):
        print("Missing environment variables, skipping confirmation email.", file=sys.stderr)
        sys.exit(1)

    confirm_url = f"{origin}/api/confirm?token={confirm_token}"
    msg = MIMEText(build_html_email(confirm_url), "html", "utf-8")
    msg["Subject"] = "Confirm your AI Daily Newsletter subscription"
    msg["From"] = formataddr(("AI Daily Newsletter", from_addr))
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
            server.login(from_addr, token)
            server.sendmail(from_addr, [to_email], msg.as_string())
        print(f"Confirmation email sent to {to_email}")
    except Exception as e:
        print(f"QQ SMTP error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
