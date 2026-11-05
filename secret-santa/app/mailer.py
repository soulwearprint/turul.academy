"""Postcard e-mails from the North Pole.

Each participant gets their own message (single To:, no CC/BCC), so nobody
sees anyone else's match. Uses plain SMTP, which covers Gmail, Outlook,
Resend (smtp.resend.com), Brevo, Mailgun, etc.

If SMTP_HOST is not set, the app runs in *outbox mode*: messages are written
as .eml files to data/outbox/ instead of being sent (for local testing only).
"""
from __future__ import annotations

import html
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path


@dataclass
class Letter:
    giver_name: str
    giver_email: str
    receiver_name: str
    year: int
    budget: str = ""
    exchange_date: str = ""
    note: str = ""
    updated: bool = False  # a re-draw replaced an earlier card


def mode() -> str:
    return "smtp" if os.environ.get("SMTP_HOST") else "outbox"


def outbox_dir() -> Path:
    return Path(os.environ.get("SANTA_OUTBOX", Path(__file__).resolve().parent.parent / "data" / "outbox"))


def subject(letter: Letter) -> str:
    # Deliberately does NOT contain the receiver: subjects show up on lock screens.
    return f"📮 A secret letter from the North Pole for {letter.giver_name}"


def render_text(l: Letter) -> str:
    lines = [
        f"Ho ho ho, dear {l.giver_name}!",
        "",
        *(["(UPDATED CARD: the elves had to re-draw some names. This card replaces any earlier one.)", ""] if l.updated else []),
        f"The elves have drawn the names for Christmas {l.year}, and this year",
        "you will be the Secret Santa of:",
        "",
        f"    ★ {l.receiver_name} ★",
        "",
    ]
    if l.budget:
        lines.append(f"Gift budget: {l.budget}")
    if l.exchange_date:
        lines.append(f"Gift exchange: {l.exchange_date}")
    if l.note:
        lines += ["", l.note]
    lines += [
        "",
        "Remember: this is our little secret. Tell no one — not even the reindeer!",
        "",
        "With warm wishes from the North Pole,",
        "Santa Claus",
    ]
    return "\n".join(lines)


