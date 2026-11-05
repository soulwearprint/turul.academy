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
from dataclasses import dataclass, field
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
        "giftee_wishes": "{receiver} ezeknek örülne:",
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
        "giftee_wishes": "{receiver} would be happy with:",
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
    receiver_wishes: list = field(default_factory=list)  # [{"text", "url"}] known at sending time

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
    if l.receiver_wishes:
        lines.append(t["giftee_wishes"].format(receiver=l.receiver_name))
        lines += [f"  - {w['text']}" + (f" ({w['url']})" if w.get("url") else "") for w in l.receiver_wishes]
        lines.append("")
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
    wishes = (
        f'<p style="margin:0 0 4px;font-size:14px;color:#1d5c3f;"><b>{t["giftee_wishes"].format(receiver=e(l.receiver_name))}</b></p>'
        + _wish_list_html(l.receiver_wishes) if l.receiver_wishes else ""
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
        {wishes}
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
    deliver(build_message(l), l.giver_email, f"{l.year}")


def deliver(msg: EmailMessage, to_email: str, tag: str) -> None:
    """Send one message (or, in outbox mode, write it to data/outbox/<tag>_<email>.eml)."""
    if mode() == "outbox":
        out = outbox_dir()
        out.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in to_email)
        (out / f"{tag}_{safe}.eml").write_bytes(bytes(msg))
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



# ─── Other mails: wish-list invitation, "new gift idea" notice ────────────

def _wish_list_html(items: list) -> str:
    e = html.escape
    lis = "".join(
        f'<li style="margin:3px 0;">{e(w["text"])}'
        + (f' &mdash; <a href="{e(w["url"])}" style="color:#1d5c3f;">link</a>' if w.get("url") else "") + "</li>"
        for w in items
    )
    return f'<ul style="margin:0 0 14px;padding-left:22px;font-size:14px;color:#3a2410;">{lis}</ul>'


def _button(url: str, label: str) -> str:
    e = html.escape
    return (
        '<table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:18px auto 6px;">'
        f'<tr><td align="center" style="border-radius:8px;background:#1d5c3f;"><a href="{e(url)}" '
        'style="display:inline-block;padding:11px 22px;font-family:Arial,sans-serif;font-size:15px;font-weight:bold;'
        f'color:#ffffff;text-decoration:none;">{label}</a></td></tr></table>'
    )


def _shell(lang: str, title: str, preheader: str, inner: str, footer: str) -> str:
    """The same airmail-postcard frame as the main card, without stamp/postmark."""
    e = html.escape
    serif = "Georgia,'Times New Roman',serif"
    script = "'Brush Script MT','Segoe Script','Lucida Handwriting',cursive"
    t = TEXTS.get(lang, TEXTS[DEFAULT_LANG])
    return f"""<!doctype html>
<html lang="{e(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{e(title)}</title></head>
<body style="margin:0;padding:0;background:#0f2f24;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f2f24;"><tr><td align="center" style="padding:28px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#c8102e;background-image:repeating-linear-gradient(135deg,#c8102e 0 18px,#ffffff 18px 30px,#1d5c3f 30px 48px,#ffffff 48px 60px);border-radius:6px;">
  <tr><td style="padding:10px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbf3e2;border-radius:3px;">
    <tr><td style="padding:22px 28px 0;font-family:{serif};font-size:12px;letter-spacing:3px;color:#8a6a45;text-transform:uppercase;">{t["header"]} &nbsp;🎅</td></tr>
    <tr><td style="padding:12px 28px 8px;font-family:{serif};color:#3a2410;">
      {inner}
      <p style="margin:18px 0 0;font-size:14px;">{t["closing"]}</p>
      <p style="margin:2px 0 0;font-family:{script};font-size:32px;color:#c8102e;">{t["signature"]}</p>
    </td></tr>
    <tr><td style="padding:10px 28px 18px;border-top:1px dashed #d9c7a3;font-family:{serif};font-size:11px;color:#8a6a45;">{footer}</td></tr>
    </table>
  </td></tr></table>
</td></tr></table>
</body></html>"""


def _envelope(lang: str, to_name: str, to_email: str, subj: str, text: str, html_body: str) -> EmailMessage:
    t = TEXTS.get(lang, TEXTS[DEFAULT_LANG])
    sender = os.environ.get("MAIL_FROM", "santa@example.com")
    msg = EmailMessage()
    msg["Subject"] = subj
    msg["From"] = formataddr((os.environ.get(f"MAIL_FROM_NAME_{lang.upper()}") or t["from_name"], sender))
    msg["To"] = formataddr((to_name, to_email))
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    return msg


