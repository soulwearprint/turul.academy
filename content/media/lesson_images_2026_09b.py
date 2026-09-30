"""Photos for PHYS-78-03 lessons 2–4 (2026-09-30), sourced from Wikimedia Commons (licence + author
checked on each file page; see manifest.json). Follows lesson_images_2026_09.py: each card is written
through the edit_content_card RPC, so every change is in content_edits and can be undone from the review queue.

  python3 ../media/lesson_images_2026_09b.py --batch 3 --dry-run   # from backend/ (reads .env or the environment)
  python3 ../media/lesson_images_2026_09b.py --batch 3             # uploads staged files, then edits the cards
Batches 1 (5 photos), 2 (5 photos) and 3 (crash-test photo swap + 6 own drawings) are all applied; do not re-run them.

Staged files: content/media/staging/PHYS-78-03/<name>.webp|.svg (git-ignored; the photos are resized copies
of Commons thumbnails, the SVGs come from make_physics_diagrams_2.py). Upload target is the public Storage
bucket `content-media`; cards store the path, never a hotlink.
The Hungarian card texts are new — a teacher should read them (Content_Sourcing_Policy §6).
"""
import json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(HERE, 'staging', 'PHYS-78-03')
C = 'https://commons.wikimedia.org/wiki/File:'
U = 'content-media/phys/utido/'
B = 'content-media/phys/biztonsag/'
E = 'content-media/phys/erok/'

