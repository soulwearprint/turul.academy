"""HIST-78-VH1 · „Az első világháború, Magyarország a háborúban” — hand corrections (2026-09-29).

Found while finishing the lesson for tester feedback:
  • deep (Mesélj még!): the proof pass broke the articles („az háború”, 60×) — rewritten by hand;
    also „elkerülhetetlen volt a háború” (loaded) and a muddled Tisza card.
  • text: Hungary as the Monarchy's „gazdasági központja” (it was its main food producer),
    Tisza „a központi hatalmak mellett érvelt”, Sarajevo „elindította a feszültségeket”,
    territory loss „a trianoni békeszerződéshez vezetett” (cause and effect reversed).
  • quiz #5 „melyik város közelében” → „melyik városban”; story #3 „falunapok” (anachronism) → „búcsúk”.
Every change goes through edit_content_card (logged in content_edits, undoable from the queue).
Run from backend/:  python3 ../content/fixes/hist_78_vh1_lesson1_2026_09.py [--dry-run]
"""
import json, sys, urllib.request

LESSON = '5b3c752f-1a0a-4289-bb68-db0002cedfe7'

TEXT = {
 0: {'body': 'Az első világháború 1914 és 1918 között zajlott, és addig a világ legnagyobb háborúja volt. A nagyhatalmak két táborra oszlottak: az antantra és a központi hatalmakra. Magyarország az Osztrák–Magyar Monarchia részeként a központi hatalmak oldalán harcolt. A háború politikai, társadalmi és gazdasági következményei mélyen érintették az országot.'},
 1: {'body': 'A háború elején mindkét fél gyors győzelemre számított, de a nyugati fronton hamar állóháború alakult ki: a katonák lövészárkokban, hónapokig ugyanazon a vonalon harcoltak. Az olasz fronton, az Isonzó mentén — például a Doberdón — magyar katonák ezrei harcoltak nehéz körülmények között. A hadsereg ellátása a hátország feladata volt. Magyarország a Monarchia legfontosabb élelmiszer-termelő területe volt, ezért nagy szerepe volt a katonák ellátásában.'},
 2: {'body': 'Tisza István 1913 és 1917 között Magyarország miniszterelnöke volt. 1914 júliusában eleinte ellenezte a Szerbia elleni háborút: attól tartott, hogy Románia megtámadja Erdélyt, és hogy a Monarchia újabb szláv lakosságú területekkel gyengülne. Végül mégis beleegyezett a hadüzenetbe, és a háború alatt keményen irányította a magyar kormányt. 1917-ben le kellett mondania, 1918 októberében pedig meggyilkolták.'},
 3: {'body': '1914. június 28-án Szarajevóban, Bosznia fővárosában egy boszniai szerb diák, Gavrilo Princip lelőtte Ferenc Ferdinánd trónörököst és feleségét. A Monarchia Szerbiát tette felelőssé, és ultimátumot küldött neki. Mivel Szerbia nem fogadta el minden pontját, a Monarchia július 28-án hadat üzent. A szövetségi rendszerek miatt néhány nap alatt a többi nagyhatalom is hadba lépett.'},
 4: {'body': 'A háborút a központi hatalmak elvesztették, és a Monarchia 1918 őszén felbomlott. Magyarország 1920-ban kénytelen volt aláírni a trianoni békediktátumot, amely területének mintegy kétharmadát a szomszédos államokhoz csatolta; több mint hárommillió magyar került a határokon túlra. A háború és a területvesztés sebei mélyen hatottak a magyar társadalomra és politikára.',
     'key_term': 'trianoni békediktátum'},
}