INVITE = {
    "hu": {
        "subject": "🎄 Készül a titkos Mikulás-húzás, {name}! Mit kérnél?",
        "pre": "Írd meg pár ajándékötletedet, mielőtt a manók kihúzzák a neveket.",
        "greeting": "Ho-ho-ho, kedves {name}!",
        "body": "Hamarosan kihúzzuk a neveket a {year}-es titkos Mikulásra. Hogy a titkos Mikulásodnak "
                "ne kelljen találgatnia (vagy telefonon faggatnia a rokonságot), írj meg néhány ajándékötletet, "
                "aminek örülnél. Teljesen önkéntes!",
        "button": "🎁 Megadom az ötleteimet",
        "budget": "Ajándékkeret: <b>{budget}</b> &ndash; kérlek, ennél drágább ötletet ne írj. 😉",
        "budget_text": "Ajándékkeret: {budget} – kérlek, ennél drágább ötletet ne írj.",
        "after": "Amint megvan a húzás, megérkezik a képeslapod is, benne a megajándékozottad nevével.",
        "footer": "Ez a link csak a tiéd &ndash; kérlek, ne továbbítsd. &middot; <a href=\"{url}#lang\" style=\"color:#8a6a45;\">Read this in English</a>",
        "text_link": "A te oldalad (ne add tovább):",
    },
    "en": {
        "subject": "🎄 Secret Santa is coming, {name}! What would you like?",
        "pre": "Add a few gift ideas before the elves draw the names.",
        "greeting": "Ho ho ho, dear {name}!",
        "body": "We will soon draw the names for Secret Santa {year}. So that your Secret Santa doesn't have to guess "
                "(or phone around the family), add a few gift ideas you would be happy to receive. Completely optional!",
        "button": "🎁 Add my gift ideas",
        "budget": "Gift budget: <b>{budget}</b> &ndash; please keep your ideas within it. 😉",
        "budget_text": "Gift budget: {budget} – please keep your ideas within it.",
        "after": "Once the names are drawn, your postcard will arrive with the name of your giftee.",
        "footer": "This link is just for you &ndash; please don&rsquo;t forward it. &middot; <a href=\"{url}#lang\" style=\"color:#8a6a45;\">Olvasd el magyarul</a>",
        "text_link": "Your page (please don't share):",
    },
}


def build_invite(name: str, to_email: str, lang: str, year: int, budget: str, url: str) -> EmailMessage:
    e = html.escape
    t = INVITE.get(lang, INVITE[DEFAULT_LANG])
    inner = (
        f'<p style="margin:0 0 12px;font-size:22px;">{t["greeting"].format(name=e(name))}</p>'
        f'<p style="margin:0 0 12px;font-size:15px;line-height:1.6;">{t["body"].format(year=year)}</p>'
        + (f'<p style="margin:0;padding:8px 12px;background:#fff1c2;border-left:4px solid #b8860b;font-size:14px;">💰 {t["budget"].format(budget=e(budget))}</p>' if budget else "")
        + _button(url, t["button"])
        + f'<p style="margin:12px 0 0;font-size:14px;line-height:1.5;">{t["after"]}</p>'
    )
    text = "\n".join([
        t["greeting"].format(name=name), "", t["body"].format(year=year), "",
        *([t["budget_text"].format(budget=budget), ""] if budget else []),
        t["text_link"], url, "", t["after"],
    ])
    subj = t["subject"].format(name=name)
    return _envelope(lang, name, to_email, subj, text,
                     _shell(lang, subj, t["pre"], inner, t["footer"].format(url=e(url))))


REASONS = {
    "hu": {"got_it": "már megkapta / van hasonlója", "not_wanted": "már nem szeretné",
           "mistake": "tévedésből került fel", "other": "már nem aktuális"},
    "en": {"got_it": "already got it / has a similar one", "not_wanted": "doesn't want it any more",
           "mistake": "added by mistake", "other": "no longer relevant"},
}