# block id -> {card index: (expected heading, staged file name, storage path, card fields)}
BATCH1 = {  # applied 2026-09-30 morning (first 5 photos)
  'f3e4a797-c1af-4d18-acb7-a0715f0b40fc': {  # Út és idő kiszámítása
    5: ('Sebesség mérése', 'sebessegkijelzo-nagykovacsi.webp', U + 'sebessegkijelzo-nagykovacsi.webp', dict(
        description='Sok úton kijelző mutatja az arra haladók pillanatnyi sebességét. Egy radar méri a jármű sebességét, a kijelző pedig km/h-ban kiírja — itt 52 km/h-t, és a „LASSÍTS!” felirat figyelmeztet. A radar a járműről visszavert rádióhullámok megváltozásából (Doppler-hatás) számítja ki a sebességet.',
        caption='Sebességkijelző radarral, Nagykovácsi (Pest vármegye)',
        image={'src': U + 'sebessegkijelzo-nagykovacsi.webp', 'alt': 'Út menti kijelző napelemmel: „SEBESSÉGE: 52 km/h, LASSÍTS!”',
               'credit': 'Globetrotter19 · CC BY-SA 3.0',
               'source': C + 'Speed_radar_with_solar_panel,_Nagykovácsi_Road,_2020_Nagykovácsi.jpg'})),
  },
  '9fd5a9a0-12e1-45dc-b8ec-a5cdd3078a86': {  # Erők és gyorsulás vizsgálata
    1: ('Nehézségi erő és nehézségi gyorsulás', 'toll-es-kalapacs-hold.webp', E + 'toll-es-kalapacs-hold.webp', dict(
        description='A nehézségi erő F = m · g, ahol g a nehézségi gyorsulás (a Földön kb. 9,81 m/s²): a szabadon eső test sebessége másodpercenként kb. 9,81 m/s-mal nő. A levegőben a légellenállás miatt egy toll lassabban esik, mint egy kalapács. Légüres térben nincs légellenállás, ezért minden test egyformán gyorsul. Ezt mutatta meg David Scott, az Apollo–15 parancsnoka 1971. augusztus 2-án a Holdon: egyszerre ejtett el egy kalapácsot és egy tollat, és egyszerre értek földet. A Holdon a nehézségi gyorsulás a földinek kb. a hatoda.',
        caption='A toll és a kalapács a Hold felszínén, a kísérlet után (Apollo–15, 1971)',
        image={'src': E + 'toll-es-kalapacs-hold.webp', 'alt': 'Holdpor és aranyszínű fólia a leszállóegység alatt; a porban egy toll és egy kalapács',
               'credit': 'NASA · közkincs', 'source': C + 'Apollo_15_F%26H.jpg'})),
  },
  '988c7f19-cdc8-4113-9e91-223ce3afbd86': {  # Közlekedési eszközök biztonsági rendszerei
    0: ('Önvezérelt autó működési elve', 'lidar.webp', B + 'lidar.webp', dict(
        description='Az önvezérelt autók „szemei” az érzékelők: kamerák, radarok és lidarok. A lidar lézerimpulzusokat bocsát ki, és méri, mennyi idő alatt verődnek vissza. A távolságot ebből számolja ki: a fény útja oda-vissza az idő és a fénysebesség szorzata, a távolság ennek a fele. A forgó lidar így másodpercenként sokszor felméri a környezetet, és háromdimenziós térképet készít róla. A képen egy önvezető kutatóautó tetején forgó, 64 lézersugaras lidar látható.',
        caption='Forgó lidar egy önvezető kutatóautó tetején',
        image={'src': B + 'lidar.webp', 'alt': 'Forgó lidar-érzékelő közelről, alján lézerfigyelmeztető címkével',
               'credit': 'Steve Jurvetson · CC BY 2.0', 'source': C + 'Velodyne_High-Def_LIDAR.jpg'})),
    1: ('Légzsák működése', 'legzsak-toresteszt.webp', B + 'legzsak-toresteszt.webp', dict(
        description='Ütközéskor az autó hirtelen lelassul, az utas teste viszont a tehetetlensége miatt tovább mozogna előre. Az érzékelők jelzésére a légzsák a másodperc törtrésze alatt felfújódik, és lágyabban fékezi az utas fejét és mellkasát, így kisebb erő hat rá. A képen egy 40 km/h-s törésteszt látható: az első ülésen öv és légzsák, a hátsó ülésen öv vagy semmi nem védi a próbabábút.',
        caption='Törésteszt 40 km/h-val: próbabábúk övvel és légzsákkal',
        image={'src': B + 'legzsak-toresteszt.webp', 'alt': 'Oldalnézet egy törésteszt közben kettévágott autóból: az első próbabábú előtt felfújódott légzsák',
               'credit': 'Transport for NSW · CC BY-SA 4.0', 'source': C + 'Crash-test-with-airbag-and-safty-belt.jpg'})),
    2: ('Biztonsági öv működése', 'biztonsagi-ov.webp', B + 'biztonsagi-ov.webp', dict(
        description='A háromponti biztonsági öv a vállon és a mellkason, illetve a medencén át fogja meg a testet, vagyis a legerősebb részeken. Ütközéskor az öv az autóval együtt lassítja az utast. Nélküle az utas a tehetetlensége miatt az ütközés előtti sebességével repülne tovább előre, amíg neki nem csapódik a kormánynak, a műszerfalnak vagy a szélvédőnek.',
        caption='Próbabábú háromponti biztonsági övvel',
        image={'src': B + 'biztonsagi-ov.webp', 'alt': 'Sárga próbabábú az ülésben, vállon és medencén átfutó háromponti övvel',
               'credit': 'ITU Pictures · CC BY 2.0', 'source': C + 'Crash_test_dummy_with_three-point_seat_belt_(cropped).jpg'})),
  },
}


