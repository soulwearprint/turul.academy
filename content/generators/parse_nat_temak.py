"""
Second parse pass over the official NAT kerettanterv docx files.

history_nat2020.json holds the Témakör-level mandatory elements. This pass adds
the missing tier: the Témák (sub-lessons) and their Altémák under each Témakör,
which the docx encode as table rows (col0 = Téma, col1 = Altémák). Elements stay
sourced from the curated history_nat2020.json (matched by Témakör title).

Output: content/nat_curriculum/history_nat2020_temak.json
  { "<Témakör title>": {
        "school": "F"|"K", "temak": [ {"title": "...", "altemak": ["...", ...]} ],
        "elements": {"fogalmak":[...], "szemelyek":[...], "kronologia":[...], "topografia":[...]}
  }, ... }
"""
import os, json, zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(__file__)
DOCX = {"F": os.path.expanduser("~/Downloads/Tortenelem_F.docx"),
        "K": os.path.expanduser("~/Downloads/Tortenelem_K.docx")}
NAT_JSON = os.path.join(HERE, "../nat_curriculum/history_nat2020.json")
OUT = os.path.join(HERE, "../nat_curriculum/history_nat2020_temak.json")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HEADER_TEMAK = {"témák", "altémák", "fogalmak és adatok/lexikák", "fejlesztési feladatok",
                "részletes követelmények"}


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()

def _cell_lines(tc):
    return [t for t in (_ptext(p) for p in tc.iter(W + "p")) if t]


def _parse_docx(path, school):
    """Return {temakor_title: [ {title, altemak[]} ]} from one docx."""
    body = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml")).find(W + "body")
    out = {}
    last_tk = None
    for ch in list(body):
        if ch.tag == W + "p":
            t = _ptext(ch)
            if t.startswith("Témakör:"):
                last_tk = t.split("Témakör:", 1)[1].strip()
        elif ch.tag == W + "tbl" and last_tk:
            rows = ch.findall(W + "tr")
            temak = []
            for tr in rows:
                cells = tr.findall(W + "tc")
                if len(cells) != 4:
                    continue
                title = " ".join(_cell_lines(cells[0])).strip()
                if not title or title.lower() in HEADER_TEMAK:
                    continue
                altemak = _cell_lines(cells[1])
                temak.append({"title": title, "altemak": altemak})
            if temak:
                out.setdefault(last_tk, [])
                # a Témakör may span multiple tables (page breaks) -> accumulate
                out[last_tk].extend(temak)
                last_tk = None  # consume; next table needs its own heading
    return out


SCHOOL_OF = {"altalanos_iskola": "F", "gimnazium": "K"}

def _load_elements():
    """Keyed by 'school::title' since some titles repeat across F/K with different depth."""
    d = json.load(open(NAT_JSON, encoding="utf-8"))
    by_key = {}
    for section in ("altalanos_iskola", "gimnazium"):
        sc = SCHOOL_OF[section]
        for band, arr in d[section].items():
            for t in arr:
                by_key[f"{sc}::{t['temakor'].strip().lower()}"] = {
                    k: t.get(k, []) for k in ("fogalmak", "szemelyek", "kronologia", "topografia")}
    return by_key


def main():
    elements = _load_elements()
    result = {}
    for school, path in DOCX.items():
        if not os.path.exists(path):
            print(f"⚠ missing {path}"); continue
        for tk, temak in _parse_docx(path, school).items():
            title = tk.strip()
            key = f"{school}::{title}"
            el = elements.get(f"{school}::{title.lower()}")
            result[key] = {"school": school, "title": title, "temak": temak,
                           "elements": el or {"fogalmak": [], "szemelyek": [],
                                              "kronologia": [], "topografia": []},
                           "_elements_matched": el is not None}
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    matched = sum(1 for v in result.values() if v["_elements_matched"])
    print(f"Témakörök parsed: {len(result)}  (elements matched: {matched})")
    print(f"Témák total: {sum(len(v['temak']) for v in result.values())}")
    unmatched = [k for k, v in result.items() if not v["_elements_matched"]]
    if unmatched:
        print("⚠ elements NOT matched (title mismatch vs JSON):")
        for u in unmatched: print("   -", u)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
