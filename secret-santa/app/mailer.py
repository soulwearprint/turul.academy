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


# All postcard wording, per language. Hungarian is the default.
TEXTS = {
    "hu": {
        "subject": "📮 Titkos levél érkezett az Északi-sarkról, {giver}!",
        "preheader": "Egy nyugodt, titkos helyen nyisd meg – ez csak neked szól. ✨",
        "header": "Képeslap · Északi-sarki Posta",
        "stamp": "ÉSZAKI-SARK",
        "postmark": "MIKULÁS<br>MŰHELYE<br>★ DEC. 24. ★",
        "greeting": "Ho-ho-ho, kedves {giver}!",
        "updated_html": "✉️ <b>Frissített képeslap.</b> A manóknak újra kellett húzniuk néhány nevet &ndash; ez a lap felülírja a korábbit.",
        "updated_text": "(FRISSÍTETT KÉPESLAP: a manóknak újra kellett húzniuk néhány nevet. Ez a lap felülírja a korábbit.)",
        "body": "Manóim az északi fény alatt szorgosan húzták a neveket, és örömmel tudatom veled, "
                "hogy {year} karácsonyán te leszel a titkos Mikulás. A megajándékozottad&hellip;",
        "body_text": "Manóim kihúzták a neveket: {year} karácsonyán te leszel a titkos Mikulás. A megajándékozottad:",
        "giftee": "✦ A TE MEGAJÁNDÉKOZOTTAD ✦",
        "budget": "Ajándékkeret",
        "exchange": "Ajándékozás",
        "secret": "Ne feledd: ez a mi kis titkunk. Senkinek ne áruld el &ndash; még a rénszarvasoknak sem! 🦌",
        "secret_text": "Ne feledd: ez a mi kis titkunk. Senkinek ne áruld el – még a rénszarvasoknak sem!",
        "closing": "Meleg üdvözlettel az Északi-sarkról,",
        "signature": "a Mikulás",
        "footer": "Címzett: {giver} &middot; szánon kézbesítve, manók által lepecsételve. Kérlek, ne továbbítsd ezt a lapot.",
        "from_name": "Mikulás · Északi-sark",
        "page_button": "🎁 Kívánságlisták megnyitása",
        "page_sub": "Itt láthatod, mit szeretne {receiver}, és megadhatod a saját ajándékötleteidet is.",
        "page_text": "Kívánságlisták (a te titkos oldalad – ne add tovább a linket):",
        "switch_lang": "Read this card in English",
    },
    "en": {
        "subject": "📮 A secret letter from the North Pole for {giver}",
        "preheader": "Open me somewhere private — this one is just for you. ✨",
        "header": "Post Card · North Pole Mail",
        "stamp": "NORTH POLE",
        "postmark": "SANTA'S<br>WORKSHOP<br>★ 24 DEC ★",
        "greeting": "Ho ho ho, dear {giver}!",
        "updated_html": "✉️ <b>Updated card.</b> The elves had to re-draw some names &mdash; this card replaces any earlier one.",
        "updated_text": "(UPDATED CARD: the elves had to re-draw some names. This card replaces any earlier one.)",
        "body": "My elves have been very busy drawing names by the light of the northern stars, and I am "
                "delighted to tell you that for Christmas {year} you will be the Secret Santa of&hellip;",
        "body_text": "The elves have drawn the names: for Christmas {year} you will be the Secret Santa of:",
        "giftee": "✦ YOUR GIFTEE ✦",
        "budget": "Gift budget",
        "exchange": "Gift exchange",
        "secret": "Remember: this is our little secret. Tell no one &mdash; not even the reindeer! 🦌",
        "secret_text": "Remember: this is our little secret. Tell no one — not even the reindeer!",
        "closing": "With warm wishes from the North Pole,",
        "signature": "Santa Claus",
        "footer": "To: {giver} &middot; delivered by sleigh, sealed by elves. Please don&rsquo;t forward this card.",
        "from_name": "Santa Claus · North Pole",
        "page_button": "🎁 Open the wish lists",
        "page_sub": "See what {receiver} would love to get, and add a few gift ideas of your own.",
        "page_text": "Wish lists (your private page — please don't share the link):",
        "switch_lang": "Olvasd el magyarul",
    },
}
LANGS = tuple(TEXTS)
DEFAULT_LANG = "hu"


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
    lang: str = DEFAULT_LANG
    page_url: str = ""  # personal page (wish lists, language); private to this person

    @property
    def t(self) -> dict[str, str]:
        return TEXTS.get(self.lang, TEXTS[DEFAULT_LANG])