BATCH2 = {  # applied 2026-09-30 (second round)
  'f3e4a797-c1af-4d18-acb7-a0715f0b40fc': {  # Út és idő kiszámítása
    1: ('Sebesség', 'sebessegmero-bmw-r26.webp', U + 'sebessegmero-bmw-r26.webp', dict(
        description='A sebesség megmutatja, hogy a test mennyi utat tesz meg egységnyi idő alatt: v = s : t. A járművek sebességmérője a pillanatnyi sebességet mutatja km/h-ban, a kilométer-számláló pedig a megtett utat adja össze. A képen egy 1960-as BMW motorkerékpár sebességmérője látható, amelynek skálája 0-tól 140 km/h-ig tart.',
        caption='Sebességmérő és kilométer-számláló egy 1960-as motorkerékpáron',
        image={'src': U + 'sebessegmero-bmw-r26.webp', 'alt': 'Kör alakú sebességmérő fekete számlappal, 0–140 km/h skálával, közepén a kilométer-számlálóval',
               'credit': 'Palauenc05 · CC BY-SA 4.0', 'source': C + 'BMW_R26_1960_Tacho.jpg'})),
    3: ('Utazásból hátralévő idő', 'utjelzo-tabla.webp', U + 'utjelzo-tabla.webp', dict(
        description='Az útjelző táblák a városok hátralévő távolságát mutatják. Ha ismerjük a távolságot és a várható átlagsebességet, kiszámolhatjuk a hátralévő időt: t = s : v. Például ha a tábla szerint Hamiltonig még 54 km van hátra, és átlagosan 90 km/h-val haladunk, akkor t = 54 km : 90 km/h = 0,6 óra, vagyis 36 perc. A képen egy tasmaniai (Ausztrália) autópálya-tábla látható.',
        caption='Útjelző tábla: a városok távolsága kilométerben (Tasmania, Ausztrália)',
        image={'src': U + 'utjelzo-tabla.webp', 'alt': 'Zöld útjelző tábla városnevekkel és a hozzájuk tartozó távolságokkal kilométerben',
               'credit': 'Chuq · CC BY-SA 4.0', 'source': C + 'Distance_road_sign,_Lyell_Highway,_Granton,_Tasmania.jpg'})),
  },
  '9fd5a9a0-12e1-45dc-b8ec-a5cdd3078a86': {  # Erők és gyorsulás vizsgálata
    4: ('Sebességváltozás fékezés során', 'fekezesi-nyomok.webp', E + 'fekezesi-nyomok.webp', dict(
        description='Fékezéskor a fékek és az út közötti súrlódási erő csökkenti az autó sebességét: az autó lassul, vagyis a gyorsulása a haladási iránnyal ellentétes. Ha a kerekek blokkolnak, a gumi csúszik az úton, és fekete fékezési nyomot hagy, mint a képen. Állandó lassulás esetén a fékút a kezdősebesség négyzetével nő: kétszer akkora sebességnél négyszer hosszabb út kell a megálláshoz.',
        caption='Fékezési nyomok az aszfalton',
        image={'src': E + 'fekezesi-nyomok.webp', 'alt': 'Fekete-fehér fénykép: íves, fekete fékezési nyomok egy kanyargós úton',
               'credit': 'Robert · CC BY-SA 3.0', 'source': C + 'Bremsspur.jpg'})),
    5: ('Sebesség mérésének eljárása', 'stopper.webp', E + 'stopper.webp', dict(
        description='A sebesség méréséhez két dolgot kell megmérni: az utat mérőszalaggal, az időt stopperrel. Ezután v = s : t. Például ha egy kerékpáros 20 m-t 4 s alatt tesz meg, a sebessége 20 m : 4 s = 5 m/s. A mérés akkor pontos, ha a stoppert pontosan indítjuk és állítjuk meg, és a mérést többször megismételjük.',
        caption='Mechanikus stopper',
        image={'src': E + 'stopper.webp', 'alt': 'Analóg stopper számlappal, másodperc- és percmutatóval, három gombbal',
               'credit': 'R. Henrik Nilsson · CC BY 4.0', 'source': C + 'Ca_1970_mechanical_stopwatch_by_Herwins_Switzerland.jpg'})),
  },
  '988c7f19-cdc8-4113-9e91-223ce3afbd86': {  # Közlekedési eszközök biztonsági rendszerei
    3: ('Kölcsönhatás a járművek között', 'utkozes-fanak.webp', B + 'utkozes-fanak.webp', dict(
        description='Két test kölcsönhatásakor mindkettőre erő hat: az egyik test ugyanakkora erővel hat a másikra, mint az az elsőre, csak ellenkező irányban (Newton III. törvénye). Ütközéskor az autó a fára hat, a fa ugyanakkora erővel az autóra, ezért deformálódik az autó eleje. A képen egy közlekedésbiztonsági figyelemfelhívó installáció látható: egy fának 120 km/h-val ütköző autó roncsa. Minél nagyobb az ütközés előtti sebesség, annál nagyobb az autó mozgási energiája, és annál nagyobb a károsodás.',
        caption='Közlekedésbiztonsági installáció Frankfurtban: autó, amely 120 km/h-val fának ütközött',
        image={'src': B + 'utkozes-fanak.webp', 'alt': 'Összeroncsolódott autó egy fatörzs körül, éjszakai fényekkel',
               'credit': 'Norbert Nagel · CC BY-SA 3.0', 'source': C + 'Car_accident_memorial_-_Unfall_Denk_mal_-_Frankfurt_-_Germany_-_01.jpg'})),
  },
}

