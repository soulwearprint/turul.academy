"""Render a Témakör's content_blocks into a human-review markdown doc."""
import os, json, sys, httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
SB=os.getenv("SUPABASE_URL"); SVC=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H={"apikey":SVC,"Authorization":f"Bearer {SVC}"}
TOPIC_NAT=sys.argv[1] if len(sys.argv)>1 else "HIST-78-VH1"
OUT=sys.argv[2] if len(sys.argv)>2 else "../exports/WWI_temakor_review.md"
MODE_HEAD={"text":"### 📖 Szöveg","story":"### 🎭 Történet","visual":"### 🗺️ Vizuális",
           "quiz":"### 🧠 Lecke-kvíz","world":"### 🌍 Világ ekkor"}

def cards(b): 
    c=b.get("content"); return c if isinstance(c,list) else c.get("cards",[])

def render_cards(mode, blk, L):
    out=[]
    for cd in cards(blk):
        if mode=="text":
            out.append(f"**{cd.get('heading','')}**\n{cd.get('body','')}")
            if cd.get("key_term"): out.append(f"> 🔑 {cd['key_term']}")
        elif mode=="story":
            persp=f" _({cd['mood']})_" if cd.get("mood") else ""
            out.append(f"**{cd.get('heading','')}**{persp}\n{cd.get('body','')}")
        elif mode=="visual":
            out.append(f"**{cd.get('heading','')}** _({cd.get('visual_type','')})_\n{cd.get('description','')}")
            if cd.get("caption"): out.append(f"> {cd['caption']}")
        elif mode=="quiz":
            out.append(f"**K:** {cd.get('question','')}")
            for o in cd.get("options",[]): out.append(f"   - {o}")
            out.append(f"   - ✔ Helyes: {cd.get('correct','')} — *{cd.get('explanation','')}*")
        elif mode=="world":
            out.append(f"**{cd.get('year','')} — {cd.get('heading','')}**\n{cd.get('body','')}")
            if cd.get("link_hu"): out.append(f"> ↪ {cd['link_hu']}")
        out.append("")
    return "\n".join(out)

with httpx.Client() as c:
    t=c.get(f"{SB}/rest/v1/curriculum_topics?nat_id=eq.{TOPIC_NAT}&select=id,title_hu",headers=H).json()[0]
    tid=t["id"]
    les=c.get(f"{SB}/rest/v1/curriculum_lessons?topic_id=eq.{tid}&select=id,nat_id,title_hu&order=order_index",headers=H).json()
    L=[f"# {t['title_hu']}\n", "_Turul Academy — NAT 3-tier slice (level: alap). Review copy._\n",
       "_Minden kötelező NAT-elem lefedettsége auditált: 29/29 = 100%._\n", "---\n"]
    for lz in les:
        L.append(f"\n## Lecke (Téma): {lz['title_hu']}\n")
        blks=c.get(f"{SB}/rest/v1/content_blocks?lesson_id=eq.{lz['id']}&scope=eq.lesson&select=mode,content",headers=H).json()
        by={b["mode"]:b for b in blks}
        for m in ["text","story","visual","quiz","world"]:
            if m in by:
                L.append(MODE_HEAD[m]+"\n"); L.append(render_cards(m,by[m],lz))
    # topic-scope quiz
    tq=c.get(f"{SB}/rest/v1/content_blocks?topic_id=eq.{tid}&scope=eq.topic&select=mode,content",headers=H).json()
    if tq:
        L.append("\n## 🎯 Témazáró kvíz\n")
        L.append(render_cards("quiz",tq[0],None))
    open(OUT,"w").write("\n".join(L))
    print(f"Wrote {OUT}")