def mode() -> str:
    return "smtp" if os.environ.get("SMTP_HOST") else "outbox"


def outbox_dir() -> Path:
    return Path(os.environ.get("SANTA_OUTBOX", Path(__file__).resolve().parent.parent / "data" / "outbox"))


def subject(l: Letter) -> str:
    # Deliberately does NOT contain the receiver: subjects show up on lock screens.
    return l.t["subject"].format(giver=l.giver_name)


def render_text(l: Letter) -> str:
    t = l.t
    lines = [t["greeting"].format(giver=l.giver_name), ""]
    if l.updated:
        lines += [t["updated_text"], ""]
    lines += [t["body_text"].format(year=l.year), "", f"    ★ {l.receiver_name} ★", ""]
    if l.budget:
        lines.append(f"{t['budget']}: {l.budget}")
    if l.exchange_date:
        lines.append(f"{t['exchange']}: {l.exchange_date}")
    if l.note:
        lines += ["", l.note]
    if l.page_url:
        lines += ["", t["page_text"], l.page_url]
    lines += ["", t["secret_text"], "", t["closing"], t["signature"]]
    if l.page_url:
        lines += ["", f"{t['switch_lang']}: {l.page_url}#lang"]
    return "\n".join(lines)


def render_html(l: Letter) -> str:
    e = html.escape
    t = l.t
    giver = e(l.giver_name)
    details = ""
    if l.budget:
        details += f'<tr><td style="padding:2px 0;font-size:14px;color:#5b3a1a;">🎁 <b>{t["budget"]}:</b> {e(l.budget)}</td></tr>'
    if l.exchange_date:
        details += f'<tr><td style="padding:2px 0;font-size:14px;color:#5b3a1a;">📅 <b>{t["exchange"]}:</b> {e(l.exchange_date)}</td></tr>'
    note = (
        f'<p style="margin:14px 0 0;font-size:14px;line-height:1.5;color:#5b3a1a;font-style:italic;">{e(l.note)}</p>'
        if l.note else ""
    )
    updated = (
        '<p style="margin:0 0 12px;padding:8px 12px;background:#fff1c2;border-left:4px solid #b8860b;font-size:13px;color:#5b3a1a;">'
        f'{t["updated_html"]}</p>' if l.updated else ""
    )
    page = ""
    switch = ""
    if l.page_url:
        url = e(l.page_url)
        page = (
            '<table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:18px auto 4px;">'
            f'<tr><td align="center" style="border-radius:8px;background:#1d5c3f;">'
            f'<a href="{url}" style="display:inline-block;padding:11px 22px;font-family:Arial,sans-serif;font-size:15px;'
            f'font-weight:bold;color:#ffffff;text-decoration:none;">{t["page_button"]}</a></td></tr></table>'
            f'<p style="margin:0;text-align:center;font-size:13px;color:#5b3a1a;">{t["page_sub"].format(receiver=e(l.receiver_name))}</p>'
        )
        switch = f' &middot; <a href="{url}#lang" style="color:#8a6a45;">{t["switch_lang"]}</a>'
    serif = "Georgia,'Times New Roman',serif"
    script = "'Brush Script MT','Segoe Script','Lucida Handwriting',cursive"
    # Table layout + inline styles only: that is what e-mail clients render reliably.
    return f"""<!doctype html>
<html lang="{e(l.lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{e(subject(l))}</title></head>
<body style="margin:0;padding:0;background:#0f2f24;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{t["preheader"]}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f2f24;">
<tr><td align="center" style="padding:28px 12px;">
  <div style="font-size:18px;letter-spacing:10px;color:#e8f1ee;padding-bottom:10px;">❄ ✦ ❄ ✦ ❄</div>
  <!-- airmail border -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#c8102e;background-image:repeating-linear-gradient(135deg,#c8102e 0 18px,#ffffff 18px 30px,#1d5c3f 30px 48px,#ffffff 48px 60px);border-radius:6px;">
  <tr><td style="padding:10px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbf3e2;border-radius:3px;">
    <tr>
      <td style="padding:22px 24px 0;font-family:{serif};font-size:12px;letter-spacing:3px;color:#8a6a45;text-transform:uppercase;">
        {t["header"]}
      </td>
      <td align="right" valign="top" style="padding:16px 18px 0 0;width:120px;">
        <!-- stamp -->
        <table role="presentation" cellpadding="0" cellspacing="0" style="border:2px dashed #c8102e;background:#ffffff;">
        <tr><td align="center" style="padding:6px 10px;font-family:{serif};">
          <div style="font-size:34px;line-height:40px;">🎅</div>
          <div style="font-size:9px;letter-spacing:1px;color:#c8102e;font-weight:bold;">{t["stamp"]}</div>
          <div style="font-size:9px;color:#1d5c3f;">{l.year} · 1 ♥</div>
        </td></tr></table>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:0 24px;">
        <!-- postmark -->
        <div style="float:right;margin:-6px 70px 0 0;width:78px;height:78px;border:2px solid #3b5f8a;border-radius:50%;color:#3b5f8a;font-family:{serif};font-size:9px;text-align:center;line-height:12px;opacity:.75;transform:rotate(-14deg);">
          <div style="padding-top:20px;">{t["postmark"]}</div>
        </div>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:6px 28px 8px;font-family:{serif};color:#3a2410;">
        <p style="margin:0 0 12px;font-size:22px;">{t["greeting"].format(giver=giver)}</p>
        {updated}
        <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">{t["body"].format(year=l.year)}</p>
        <table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:6px auto 16px;">
        <tr><td align="center" style="padding:14px 30px;border:2px solid #b8860b;border-radius:10px;background:#fffaf0;">
          <div style="font-size:12px;letter-spacing:3px;color:#1d5c3f;">{t["giftee"]}</div>
          <div style="font-size:30px;font-weight:bold;color:#c8102e;padding-top:4px;">{e(l.receiver_name)}</div>
        </td></tr></table>
        <table role="presentation" cellpadding="0" cellspacing="0">{details}</table>
        {note}
        {page}
        <p style="margin:16px 0 0;font-size:14px;line-height:1.5;">{t["secret"]}</p>
        <p style="margin:18px 0 0;font-size:14px;">{t["closing"]}</p>
        <p style="margin:2px 0 0;font-family:{script};font-size:34px;color:#c8102e;">{t["signature"]}</p>
      </td>
    </tr>
    <tr>
      <td colspan="2" style="padding:10px 28px 18px;border-top:1px dashed #d9c7a3;font-family:{serif};font-size:11px;color:#8a6a45;">
        {t["footer"].format(giver=giver)}{switch}
      </td>
    </tr>
    </table>
  </td></tr></table>
  <div style="font-size:18px;letter-spacing:10px;color:#e8f1ee;padding-top:10px;">❄ ✦ ❄ ✦ ❄</div>
</td></tr></table>
</body></html>"""


def build_message(l: Letter) -> EmailMessage:
    sender = os.environ.get("MAIL_FROM", "santa@example.com")
    sender_name = os.environ.get(f"MAIL_FROM_NAME_{l.lang.upper()}") or l.t["from_name"]
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