DEEP = {
 0: {'heading': 'Miért lett világháború egy helyi konfliktusból?',
     'body': 'A háború előtt a nagyhatalmak között erős volt a versengés: a gyarmatokért, a piacokért, a hadseregek és a flották fejlesztéséért. Az egyes népek nemzeti törekvései — például a délszlávoké a Balkánon — újabb feszültségeket okoztak. A nagyhatalmak szövetségi rendszerekbe tömörültek: a hármas szövetségbe és az antantba. Ezért amikor a Monarchia hadat üzent Szerbiának, egymás után léptek be a szövetségesek is, és a helyi háborúból néhány nap alatt európai, majd világháború lett.',
     'did_you_know': 'A kortársak „Nagy Háborúnak” nevezték — akkor még senki sem tudta, hogy lesz második világháború is.',
     'think': 'Miért lehet veszélyes, ha egy kis konfliktusba a szövetségek miatt nagyhatalmak is belesodródnak?',
     'think_answer': 'Mert egy helyi vita így gyorsan sok országra terjedhet: ha az egyik fél szövetségese belép, a másik fél szövetségesei is belépnek, és a háború egyre nagyobb lesz.'},
 1: {'heading': 'A hátország a háborúban',
     'body': 'A frontokon harcoló milliók ellátásához az egész ország munkájára szükség volt. A gyárak fegyvert, lőszert és felszerelést gyártottak, a falvakban élelmiszert termeltek a hadseregnek. A frontra vonult férfiak helyén sok nő dolgozott a gyárakban, a földeken és a hivatalokban. Az élelmiszer egyre kevesebb lett: bevezették a jegyrendszert, a lisztet és a kenyeret csak jegyre lehetett kapni.',
     'did_you_know': 'A jegyrendszer idején a kenyérért gyakran órákig kellett sorban állni.',
     'think': 'Mi történik egy hadsereggel, ha a hátország már nem tudja ellátni élelemmel és lőszerrel?',
     'think_answer': 'A katonák éheznek, nem tudnak jól harcolni, és egyre kevésbé bíznak a vezetésben. A háború végén a Monarchia hadserege részben ezért is bomlott fel.'},
 2: {'heading': 'Tisza István dilemmája',
     'body': '1914 júliusában a Monarchia vezetői közül kezdetben egyedül Tisza István ellenezte a Szerbia elleni háborút. Két dologtól tartott: hogy Románia megtámadja Erdélyt, és hogy egy győzelem után a Monarchia újabb szláv lakosságú területeket kap, ami gyengítené a magyarság helyzetét. Végül azzal a feltétellel egyezett bele a háborúba, hogy a Monarchia nem csatol el szerb területeket. 1917-ben, a választójogról folyó vitában IV. Károly lemondásra kényszerítette.',
     'did_you_know': 'Tiszát 1918. október 31-én, az őszirózsás forradalom napján katonák lőtték le budapesti otthonában.',
     'think': 'Mit tehet egy vezető, ha rossznak tart egy döntést, de a szövetségesei és a társai mind mellette vannak?',
     'think_answer': 'Érvelhet, feltételeket szabhat, vagy lemondhat. Tisza feltételt szabott — ne csatoljanak el szerb területeket —, de végül beleegyezett a háborúba.'},
 3: {'heading': 'Szarajevó: egy nap, amely megváltoztatta a világot',
     'body': 'Ferenc Ferdinánd trónörökös 1914 júniusában hadgyakorlat miatt látogatott Boszniába. Június 28-án a merénylők közül először egyikük bombát dobott az autójára, de az a mögöttük haladó kocsinál robbant. Később a trónörökös autója rossz utcába fordult, és megállt — éppen ott, ahol Gavrilo Princip állt. Két lövése megölte a trónörököst és feleségét, Chotek Zsófiát.',
     'did_you_know': 'Princip a merénylet idején még nem volt 20 éves, ezért nem ítélhették halálra: 20 év börtönt kapott, és 1918-ban a börtönben halt meg.',
     'think': 'Ha aznap nem fordul rossz utcába az autó, elkerülhető lett volna a háború?',
     'think_answer': 'Ezt senki sem tudhatja biztosan. A nagyhatalmak közötti feszültségek már nagyok voltak, így egy másik válság is kirobbanthatta volna a háborút. A merénylet inkább szikra volt, mint egyetlen ok.'},
 4: {'heading': 'Trianon a mindennapokban',
     'body': 'A trianoni békediktátum után az új határok sok helyen falvakat, birtokokat, vasútvonalakat vágtak ketté. Több mint hárommillió magyar került a szomszédos államokba: Csehszlovákiába, Romániába, a Szerb–Horvát–Szlovén Királyságba és Ausztriába. Sokan elvesztették az állásukat, és százezrek menekültek az új Magyarország területére. Az ország elvesztette erdői, bányái és nyersanyagforrásai nagy részét is.',
     'did_you_know': 'Azokat a menekülteket, akik évekig vasúti kocsikban laktak a pályaudvarokon, „vagonlakóknak” nevezték.',
     'think': 'Mit jelenthetett egy családnak, ha a rokonai egyik napról a másikra egy másik ország állampolgárai lettek?',
     'think_answer': 'Nehezebb lett a találkozás (útlevél, határátlépés), a rokonoknak más nyelvű iskolákba és hivatalokba kellett járniuk, és sokan attól féltek, hogy elveszítik a magyar nyelvüket és kultúrájukat.'},
}

QUIZ = {4: {'question': 'Melyik városban történt a merénylet, amely kirobbantotta az első világháborút?'}}
STORY = {2: {'body': 'A háború alatt a gyermekek is megérezték a felnőttek aggodalmait. Az iskolákban a tanárok próbálták enyhíteni a feszültséget, de a háborús események a tanórákon is megjelentek. A gyerekek háborúsat játszottak, és sokszor a szüleik munkáját is segítették. A közösségi alkalmak, például a búcsúk, fontos szerepet játszottak abban, hogy a gyerekek ne veszítsék el a reményt és a vidámságot.'}}


def main(dry):
    env = {}
    for line in open('.env'):
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1); env[k.strip()] = v.strip().strip('"').strip("'")
    sb, key = env['SUPABASE_URL'].rstrip('/'), env['SUPABASE_SERVICE_ROLE_KEY']
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    def call(method, path, body=None):
        r = urllib.request.Request(sb + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(r) as resp:
            raw = resp.read(); return json.loads(raw) if raw else None
    blocks = {b['mode']: b for b in call('GET', f'/rest/v1/content_blocks?lesson_id=eq.{LESSON}&mode=in.(text,deep,quiz,story)&select=id,mode,content')}
    for mode, changes in (('text', TEXT), ('deep', DEEP), ('quiz', QUIZ), ('story', STORY)):
        b = blocks[mode]
        for i, ch in changes.items():
            before = b['content'][i]
            after = dict(before, **ch)
            assert set(after) == set(before), (mode, i, set(after) ^ set(before))
            if dry:
                print(mode, i, [k for k in ch if before.get(k) != ch[k]]); continue
            eid = call('POST', '/rest/v1/rpc/edit_content_card', {'p_block_id': b['id'], 'p_card_index': i,
                       'p_before': before, 'p_after': after, 'p_editor': None})
            print(mode, i, 'edit', eid)
    if not dry:
        call('PATCH', f"/rest/v1/content_blocks?id=eq.{blocks['deep']['id']}", {'is_active': True, 'review_status': 'approved'})
        print('deep block activated')

if __name__ == '__main__':
    main('--dry-run' in sys.argv)
