# 🎅 Family Secret Santa

A small self-hosted app for a family Secret Santa: keep a family list with
e-mail addresses, draw names secretly each year, and e-mail every person
their own postcard from the North Pole.

Python 3.11+ · FastAPI · SQLite · no build step. It is self-contained and
unrelated to the rest of this repository.

## Run it

```bash
cd secret-santa
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in SMTP settings to send real e-mail
uvicorn app.main:app --env-file .env --port 8080
```

Open http://localhost:8080 and create the first admin.

Tests: `pip install -r requirements-dev.txt && python -m pytest -q`

## How it works

| Requirement | Implementation |
|---|---|
| Family members with e-mails | **Family** tab. Removing someone who took part in a past year archives them, so history is kept. |
| 1-to-1 random draw | Uniform random derangement: everyone gives once, receives once, never draws themselves (`app/draw.py`). |
| Up to 5 admins, the first one mandatory | Created at setup; admins #2 to #5 are optional, and admin #1 cannot be removed. |
| Admins can unlock the matches | **🔓 Unlock matches** asks for the password again and writes `MATCHES REVEALED` to the log, which every admin can see. |
| Results stored per year | One draw per year. New years start from the previous year's list. |
| Participant list changes from year to year | Tick or untick people for each year. |
| Confirmation of who gets reshuffled after a change | See [Changing the list after the draw](#changing-the-list-after-the-draw). |
| Personal postcard e-mails | One message per person with a single `To:` address and no CC or BCC. The subject line never names the giftee, because subjects show on lock screens. The admin who presses *Send* never sees what the postcard says. |

### Secrecy model

- The matches are **encrypted at rest** with AES-256-GCM. The key is wrapped
  separately with each admin's password (scrypt). Someone who copies the
  database file can't read who drew whom without an admin password.
- While logged in, the unwrapped key is kept only in server memory. Restarting
  the server logs everyone out.
- **There is no password reset.** If every admin forgets their password, past
  matches can't be recovered, though new draws still work after re-setup on a
  fresh database. Add a second admin as a backup.

### Changing the list after the draw

When you save a different participant list for a year that has already been
drawn, sending postcards is blocked and a dialog asks **who should be
reshuffled**:

- **Reshuffle everyone** gives a completely new draw.
- **Pick names** redraws only the people you tick. Everyone else keeps their
  giftee, which helps when some gifts are already bought.
- **New members** are always included.
- **People whose giftee left** must be redrawn as well. They are included
  automatically and **not shown to you**, and the same number of random
  *decoys* is mixed in with them. The dialog reports only a count, and that
  count doesn't change with your selection, so it can't reveal who was giving
  to the person who left.

Everyone who is redrawn gets a new, marked **Updated card**, even if they
happened to draw the same person again.

## Sending e-mail

If `SMTP_HOST` is not set, the app runs in **outbox mode** and writes `.eml`
files to `data/outbox/` (for testing; those files contain the matches).

Any SMTP provider works; see `.env.example` for Resend and Gmail settings.
Use port 465 for SSL or 587 for STARTTLS.

> ⚠️ **Where copies of the e-mails end up.** The postcards are hidden from the
> other participants, but your mail provider still keeps copies:
> - **Gmail or Outlook SMTP** saves every sent postcard in the sender's *Sent*
>   folder, so whoever owns that mailbox can read all the matches. Use a
>   dedicated account that no participant reads.
> - **Resend, Brevo, Mailgun and similar** keep message logs in their
>   dashboard. Anyone with dashboard access can open them.
> - Recipients who **share an inbox** (for example, a child using a parent's
>   address) will see each other's cards.

## Deploying

This is a single process with a single SQLite file. Any small host with a
persistent disk works, such as Railway (with a volume), Fly.io or a home
server. Serve it over HTTPS and set `SANTA_SECURE_COOKIE=1`. Back up
`data/santa.db`.

Serverless hosts such as Vercel don't fit this app as written, for two
reasons: the filesystem there is temporary, and sessions are kept in memory.
