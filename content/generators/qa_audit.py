"""
Web fact-check audit — tooling for the snapshot → findings → apply loop.

The lessons live in Supabase; a session without DB keys audits them from the repo snapshot
(content/snapshot/<nat_id>.json, written by export_snapshot.py) and writes findings to
content/qa/<nat_id>.json. A session WITH keys applies them through edit_content_card, so
every change lands in content_edits and can be undone from /admin/reports → Szerkesztések.
Format: content/qa/README.md.

    python qa_audit.py checklist HIST-56-01          # every text field, numbered, for reading
    python qa_audit.py lint HIST-56-01               # mechanical checks + time-sensitive claims
    python qa_audit.py validate HIST-56-01           # findings file vs. schema and snapshot
    python qa_audit.py status                        # coverage per band
    python qa_audit.py apply HIST-56-01 --dry-run    # needs backend/.env (service key)
    python qa_audit.py apply HIST-56-01 --editor <user_profiles.id>

No network or DB access except `apply`.
"""
import os, re, sys, json, argparse
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "../snapshot")
QA = os.path.join(HERE, "../qa")

VERDICTS = {
    "wrong":        "the claim is false",
    "outdated":     "was true, no longer is (records, 'today', statistics)",
    "misleading":   "technically true but teaches a wrong picture / misconception",
    "quiz_key":     "the quiz's marked answer is wrong, or more than one option is correct",
    "unverifiable": "no reliable source confirms it — generalise or remove",
    "language":     "grammar / Hungarian number format / article damage",
}
SEVERITIES = ("high", "medium", "low")      # high: a student would learn or be graded on something false
APPLY = ("auto", "review", "none")          # auto: safe to apply as is; review: a human decides
NEEDS_SOURCE = {"wrong", "outdated", "misleading"}   # quiz_key can be internal (key not an option)

# Words that make a claim go stale or make it checkable against the world rather than the textbook.
TIME_SENSITIVE = re.compile(
    r"\b(rekord\w*|világrekord\w*|jelenleg|napjainkban|ma már|mai napig|máig|legújabb|"
    r"a világ leg\w+|leg(?:nagyobb|kisebb|gyorsabb|magasabb|hosszabb|mélyebb|régebbi|több)\w*|"
    r"millió|milliárd|százalék\w*|\d+\s?%)", re.I)
YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
DOT_DECIMAL = re.compile(r"(?<![\d.])\d+\.\d+(?![\d.])")          # 9.81 → should be 9,81
AZ_CONSONANT = re.compile(r"(?<![^\W\d_])[Aa]z (?=[bcdfghjklmnprstvzBCDFGHJKLMNPRSTVZ])")
A_VOWEL = re.compile(r"(?<![^\W\d_])[Aa] (?=[aáeéiíoóöőuúüűAÁEÉIÍOÓÖŐUÚÜŰ])")


# ── snapshot access ───────────────────────────────────────────────
def load_snapshot(nat_id):
    with open(os.path.join(SNAP, f"{nat_id}.json"), encoding="utf-8") as f:
        return json.load(f)


def iter_blocks(snap):
    """(lesson or None, block) for every block, lesson blocks first."""
    for L in snap.get("lessons", []):
        for b in L.get("blocks", []):
            yield L, b
    for b in snap.get("topic_blocks", []):
        yield None, b


def iter_fields(card, path=""):
    """(field_path, text) for every string in a card, e.g. ('options[2]', 'C) …')."""
    if isinstance(card, str):
        yield path, card
    elif isinstance(card, dict):
        for k, v in card.items():
            if k in ("type", "anchor", "image") and path == "":
                continue                                    # structure / media, not prose
            yield from iter_fields(v, f"{path}.{k}" if path else k)
    elif isinstance(card, list):
        for i, v in enumerate(card):
            yield from iter_fields(v, f"{path}[{i}]")


def block_label(L, b):
    where = f"lesson {L['order_index']}: {L['title_hu']}" if L else "TOPIC"
    return f"{where} · {b['mode']}{'' if b.get('is_active', True) else ' (INACTIVE)'} · block {b['block_id']}"


# ── checklist ─────────────────────────────────────────────────────
def cmd_checklist(a):
    snap = load_snapshot(a.nat_id)
    print(f"# {snap['nat_id']} — {snap['title_hu']} ({snap.get('grade')}. évf.)\n")
    for L, b in iter_blocks(snap):
        if a.modes and b["mode"] not in a.modes:
            continue
        print(f"## {block_label(L, b)}")
        for i, card in enumerate(b.get("content") or []):
            print(f"[{i}]")
            for path, text in iter_fields(card):
                if text.strip():
                    print(f"  {path}: {text}")
        print()