def render_html(l: Letter) -> str:
    e = html.escape
    details = ""
    if l.budget:
        details += f'<tr><td style="padding:2px 0;font-size:14px;color:#5b3a1a;">🎁 <b>Gift budget:</b> {e(l.budget)}</td></tr>'
    if l.exchange_date:
        details += f'<tr><td style="padding:2px 0;font-size:14px;color:#5b3a1a;">📅 <b>Gift exchange:</b> {e(l.exchange_date)}</td></tr>'
    note = (
        f'<p style="margin:14px 0 0;font-size:14px;line-height:1.5;color:#5b3a1a;font-style:italic;">{e(l.note)}</p>'
        if l.note else ""
    )
    updated = (
        '<p style="margin:0 0 12px;padding:8px 12px;background:#fff1c2;border-left:4px solid #b8860b;font-size:13px;color:#5b3a1a;">'
        "✉️ <b>Updated card.</b> The elves had to re-draw some names &mdash; this card replaces any earlier one.</p>"
        if l.updated else ""
    )
    serif = "Georgia,'Times New Roman',serif"
    script = "'Brush Script MT','Segoe Script','Lucida Handwriting',cursive"
    # Table layout + inline styles only: that is what e-mail clients render reliably.
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{e(subject(l))}</title></head>
<body style="margin:0;padding:0;background:#0f2f24;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Open me somewhere private — this one is just for you. ✨</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f2f24;">
<tr><td align="center" style="padding:28px 12px;">
  <div style="font-size:18px;letter-spacing:10px;color:#e8f1ee;padding-bottom:10px;">❄ ✦ ❄ ✦ ❄</div>
  <!-- airmail border -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#c8102e;background-image:repeating-linear-gradient(135deg,#c8102e 0 18px,#ffffff 18px 30px,#1d5c3f 30px 48px,#ffffff 48px 60px);border-radius:6px;">
  <tr><td style="padding:10px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbf3e2;border-radius:3px;">
    <tr>
      <td style="padding:22px 24px 0;font-family:{serif};font-size:12px;letter-spacing:3px;color:#8a6a45;text-transform:uppercase;">
        Post Card · North Pole Mail
      </td>
      <td align="right" valign="top" style="padding:16px 18px 0 0;width:120px;">
        <!-- stamp -->
        <table role="presentation" cellpadding="0" cellspacing="0" style="border:2px dashed #c8102e;background:#ffffff;">
        <tr><td align="center" style="padding:6px 10px;font-family:{serif};">
          <div style="font-size:34px;line-height:40px;">🎅</div>
          <div style="font-size:9px;letter-spacing:1px;color:#c8102e;font-weight:bold;">NORTH POLE</div>
          <div style="font-size:9px;color:#1d5c3f;">{l.year} · 1 ♥</div>
        </td></tr></table>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:0 24px;">
        <!-- postmark -->
        <div style="float:right;margin:-6px 70px 0 0;width:78px;height:78px;border:2px solid #3b5f8a;border-radius:50%;color:#3b5f8a;font-family:{serif};font-size:9px;text-align:center;line-height:12px;opacity:.75;transform:rotate(-14deg);">
          <div style="padding-top:20px;">SANTA'S<br>WORKSHOP<br>★ 24 DEC ★</div>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:6px 28px 8px;font-family:{serif};color:#3a2410;">
        <p style="margin:0 0 12px;font-size:22px;">Ho ho ho, dear {e(l.giver_name)}!</p>
        {updated}
        <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">
          My elves have been very busy drawing names by the light of the northern stars,
          and I am delighted to tell you that for Christmas {l.year} you will be the
          Secret Santa of&hellip;
        </p>
        <table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:6px auto 16px;">
        <tr><td align="center" style="padding:14px 30px;border:2px solid #b8860b;border-radius:10px;background:#fffaf0;">
          <div style="font-size:12px;letter-spacing:3px;color:#1d5c3f;">✦ YOUR GIFTEE ✦</div>
          <div style="font-size:30px;font-weight:bold;color:#c8102e;padding-top:4px;">{e(l.receiver_name)}</div>
        </td></tr></table>
        <table role="presentation" cellpadding="0" cellspacing="0">{details}</table>
        {note}
        <p style="margin:16px 0 0;font-size:14px;line-height:1.5;">
          Remember: this is our little secret. Tell no one &mdash; not even the reindeer! 🦌
        </p>
        <p style="margin:18px 0 0;font-size:14px;">With warm wishes from the North Pole,</p>
        <p style="margin:2px 0 0;font-family:{script};font-size:34px;color:#c8102e;">Santa Claus</p>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:10px 28px 18px;border-top:1px dashed #d9c7a3;font-family:{serif};font-size:11px;color:#8a6a45;">
        To: {e(l.giver_name)} &middot; delivered by sleigh, sealed by elves. Please don&rsquo;t forward this card.
      </td>
    </tr>
    </table>
  </td></tr></table>
  <div style="font-size:18px;letter-spacing:10px;color:#e8f1ee;padding-top:10px;">❄ ✦ ❄ ✦ ❄</div>
</td></tr></table>
</body></html>"""


def build_message(l: Letter) -> EmailMessage:
    sender = os.environ.get("MAIL_FROM", "santa@example.com")
    sender_name = os.environ.get("MAIL_FROM_NAME", "Santa Claus · North Pole")
    msg = EmailMessage()
    msg["Subject"] = subject(l)
    msg["From"] = formataddr((sender_name, sender))
    msg["To"] = formataddr((l.giver_name, l.giver_email))
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    msg.set_content(render_text(l))
    msg.add_alternative(render_html(l), subtype="html")
    return msg


def send(l: Letter) -> None:
    msg = build_message(l)
    if mode() == "outbox":
        out = outbox_dir()
        out.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in l.giver_email)
        (out / f"{l.year}_{safe}.eml").write_bytes(bytes(msg))
        return
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            if user:
                s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            if user:
                s.login(user, password)
            s.send_message(msg)
