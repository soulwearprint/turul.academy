"""Photos for PHYS-78-03 lessons 2–4 (2026-09-30), sourced from Wikimedia Commons (licence + author
checked on each file page; see manifest.json). Follows lesson_images_2026_09.py: each card is written
through the edit_content_card RPC, so every change is in content_edits and can be undone from the review queue.

  python3 ../media/lesson_images_2026_09b.py --dry-run      # from backend/ (reads .env)
  python3 ../media/lesson_images_2026_09b.py                # uploads staged files, then edits the cards

Staged files: content/media/staging/PHYS-78-03/<name>.webp (resized copies, git-ignored). Upload target is
the public Storage bucket `content-media`; cards store the path, never a hotlink.
The Hungarian card texts are new — a teacher should read them (Content_Sourcing_Policy §6).
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(HERE, 'staging', 'PHYS-78-03')
C = 'https://commons.wikimedia.org/wiki/File:'
U = 'content-media/phys/utido/'
B = 'content-media/phys/biztonsag/'
E = 'content-media/phys/erok/'

# block id -> {card index: (expected heading, staged file name, storage path, card fields)}
BLOCKS = {
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


def main(dry):
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
    for block, cards_ch in BLOCKS.items():
        cards = call('GET', f'/rest/v1/content_blocks?id=eq.{block}&select=content')[0]['content']
        for i, (heading, fname, path, ch) in cards_ch.items():
            before = cards[i]
            assert before['heading'] == heading, f'{block[:8]} card {i}: expected {heading!r}, found {before["heading"]!r}'
            f = os.path.join(STAGING, fname)
            w, hh = Image.open(f).size
            ch = dict(ch, image=dict(ch['image'], w=w, h=hh))
            after = dict(before, **ch)
            if dry:
                print(block[:8], i, heading, '→ image', path, f'{w}x{hh}'); continue
            call('POST', '/storage/v1/object/' + path, raw=open(f, 'rb').read(),
                 headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'image/webp', 'x-upsert': 'true'})
            eid = call('POST', '/rest/v1/rpc/edit_content_card', {'p_block_id': block, 'p_card_index': i,
                       'p_before': before, 'p_after': after, 'p_editor': None})
            print(block[:8], i, heading, 'uploaded + edit', eid)

if __name__ == '__main__':
    main('--dry-run' in sys.argv)
