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
| 1-to-1 random draw | Uniformly random among all valid draws: everyone gives once, receives once, never draws themselves (`app/draw.py`). |
| Couples never draw each other | **Family → Never draw each other**. Each rule works both ways and applies every year. |
| No repeat of last year | On by default for each year (**Details** → *Nobody draws the same person as in the previous year's draw*). It compares against the most recent earlier year that has a draw. |
| Postcard language | Hungarian by default. An admin sets **English** per person in the Family tab, or the participant switches it from the link in their card, optionally getting the card resent. |
| Wish-list invitation before the draw | **✉️ Send wish-list invitations** on a year that hasn't been drawn. Each person gets an e-mail with their own link, so they can add gift ideas early. The invitation shows the budget. Postcards then list the giftee's ideas directly. |
| Daily digest to the giver | Changes to gift ideas reach each Secret Santa in **one e-mail a day** (default 18:00, Europe/Budapest), listing new ideas, ideas that are no longer wanted (with the reason), and the current list. It goes out only after that Secret Santa's postcard has been sent, never repeats anything, and follows reshuffles. Admins can **Send digest now**. |
| Removing vs. marking obsolete | An idea the Secret Santa hasn't received yet (not in their postcard or a digest) can simply be **removed**, and nobody hears about it. Once received, it can only be marked **no longer wanted**, with a reason: *already got it / similar*, *don't want it any more*, *added by mistake*, *other*. It then shows struck through on the giver's page and in the next digest. The owner can **restore** it. |
| Gift ideas | Each card has a **🎁 Open the wish lists** button that leads to that person's private page. There they add up to 5 gift ideas (each with an optional link) and see their giftee's ideas. The year's **gift budget** is shown prominently, including right above the idea form. |
| Up to 5 admins, the first one mandatory | Created at setup; admins #2 to #5 are optional, and admin #1 cannot be removed. See [Admins and sign-in](#admins-and-sign-in). |
| Admins can unlock the matches | **🔓 Unlock matches** requires a fresh confirmation (password again, or a new Google sign-in) and writes `MATCHES REVEALED` to the log, which every admin can see. |
| Results stored per year | One draw per year. New years start from the previous year's list. |
| Participant list changes from year to year | Tick or untick people for each year. |
| Confirmation of who gets reshuffled after a change | See [Changing the list after the draw](#changing-the-list-after-the-draw). |
| Personal postcard e-mails | One message per person with a single `To:` address and no CC or BCC. The subject line never names the giftee, because subjects show on lock screens. The admin who presses *Send* never sees what the postcard says. |

### Draw rules

With 10 to 12 people, a few couples and the no-repeat rule, a valid draw nearly
always exists. The app first samples uniformly at random. If that fails, it
runs an exhaustive search, which settles whether any valid draw exists. If none
does, it says so, for example: *"These rules make a draw impossible. Try
removing an exclusion, or turn off 'avoid last year's match'."*

If a rule is added **after** a draw, whoever now breaks it is redrawn at the
next reshuffle. They are hidden in the same way as the people whose giftee
left (see below).

### Admins and sign-in

An admin is a row in the **Admins** tab with a **name** and one or both of:

- **Password.** At login, the admin types their name and password. Any
  admin can add a new admin with an initial password, which the new admin
  then changes under **Admins → Change my password**. The password never
  leaves the server and is stored only as a scrypt-derived key that unlocks
  the matches.
- **Google account.** The admin clicks **Sign in with Google**. The app
  accepts only verified Google e-mail addresses that are registered on an
  admin row; anyone else is refused, and the refusal is logged. To unlock the
  matches, Google asks the admin to sign in again (`prompt=login`), and that
  confirmation is good for one unlock within 2 minutes.

To set up Google sign-in:

1. In [Google Cloud Console](https://console.cloud.google.com/), go to
   *APIs & Services → Credentials → Create credentials → OAuth client ID*
   and choose *Web application*.
2. Set the *Authorised redirect URI* to `https://<your-host>/auth/google/callback`.
3. On the *OAuth consent screen*, choose *External*. The scopes are only
   `openid email profile`, which are non-sensitive and need no Google review.
   While the app is in *Testing* status, only accounts listed as test users
   can sign in, so add the admins there.
4. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `PUBLIC_URL`,
   `SANTA_SERVER_KEY` and `SANTA_FIRST_ADMIN_EMAIL` (see `.env.example`).
   Admin #1 is then created by signing in with that Google account.

Google sign-in is not part of the automated tests against real Google. The
tests replace Google's token endpoint with a stub, so try one real sign-in
after setting it up.

### Personal pages (wish lists and language)

Participants don't need a login. Every postcard carries a random private link
(`/p/<token>`):

- **The server never stores the token.** It keeps only a hash, used to look
  the link up, plus that person's match encrypted with a key derived from the
  token. So the page can show "your giftee" while no admin is logged in, and
  the database alone still reveals nothing.
- **Anyone with the link sees that person's match**, just like the card
  itself. The page says so ("don't share the link"). It sends
  `Referrer-Policy: no-referrer` so the link isn't leaked to shops linked in
  wish lists.
- **Resending a card, or reshuffling someone, replaces their link.** The old
  link then shows "this link is no longer valid". Gift ideas are kept per
  person per year, so they survive a reshuffle.
- **An invitation is the same kind of link, just without a match.** Each
  person has one link per year, and their postcard link replaces the
  invitation link.
- **How the "new gift idea" e-mail finds the giver.** Every link has its own
  X25519 key pair. Its private half is encrypted with the link token. At draw
  and reshuffle time, the server seals each person's Secret Santa to that
  person's public key. Saving ideas through the link is the only thing that
  can open it, and the result is used only to address the e-mail. The giver
  isn't shown on the page, and the database alone doesn't reveal them.
- **The activity log records only that a notice went out**, worded as
  "to Anna's Secret Santa".
- **Where the digest's giver is kept.** When someone changes their ideas,
  the request carries their link token, so the server can open the giver
  route and queue "this Secret Santa has news". The giver id in that queue
  entry is encrypted with the **server key**: `SANTA_SERVER_KEY` if set,
  otherwise a key generated once into `data/server.key`. The database plus
  that key reveals the pairs that are waiting in the queue, so for real use
  set `SANTA_SERVER_KEY` in the environment, outside the data folder.
- **Daily schedule.** The digest runs inside the app process. Set the hour
  with `SANTA_DIGEST_HOUR` and the time zone with `SANTA_TZ`. Run a single
  app process (one worker), otherwise digests can go out twice.
- **When the Secret Santa changes** (a reshuffle), the new one has seen
  nothing yet. That person's ideas therefore count as unsent again, and
  ideas already marked obsolete are dropped.
- **Gift ideas aren't encrypted.** They aren't secret, and admins see only
  how many ideas each person has added.
- **Gift ideas are per year.** Last year's ideas aren't carried over.
- **Links are prefetch-safe.** The language link opens the page (`#lang`)
  rather than switching on click, because e-mail security scanners open links
  automatically.

Set `PUBLIC_URL` so the links in the cards use your real address. Without it,
the address the admin used to open the app is used.

### Secrecy model

- The matches are **encrypted at rest** with AES-256-GCM. The key is wrapped
  separately with each admin's password (scrypt). Someone who copies the
  database file can't read who drew whom without an admin password.
- While logged in, the unwrapped key is kept only in server memory. Restarting
  the server logs everyone out.
- **With Google sign-in enabled**, the key is also wrapped with
  `SANTA_SERVER_KEY`, an environment secret, because Google confirms who you
  are but gives the app no secret to decrypt with. Reading the matches then
  takes **the database plus that server secret**. So keep the secret out of
  database backups, and don't lose it, or Google-only admins can no longer
  open the matches (password admins still can).
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
