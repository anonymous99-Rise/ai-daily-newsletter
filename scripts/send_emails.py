#!/usr/bin/env python3
"""Send daily newsletter emails via Resend or QQ SMTP.

Supports two providers (tried in order):
  1. Resend API (RESEND_API_KEY)
  2. QQ SMTP (QQ_EMAIL_TOKEN + QQ_EMAIL_ADDR)
"""

import json
import os
import smtplib
import sys
import urllib.request
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Optional

SUBSCRIBERS_FILE = Path(__file__).parent.parent / "data" / "subscribers.json"
LATEST_FILE = Path(__file__).parent.parent / "data" / "latest.json"


def load_subscribers() -> list[str]:
    if not SUBSCRIBERS_FILE.exists():
        print("No subscribers file found, skipping email send.")
        return []
    with open(SUBSCRIBERS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.keys())


def load_latest_news() -> list[dict]:
    if not LATEST_FILE.exists():
        return []
    with open(LATEST_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_html_email(articles: list[dict], subscriber_email: str) -> str:
    today = (articles[0].get("date") or "") if articles else ""
    rows = ""
    for article in articles[:15]:
        title = article.get("title") or "无标题"
        source = article.get("source") or ""
        url = article.get("url") or "#"
        summary = (article.get("summary") or "")[:200]
        category = article.get("category") or "AI"
        rows += f"""<tr>
  <td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;">
    <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:4px;">
      <a href="{url}" style="color:#4f46e5;text-decoration:none;">{title}</a>
    </div>
    <div style="font-size:12px;color:#64748b;margin-bottom:4px;">{summary}...</div>
    <div style="font-size:11px;color:#94a3b8;">
      <span style="background:#f1f5f9;padding:2px 8px;border-radius:9999px;">{category}</span>
      <span style="margin-left:8px;">{source}</span>
    </div>
  </td>
</tr>"""

    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head>\n"
        "<body style='margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'>\n"
        "<div style='max-width:600px;margin:0 auto;padding:20px 16px;'>\n"
        "<div style='background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:16px 16px 0 0;padding:32px 24px;text-align:center;'>\n"
        "<div style='font-size:36px;margin-bottom:8px;'>ROBOT</div>\n"
        "<h1 style='color:#fff;font-size:22px;font-weight:800;margin:0 0 4px;'>AI Daily Newsletter</h1>\n"
        "<p style='color:#c7d2fe;font-size:13px;margin:0;'>Everyday AI and Agent Front Intelligence Feed</p>\n"
        "</div>\n"
        "<div style='background:#fff;border-radius:0 0 16px 16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);'>\n"
        "<div style='padding:20px 24px 8px;border-bottom:1px solid #f1f5f9;'>\n"
        f"<p style='margin:0;font-size:13px;color:#64748b;'>Today collected <strong style='color:#4f46e5'>{len(articles)}</strong> curated articles, below are Top 15:</p>\n"
        "</div>\n"
        f"<table style='width:100%;border-collapse:collapse;'>{rows}</table>\n"
        "<div style='padding:20px 24px;text-align:center;border-top:1px solid #f1f5f9;'>\n"
        "<a href='https://ai-daily-newsletter.vercel.app' style='display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:10px 24px;border-radius:8px;font-size:13px;font-weight:600;'>Read full content on Web UI</a>\n"
        "</div></div>\n"
        "<div style='text-align:center;padding:16px 0 8px;'>\n"
        "<p style='font-size:12px;color:#94a3b8;margin:0 0 8px;'>You received this email because you subscribed to AI Daily Newsletter</p>\n"
        f"<a href='https://ai-daily-newsletter.vercel.app/api/unsubscribe?email={subscriber_email}' style='font-size:12px;color:#94a3b8;'>Unsubscribe</a>\n"
        "</div></div></body></html>"
    )


def send_via_resend(api_key: str, to_email: str, subject: str, html_body: str) -> bool:
    """Send email via Resend API."""
    data = json.dumps({
        "from": "AI Daily Newsletter <newsletter@ai-daily-newsletter.com>",
        "to": to_email,
        "subject": subject,
        "html": html_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"    Resend error: {e}", file=sys.stderr)
        return False


def send_via_qq_smtp(
    token: str,
    from_addr: str,
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """Send email via QQ SMTP using authorization code."""
    try:
        msg = MIMEText(html_body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr(("AI Daily Newsletter", from_addr))
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
            server.login(from_addr, token)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"    QQ SMTP error: {e}", file=sys.stderr)
        return False


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Try Resend first, fall back to QQ SMTP."""
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    qq_token = os.environ.get("QQ_EMAIL_TOKEN", "").strip()
    qq_addr = os.environ.get("QQ_EMAIL_ADDR", "").strip()

    if resend_key:
        if send_via_resend(resend_key, to_email, subject, html_body):
            return True
        print(f"    Resend failed, trying QQ SMTP...")

    if qq_token and qq_addr:
        return send_via_qq_smtp(qq_token, qq_addr, to_email, subject, html_body)

    print(f"    No email provider configured")
    return False


def main() -> None:
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    qq_token = os.environ.get("QQ_EMAIL_TOKEN", "").strip()
    if not resend_key and not qq_token:
        print("RESEND_API_KEY and QQ_EMAIL_TOKEN not set, skipping email send.")
        sys.exit(0)

    subscribers = load_subscribers()
    if not subscribers:
        print("No subscribers, skipping email send.")
        return

    articles = load_latest_news()
    if not articles:
        print("No latest news found, skipping email send.")
        return

    today = articles[0].get("date") if articles else ""
    subject = f"AI Daily Newsletter {today} - {len(articles)} curated articles"

    print(f"Sending newsletter to {len(subscribers)} subscriber(s)...")
    success, failed = 0, 0
    for email in subscribers:
        html = build_html_email(articles, email)
        if send_email(email, subject, html):
            print(f"  [OK] {email}")
            success += 1
        else:
            print(f"  [FAIL] {email}")
            failed += 1

    print(f"\nDone: {success}/{len(subscribers)} sent{f', {failed} failed' if failed else ''}.")


if __name__ == "__main__":
    main()