OWN = 'Ábra: Turul'
BATCH3 = {  # applied 2026-09-30 (third round): crash-test photo replaces the tree-crash photo; 6 own drawings fill the text-only cards
  'f3e4a797-c1af-4d18-acb7-a0715f0b40fc': {  # Út és idő kiszámítása
    2: ('Átlagsebesség', 'atlagsebesseg-ket-szakasz.svg', U + 'atlagsebesseg-ket-szakasz.svg', dict(
        description='Az átlagsebesség az összes megtett út és az összes eltelt idő hányadosa. Példa: egy autó az első szakaszon 40 km-t tesz meg fél óra alatt (80 km/h), a másodikon 60 km-t másfél óra alatt (40 km/h). Az egész úton 100 km-t haladt 2 óra alatt, ezért az átlagsebessége 100 km : 2 h = 50 km/h. Ez nem a két sebesség számtani közepe (az 60 km/h lenne), mert az autó a lassabb szakaszon több időt töltött.',
        caption='Átlagsebesség: v = s : t, ahol s az összes megtett út, t az összes eltelt idő.',
        image={'src': U + 'atlagsebesseg-ket-szakasz.svg', 'alt': 'Kétszakaszos út: 40 km 0,5 óra alatt (80 km/h) és 60 km 1,5 óra alatt (40 km/h); összesen 100 km 2 óra alatt, az átlagsebesség 50 km/h', 'credit': OWN})),
    4: ('Közlekedéstervezés', 'utvonaltervezo-kepernyo.svg', U + 'utvonaltervezo-kepernyo.svg', dict(
        description='Az útvonaltervező alkalmazások a távolságból és a várható átlagsebességből számolják ki az utazási időt: t = s : v. A rajzon az A és a B pont között 96 km az út, a várható átlagsebesség 80 km/h, így t = 96 km : 80 km/h = 1,2 óra, vagyis 1 óra 12 perc (0,2 óra = 0,2 · 60 perc = 12 perc). Forgalmas úton az átlagsebesség kisebb, ezért az érkezési idő is változhat. A kép szemléltető rajz, nem egy valódi alkalmazás képernyőképe.',
        caption='Szemléltető rajz egy útvonaltervezőről (nem valódi alkalmazás)',
        visual_type='szemléltető rajz',
        image={'src': U + 'utvonaltervezo-kepernyo.svg', 'alt': 'Telefonképernyő térképpel: az A pontból a B pontba vezető kék útvonal, alatta 1 óra 12 perc, 96 km, átlagsebesség 80 km/h', 'credit': OWN})),
    6: ('Sebesség és út kapcsolata', 'sebesseg-ido-terulet.svg', U + 'sebesseg-ido-terulet.svg', dict(
        description='A sebesség–idő grafikon vízszintes tengelyén az idő, függőleges tengelyén a sebesség látható. Állandó sebességnél — itt 20 m/s — a grafikon vízszintes egyenes. A vonal alatti téglalap területe a megtett út: s = v · t = 20 m/s · 10 s = 200 m. Ha a sebesség változik, akkor is a grafikon alatti terület adja a megtett utat.',
        caption='A sebesség–idő grafikon alatti terület a megtett út.',
        image={'src': U + 'sebesseg-ido-terulet.svg', 'alt': 'Sebesség–idő grafikon: vízszintes vonal 20 m/s-nál 0-tól 10 s-ig, alatta kék téglalap; a területe 200 m', 'credit': OWN})),
    7: ('Idő és távolság', 'ido-es-tavolsag.svg', U + 'ido-es-tavolsag.svg', dict(
        description='Ugyanazt a távolságot nagyobb sebességgel kevesebb idő alatt tesszük meg: t = s : v. A 120 km-es út 30 km/h-val 4 órát, 60 km/h-val 2 órát, 90 km/h-val 1 óra 20 percet, 120 km/h-val pedig 1 órát vesz igénybe. Kétszer akkora sebességnél feleannyi idő kell hozzá.',
        caption='Ugyanaz a 120 km: minél nagyobb a sebesség, annál kevesebb idő kell hozzá.',
        image={'src': U + 'ido-es-tavolsag.svg', 'alt': 'Vízszintes oszlopdiagram: 120 km megtételéhez 30 km/h-val 4 óra, 60 km/h-val 2 óra, 90 km/h-val 1 óra 20 perc, 120 km/h-val 1 óra kell', 'credit': OWN})),
  },
  '9fd5a9a0-12e1-45dc-b8ec-a5cdd3078a86': {  # Erők és gyorsulás vizsgálata
    2: ('Newton 2. törvénye', 'newton-2-torveny.svg', E + 'newton-2-torveny.svg', dict(
        description='Newton második törvénye: egy test gyorsulása egyenesen arányos a rá ható eredő erővel, és fordítottan arányos a tömegével: a = F : m, vagyis F = m · a. Az ábrán — a súrlódást elhanyagolva — mindkét kocsira ugyanakkora, 2 N erő hat. Az 1 kg-os kocsi gyorsulása 2 N : 1 kg = 2 m/s², a 2 kg-osé csak 2 N : 2 kg = 1 m/s². Kétszer akkora tömegű testet ugyanakkora erő feleakkora gyorsulással mozgat. (1 N = 1 kg · m/s².)',
        caption='Newton 2. törvénye: az erő, a tömeg és a gyorsulás kapcsolata.',
        image={'src': E + 'newton-2-torveny.svg', 'alt': 'Két kocsi: az 1 kg-os 2 N erő hatására 2 m/s²-tel, a 2 kg-os ugyanakkora erő hatására 1 m/s²-tel gyorsul', 'credit': OWN})),
  },
  '988c7f19-cdc8-4113-9e91-223ce3afbd86': {  # Közlekedési eszközök biztonsági rendszerei
    3: ('Kölcsönhatás a járművek között', 'utkozes-toresteszt.webp', B + 'utkozes-toresteszt.webp', dict(
        description='Két test kölcsönhatásakor mindkettőre erő hat: az egyik test ugyanakkora erővel hat a másikra, mint az az elsőre, csak ellenkező irányban (Newton III. törvénye). Ütközéskor az autó az akadályra hat, az akadály ugyanakkora erővel az autóra, ezért deformálódik az autó eleje. A képen egy törésteszten átesett autó látható: a fájl leírása szerint szemből ütköztették 35 mph-val, ami kb. 56 km/h. A törésteszteken azt vizsgálják, hogyan védi az utasokat a karosszéria, az öv és a légzsák. Minél nagyobb az ütközés előtti sebesség, annál nagyobb az autó mozgási energiája, és annál nagyobb a károsodás.',
        caption='Törésteszten átesett Corvette egy kiállításon (szemből, 35 mph ≈ 56 km/h)',
        image={'src': B + 'utkozes-toresteszt.webp', 'alt': 'Elöl összegyűrődött fehér sportautó egy kiállítási térben, a háttérben monitorokon a törésteszt felvételei',
               'credit': 'JaseMan · CC BY 2.0', 'source': C + 'Corvette_Crash_Tester_(3695903512).jpg'})),
    4: ('Mozgás elemzése applikációval', 'mozgaselemzo-kepernyo.svg', B + 'mozgaselemzo-kepernyo.svg', dict(
        description='A mozgáselemző alkalmazások (például a futóappok és a sportórák) mérik az időt és a megtett utat, ebből kiszámolják az átlagsebességet, és gyakran sebesség–idő grafikont is rajzolnak. A rajzon egy kocogás adatai láthatók: 8 perc 20 s (= 500 s) alatt 1,25 km (= 1250 m) út, így az átlagsebesség 1250 m : 500 s = 2,5 m/s, ami 2,5 · 3,6 = 9 km/h. A grafikon a pillanatnyi sebesség ingadozását mutatja, a szaggatott vonal az átlagsebességet. A kép szemléltető rajz, nem egy valódi alkalmazás képernyőképe.',
        caption='Szemléltető rajz egy mozgáselemző alkalmazásról (nem valódi alkalmazás)',
        visual_type='szemléltető rajz',
        image={'src': B + 'mozgaselemzo-kepernyo.svg', 'alt': 'Telefonképernyő: idő 8 perc 20 s, megtett út 1,25 km, átlagsebesség 9,0 km/h, alatta sebesség–idő grafikon szaggatott átlagvonallal', 'credit': OWN})),
  },
}

