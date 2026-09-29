"""
Finds LICENCE-COMPATIBLE candidate images on Wikimedia Commons for a search phrase and writes
them to a review file. It never approves anything and never touches the DB: a human curator
opens each file page, checks the licence/attribution, then sets "status": "approved" by hand
(Content_Sourcing_Policy §6 — Commons licence metadata is often wrong, so auto-approval is off).

Accepted licences: public domain, CC0, CC BY, CC BY-SA. Rejected: NC, ND, "fair use", unknown.
(CC BY-SA carries share-alike; NC would break if the app is ever monetised.)

    python source_media.py --nat-id PHYS-78-03 --tema "Út és idő kiszámítása" \
        --match út idő --query "speedometer car" --out ../media/PHYS-78-03_candidates.json
    python source_media.py --download ../media/PHYS-78-03_candidates.json   # approved entries only

Downloaded files are staged in content/media/staging/<NAT-ID>/ — upload each to the public Storage
bucket `content-media` at the printed path (self-hosted, never hotlinked). Then feed the file to
apply_media.py.
"""
import os, re, sys, json, argparse, html

UA = "TurulAcademyBot/0.1 (https://turul.academy; support@turul.app)"
API = "https://commons.wikimedia.org/w/api.php"
OK_MIME = {"image/jpeg", "image/png", "image/svg+xml"}
STAGING = os.path.join(os.path.dirname(__file__), "../media/staging")  # upload to Storage bucket `content-media`


def licence_ok(name):
    n = (name or "").strip().lower().replace("_", " ")
    if not n or re.search(r"\b(nc|nd)\b|non-?commercial|no ?deriv|fair use|all rights", n):
        return False
    return bool(re.match(r"^(public domain|pd\b|cc0|cc[- ]by(?:[- ]sa)?\b)", n))


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def to_candidate(page, tema, match):
    ii = (page.get("imageinfo") or [{}])[0]
    m = ii.get("extmetadata") or {}
    lic = (m.get("LicenseShortName") or {}).get("value", "")
    if ii.get("mime") not in OK_MIME or not licence_ok(lic):
        return None
    author = strip_tags((m.get("Artist") or {}).get("value")) or "ismeretlen"
    title = page["title"].removeprefix("File:")
    return {"tema": tema, "match": match, "title": title,
            "alt": strip_tags((m.get("ImageDescription") or {}).get("value"))[:200],
            "media": {"src": None, "source_url": ii.get("descriptionurl"), "download_url": ii.get("thumburl") or ii.get("url"),
                      "author": author, "license": lic, "license_url": (m.get("LicenseUrl") or {}).get("value"),
                      "credit": f"{author} · {lic}", "status": "pending"}}


def get_with_backoff(url, params=None, tries=5, timeout=20, **kw):
    """GET honouring Retry-After on 429 (Wikimedia robot policy); other errors raise immediately."""
    import time, httpx
    for attempt in range(tries):
        r = httpx.get(url, headers={"User-Agent": UA}, params=params, timeout=timeout, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        try:
            wait = int(r.headers.get("retry-after", ""))
        except ValueError:
            wait = 15 * (attempt + 1)
        if attempt == tries - 1:
            break
        print(f"429 from {httpx.URL(url).host}; waiting {wait}s (attempt {attempt + 1}/{tries})", file=sys.stderr)
        time.sleep(min(wait, 120))
    r.raise_for_status()


def search(query, tema, match, limit):
    r = get_with_backoff(API, {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": limit,
        "gsrsearch": query, "prop": "imageinfo", "iiprop": "url|mime|extmetadata", "iiurlwidth": 900})
    pages = (r.json().get("query") or {}).get("pages", {})
    return [c for p in sorted(pages.values(), key=lambda p: p.get("index", 0)) if (c := to_candidate(p, tema, match))]


def download(path):
    import httpx
    d = json.load(open(path, encoding="utf-8")); nat = d["nat_id"]
    for it in d["items"]:
        m = it.get("media") or {}
        if m.get("status") != "approved" or m.get("src"):
            continue
        ext = os.path.splitext(m["download_url"].split("?")[0])[1] or ".jpg"
        name = re.sub(r"[^a-z0-9]+", "-", it["title"].rsplit(".", 1)[0].lower()).strip("-")[:60] + ext
        os.makedirs(os.path.join(STAGING, nat), exist_ok=True)
        r = get_with_backoff(m["download_url"], timeout=60, follow_redirects=True)
        open(os.path.join(STAGING, nat, name), "wb").write(r.content)
        m["src"] = f"content-media/{nat.lower()}/{name}"  # upload the staged file to exactly this Storage path
        m["verified_at"] = m.get("verified_at") or __import__("datetime").datetime.utcnow().isoformat() + "Z"
        print("✓", m["src"])
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nat-id"); ap.add_argument("--tema"); ap.add_argument("--match", nargs="+")
    ap.add_argument("--query"); ap.add_argument("--out"); ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--download")
    a = ap.parse_args()
    if a.download:
        return download(a.download)
    if not (a.nat_id and a.tema and a.match and a.query and a.out):
        ap.error("--nat-id --tema --match --query --out are required")
    found = search(a.query, a.tema, a.match, a.limit)
    d = json.load(open(a.out, encoding="utf-8")) if os.path.exists(a.out) else {"nat_id": a.nat_id, "items": []}
    d["items"] += found
    json.dump(d, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(found)} licence-compatible candidates → {a.out} (all pending: review each Commons page by hand)")


if __name__ == "__main__":
    main()