# ── lint ──────────────────────────────────────────────────────────
def lint_card(mode, card):
    """Mechanical problems a reader skims past. Returns (kind, detail) pairs."""
    out = []
    if mode == "quiz" or card.get("type") == "quiz":
        opts = card.get("options") or []
        letters = [re.match(r"\s*([A-Z])\)", o or "") for o in opts]
        letters = [m.group(1) for m in letters if m]
        key = (card.get("correct") or "").strip()
        if card.get("question_type", "multiple_choice") == "multiple_choice":
            if key not in letters:
                out.append(("quiz_key", f"correct='{key}' is not one of the options' letters {letters}"))
            bodies = [re.sub(r"^\s*[A-Z]\)\s*", "", o or "").strip().lower() for o in opts]
            if len(set(bodies)) < len(bodies):
                out.append(("quiz_key", "duplicate options"))
            if not (card.get("explanation") or "").strip():
                out.append(("quiz", "no explanation"))
    text = " ".join(t for _, t in iter_fields(card))
    for m in DOT_DECIMAL.findall(text):                   # full dates (1914.07.28.) don't match
        out.append(("language", f"decimal point: {m} (Hungarian uses a comma)"))
    az = AZ_CONSONANT.findall(text)
    if len(az) >= 2:
        out.append(("language", f"„az” before a consonant ×{len(az)} — possible article damage"))
    if A_VOWEL.findall(text):
        out.append(("language", f"„a” before a vowel ×{len(A_VOWEL.findall(text))}"))
    this_year = date.today().year
    for y in {int(y) for y in YEAR.findall(text)}:
        if y > this_year:
            out.append(("time", f"year {y} is in the future"))
    ts = sorted({m.group(0).lower() for m in TIME_SENSITIVE.finditer(text)})
    if ts:
        out.append(("time_sensitive", ", ".join(ts)))
    return out


def cmd_lint(a):
    snap = load_snapshot(a.nat_id)
    n = 0
    for L, b in iter_blocks(snap):
        for i, card in enumerate(b.get("content") or []):
            for kind, detail in lint_card(b["mode"], card if isinstance(card, dict) else {}):
                if a.only and kind not in a.only:
                    continue
                n += 1
                print(f"{kind:15} {b['mode']:10} [{i}] {(L or {}).get('title_hu', 'TOPIC')[:40]:40} {detail}")
    print(f"\n{n} lint hits in {a.nat_id}", file=sys.stderr)


# ── findings validation ───────────────────────────────────────────
def find_card(snap, block_id, idx):
    for L, b in iter_blocks(snap):
        if b["block_id"] == block_id:
            content = b.get("content") or []
            return L, b, (content[idx] if 0 <= idx < len(content) else None)
    return None, None, None


def validate(nat_id):
    """Errors that would make `apply` refuse or mislead. Empty list = OK."""
    errs = []
    snap = load_snapshot(nat_id)
    with open(os.path.join(QA, f"{nat_id}.json"), encoding="utf-8") as f:
        qa = json.load(f)
    if qa.get("nat_id") != nat_id:
        errs.append(f"nat_id {qa.get('nat_id')!r} ≠ file name")
    if qa.get("snapshot_exported_at") != snap.get("exported_at"):
        errs.append("snapshot_exported_at does not match the snapshot — re-check against the current export")
    seen, edits = set(), {}
    for n, x in enumerate(qa.get("findings", [])):
        tag = f"finding {n} ({x.get('id', '?')})"
        if x.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(x.get("id"))
        if x.get("verdict") not in VERDICTS:
            errs.append(f"{tag}: verdict {x.get('verdict')!r} not in {sorted(VERDICTS)}")
        if x.get("severity") not in SEVERITIES:
            errs.append(f"{tag}: severity {x.get('severity')!r}")
        if x.get("apply") not in APPLY:
            errs.append(f"{tag}: apply {x.get('apply')!r}")
        if x.get("verdict") in NEEDS_SOURCE and not x.get("sources"):
            errs.append(f"{tag}: verdict {x.get('verdict')} needs at least one source")
        for s in x.get("sources") or []:
            if not str(s.get("url", "")).startswith("http"):
                errs.append(f"{tag}: source without a URL")
        L, b, card = find_card(snap, x.get("block_id"), x.get("card_index", -1))
        if b is None:
            errs.append(f"{tag}: block {x.get('block_id')} not in snapshot"); continue
        if card is None:
            errs.append(f"{tag}: card_index {x.get('card_index')} out of range"); continue
        if b["mode"] != x.get("mode"):
            errs.append(f"{tag}: mode {x.get('mode')} ≠ block mode {b['mode']}")
        fix = x.get("fix")
        if x.get("apply") != "none":
            if not fix:
                errs.append(f"{tag}: apply={x.get('apply')} but no fix"); continue
            if fix.get("before") != card:
                errs.append(f"{tag}: fix.before is not the snapshot card (edit_content_card would 409)")
            after = fix.get("after")
            if not isinstance(after, dict) or set(after) != set(card):
                errs.append(f"{tag}: fix.after must be the whole card with the same keys")
            if after == card:
                errs.append(f"{tag}: fix.after equals before")
            key = (x.get("block_id"), x.get("card_index"))
            if key in edits:
                errs.append(f"{tag}: second fix for the same card as {edits[key]} — merge them into one")
            edits[key] = x.get("id")
        elif fix:
            errs.append(f"{tag}: apply=none but a fix is given")
    return errs