DIGEST = {
    "hu": {
        # no giftee name in the subject: lock-screen previews
        "subject": "🎁 Napi hírek a megajándékozottad kívánságlistájáról",
        "pre": "Friss hírek az Északi-sarkról.",
        "greeting": "Ho-ho-ho, kedves {name}!",
        "intro": "A manók összegyűjtötték, mi változott <b>{receiver}</b> kívánságlistáján:",
        "intro_text": "A manók összegyűjtötték, mi változott {receiver} kívánságlistáján:",
        "new": "Új ötletek",
        "gone": "Már nem aktuális",
        "all": "A jelenlegi kívánságlista",
        "empty": "(jelenleg nincs aktív ötlet)",
        "budget": "Emlékeztető &ndash; ajándékkeret: <b>{budget}</b>",
        "budget_text": "Emlékeztető – ajándékkeret: {budget}",
        "hint": "A lista bármikor megnézhető a képeslapodban lévő gombbal.",
        "footer": "Ez a levél csak neked szól &ndash; kérlek, ne továbbítsd.",
    },
    "en": {
        "subject": "🎁 Today's news from your giftee's wish list",
        "pre": "Fresh news from the North Pole.",
        "greeting": "Ho ho ho, dear {name}!",
        "intro": "The elves have collected what changed on <b>{receiver}</b>'s wish list:",
        "intro_text": "The elves have collected what changed on {receiver}'s wish list:",
        "new": "New ideas",
        "gone": "No longer wanted",
        "all": "The current wish list",
        "empty": "(no active ideas at the moment)",
        "budget": "Reminder &ndash; gift budget: <b>{budget}</b>",
        "budget_text": "Reminder – gift budget: {budget}",
        "hint": "You can see the list any time with the button in your postcard.",
        "footer": "This e-mail is just for you &ndash; please don&rsquo;t forward it.",
    },
}


def build_digest(name: str, to_email: str, lang: str, receiver: str, new_items: list, gone_items: list,
                 current: list, budget: str) -> EmailMessage:
    e = html.escape
    t = DIGEST.get(lang, DIGEST[DEFAULT_LANG])
    reasons = REASONS.get(lang, REASONS[DEFAULT_LANG])
    h3 = lambda txt, color: f'<p style="margin:10px 0 4px;font-size:14px;color:{color};"><b>{txt}</b></p>'
    gone_html = "".join(
        f'<li style="margin:3px 0;"><s>{e(i["text"])}</s> <span style="color:#8a6a45;">&ndash; {e(reasons.get(i["reason"], reasons["other"]))}</span></li>'
        for i in gone_items)
    inner = (
        f'<p style="margin:0 0 12px;font-size:22px;">{t["greeting"].format(name=e(name))}</p>'
        f'<p style="margin:0 0 6px;font-size:15px;">{t["intro"].format(receiver=e(receiver))}</p>'
        + (h3("✨ " + t["new"], "#1d5c3f") + _wish_list_html(new_items) if new_items else "")
        + (h3("✖ " + t["gone"], "#c8102e") + f'<ul style="margin:0 0 14px;padding-left:22px;font-size:14px;color:#3a2410;">{gone_html}</ul>'
           if gone_items else "")
        + h3("🎁 " + t["all"], "#3a2410")
        + (_wish_list_html(current) if current else f'<p style="margin:0 0 14px;font-size:14px;color:#8a6a45;">{t["empty"]}</p>')
        + (f'<p style="margin:0;padding:8px 12px;background:#fff1c2;border-left:4px solid #b8860b;font-size:14px;">💰 {t["budget"].format(budget=e(budget))}</p>' if budget else "")
        + f'<p style="margin:12px 0 0;font-size:13px;color:#5b3a1a;">{t["hint"]}</p>'
    )
    fmt = lambda items: [f"  - {w['text']}" + (f" ({w['url']})" if w.get("url") else "") for w in items]
    text = "\n".join([
        t["greeting"].format(name=name), "", t["intro_text"].format(receiver=receiver), "",
        *([t["new"] + ":", *fmt(new_items), ""] if new_items else []),
        *([t["gone"] + ":", *[f"  - {i['text']} ({reasons.get(i['reason'], reasons['other'])})" for i in gone_items], ""] if gone_items else []),
        t["all"] + ":", *(fmt(current) or ["  " + t["empty"]]), "",
        *([t["budget_text"].format(budget=budget), ""] if budget else []), t["hint"],
    ])
    return _envelope(lang, name, to_email, t["subject"], text, _shell(lang, t["subject"], t["pre"], inner, t["footer"]))