BATCHES = {'1': BATCH1, '2': BATCH2, '3': BATCH3}


def main(dry, batch):
    from PIL import Image
    env = dict(os.environ)  # or backend/.env
    if os.path.exists('.env'):
        for line in open('.env'):
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1); env[k.strip()] = v.strip().strip('"').strip("'")
    sb, key = env['SUPABASE_URL'].rstrip('/'), env['SUPABASE_SERVICE_ROLE_KEY']
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    def call(method, path, body=None, headers=None, raw=None):
        r = urllib.request.Request(sb + path, method=method, headers=headers or h,
                                   data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None))
        with urllib.request.urlopen(r) as resp:
            b = resp.read(); return json.loads(b) if b else None
    for block, cards_ch in BATCHES[batch].items():
        cards = call('GET', f'/rest/v1/content_blocks?id=eq.{block}&select=content')[0]['content']
        for i, (heading, fname, path, ch) in cards_ch.items():
            before = cards[i]
            assert before['heading'] == heading, f'{block[:8]} card {i}: expected {heading!r}, found {before["heading"]!r}'
            f = os.path.join(STAGING, fname)
            if fname.endswith('.svg'):  # size from the viewBox; PIL cannot open SVG
                w, hh = (int(float(v)) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', open(f, encoding='utf-8').read()).groups())
                ctype = 'image/svg+xml'
            else:
                w, hh = Image.open(f).size
                ctype = 'image/webp'
            ch = dict(ch, image=dict(ch['image'], w=w, h=hh))
            after = dict(before, **ch)
            if dry:
                print(block[:8], i, heading, '→ image', path, f'{w}x{hh}'); continue
            call('POST', '/storage/v1/object/' + path, raw=open(f, 'rb').read(),
                 headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': ctype, 'x-upsert': 'true'})
            eid = call('POST', '/rest/v1/rpc/edit_content_card', {'p_block_id': block, 'p_card_index': i,
                       'p_before': before, 'p_after': after, 'p_editor': None})
            print(block[:8], i, heading, 'uploaded + edit', eid)

if __name__ == '__main__':
    batch = sys.argv[sys.argv.index('--batch') + 1] if '--batch' in sys.argv else '3'
    main('--dry-run' in sys.argv, batch)