def cmd_validate(a):
    ids = a.nat_ids or sorted(f[:-5] for f in os.listdir(QA) if f.endswith(".json"))
    bad = 0
    for nat in ids:
        errs = validate(nat)
        print(f"{'✗' if errs else '✓'} {nat}" + "".join(f"\n    {e}" for e in errs))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


# ── status ────────────────────────────────────────────────────────
def cmd_status(a):
    idx_path = os.path.join(SNAP, "INDEX.json")
    if not os.path.exists(idx_path):
        print("no content/snapshot/INDEX.json yet"); return
    index = json.load(open(idx_path, encoding="utf-8"))
    bands = {}
    for t in index.get("topics", index if isinstance(index, list) else []):
        qa_path = os.path.join(QA, f"{t['nat_id']}.json")
        done = os.path.exists(qa_path)
        f = json.load(open(qa_path, encoding="utf-8"))["findings"] if done else []
        s = bands.setdefault(t.get("band", "?"), {"topics": 0, "checked": 0, "findings": 0, "high": 0})
        s["topics"] += 1; s["checked"] += done
        s["findings"] += len(f); s["high"] += sum(x.get("severity") == "high" for x in f)
    print(f"{'band':14} {'checked':>9} {'findings':>9} {'high':>5}")
    for band, s in bands.items():
        print(f"{band:14} {s['checked']:>4}/{s['topics']:<4} {s['findings']:>9} {s['high']:>5}")


# ── apply (needs the service key) ─────────────────────────────────
def cmd_apply(a):
    import httpx
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "../../backend/.env"))
    sb, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (sb and key):
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing (backend/.env)")
    errs = validate(a.nat_id)
    if errs:
        sys.exit("findings do not validate — fix first:\n  " + "\n  ".join(errs))
    qa = json.load(open(os.path.join(QA, f"{a.nat_id}.json"), encoding="utf-8"))
    wanted = {"auto"} | ({"review"} if a.include_review else set())
    todo = [x for x in qa["findings"] if x["apply"] in wanted]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    applied = qa.setdefault("applied", {})
    with httpx.Client(timeout=7.0) as c:
        for x in todo:
            if x["id"] in applied:
                print(f"  = {x['id']} already applied ({applied[x['id']]})"); continue
            if a.dry_run:
                print(f"  ~ {x['id']} {x['verdict']}/{x['severity']}: {x['claim'][:70]}"); continue
            r = c.post(f"{sb}/rest/v1/rpc/edit_content_card", headers=h, json={
                "p_block_id": x["block_id"], "p_card_index": x["card_index"],
                "p_before": x["fix"]["before"], "p_after": x["fix"]["after"], "p_editor": a.editor})
            if r.status_code == 409 or "PT409" in r.text:
                print(f"  ! {x['id']}: card changed since the snapshot — skipped"); continue
            r.raise_for_status()
            applied[x["id"]] = r.json()                    # content_edits.id, for undo
            print(f"  ✓ {x['id']} → edit {applied[x['id']]}")
    if not a.dry_run:
        with open(os.path.join(QA, f"{a.nat_id}.json"), "w", encoding="utf-8") as f:
            json.dump(qa, f, ensure_ascii=False, indent=1)
    skipped = [x for x in qa["findings"] if x["apply"] not in wanted]
    print(f"{len(todo)} to apply{' (dry run)' if a.dry_run else ''} · {len(skipped)} left for review/none")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("checklist"); p.add_argument("nat_id"); p.add_argument("--modes", nargs="*")
    p.set_defaults(fn=cmd_checklist)
    p = sp.add_parser("lint"); p.add_argument("nat_id"); p.add_argument("--only", nargs="*")
    p.set_defaults(fn=cmd_lint)
    p = sp.add_parser("validate"); p.add_argument("nat_ids", nargs="*"); p.set_defaults(fn=cmd_validate)
    p = sp.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("apply"); p.add_argument("nat_id"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--editor", help="user_profiles.id recorded as the editor (default: none)")
    p.add_argument("--include-review", action="store_true", help="also apply findings marked apply=review")
    p.set_defaults(fn=cmd_apply)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
