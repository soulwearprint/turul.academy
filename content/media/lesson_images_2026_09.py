"""Images for the first two „complete” lessons (2026-09-29):
  • HIST-78-VH1 „Az első világháború, Magyarország a háborúban” — visual cards 0–7
  • PHYS-78-03  „Mozgások megfigyelése és csoportosítása”     — visual cards 0–6

Files live in the public Storage bucket `content-media` (see manifest.json for sources and
licences). Each card is written through the edit_content_card RPC, so every change is in
content_edits and can be undone from the review queue („Szerkesztések”).

Run from backend/ (reads .env):  python3 ../content/media/lesson_images_2026_09.py [--dry-run]
"""
import json, sys, urllib.request

HIST_BLOCK = 'd03a148e-3293-46dc-af01-8c64ab8f4837'
PHYS_BLOCK = '56e6d006-0a25-484a-812f-eefba274340e'
H = 'content-media/hist/elso-vilaghaboru/'
P = 'content-media/phys/mozgasok/'
C = 'https://commons.wikimedia.org/wiki/File:'
OWN = 'Ábra: Turul'

HIST = {
  0: dict(description='A háború fontos állomásai 1914 és 1918 között — Magyarország szempontjából is.',
          caption='1914–1918',
          timeline=[
            {'when': '1914. június 28.', 'what': 'Szarajevóban egy boszniai szerb diák, Gavrilo Princip lelövi Ferenc Ferdinánd trónörököst és feleségét.'},
            {'when': '1914. július 28.', 'what': 'Az Osztrák–Magyar Monarchia hadat üzen Szerbiának. A szövetségi rendszerek miatt néhány nap alatt szinte egész Európa háborúba sodródik.'},
            {'when': '1914. szeptember', 'what': 'A marne-i csatában megáll a német előrenyomulás Párizs előtt. A nyugati fronton kiépül az állóháború.'},
            {'when': '1915. május 23.', 'what': 'Olaszország hadat üzen a Monarchiának. Megnyílik az olasz front: az Isonzó mentén — Doberdónál is — sok magyar katona harcol.'},
            {'when': '1916', 'what': 'Verdun és a Somme: a nyugati front legvéresebb csatái. Augusztus 27-én Románia hadat üzen a Monarchiának, és betör Erdélybe.'},
            {'when': '1916. november 21.', 'what': 'Meghal Ferenc József. Utóda IV. Károly (osztrák császárként I. Károly).'},
            {'when': '1917', 'what': 'Áprilisban az Egyesült Államok belép a háborúba. Novemberben Oroszországban a bolsevikok átveszik a hatalmat, és Oroszország kilép a háborúból.'},
            {'when': '1918. november 3.', 'what': 'A Monarchia Padovában fegyverszünetet köt, november 11-én Németország is Compiègne-ben. Véget ér a háború.'},
          ]),
  1: dict(description='A térkép 1914 elejét mutatja: a hármas szövetség (Németország, az Osztrák–Magyar Monarchia és Olaszország) állt szemben a hármas antanttal (Franciaország, Nagy-Britannia, Oroszország). A háborúban Olaszország végül az antant oldalán harcolt, az Oszmán Birodalom és Bulgária pedig a központi hatalmakhoz csatlakozott. A nyilak a Monarchia nemzetiségeinek elszakadási törekvéseit jelzik.',
          caption='Katonai szövetségek Európában, 1914',
          image={'src': H + 'szovetsegek-1914-hu.svg', 'w': 998, 'h': 593, 'alt': 'Európa térképe 1914-ben: a hármas szövetség és a hármas antant országai',
                 'credit': 'Térkép: historicair, Fluteflute, Bibi Saint-Pol; magyarítás: Zetrs · CC BY-SA 2.5', 'source': C + 'Map_Europe_alliances_1914-hu.svg'}),
  2: dict(description='A két tábor a háború idején — Olaszország és Románia már az antant oldalán — és a fő frontok. Magyar katonák főleg a keleti fronton (Galíciában és a Kárpátokban), a szerb, az olasz (isonzói) és a román fronton harcoltak. A nyugati fronton főleg a németek álltak szemben a franciákkal és a britekkel.',
          caption='Szövetségek és fő frontok 1914–1918 között (vázlatos térkép)',
          image={'src': H + 'frontok-1914-1918-hu.svg', 'w': 998, 'h': 593, 'alt': 'Európa térképe 1914–1918: a központi hatalmak, az antant és a fő frontvonalak',
                 'credit': 'Alaptérkép: historicair, Augusta 89 (CC BY-SA 3.0); magyarítás, frontvonalak: Turul · CC BY-SA 3.0',
                 'source': C + 'Alliances_militaires_en_Europe_1914-1918-fr.svg'}),
  3: dict(description='Az állóháborúban a katonák hónapokig ugyanazokban a földbe ásott lövészárkokban éltek és harcoltak. Az árkokat szögesdrót és géppuskák védték, ezért a támadók óriási veszteségek árán is gyakran csak néhány száz métert nyertek. A fényképen osztrák–magyar katonák egy havas lövészárokban, 1915-ben.',
          caption='Osztrák–magyar katonák lövészárokban, 1915',
          image={'src': H + 'loveszarok-fortepan-52211.webp', 'w': 1400, 'h': 831, 'alt': 'Katonák puskával egy havas lövészárokban',
                 'credit': 'Fortepan / Komlós Péter · közkincs', 'source': C + 'Lövészárok._Fortepan_52211.jpg'}),
  4: dict(description='A háborút a hátország is fizette. Az állam hadikölcsönt kért a lakosságtól, a gyárak fegyvert és lőszert gyártottak, a frontra vonult férfiak helyén sokszor nők dolgoztak, az élelmiszert pedig jegyre adták. A plakátot a Budapesti Kereskedelmi és Iparkamara adta ki, Bér Dezső rajzolta.',
          caption='„Jegyezzetek hadikölcsönt!” — háborús plakát Budapestről',
          image={'src': H + 'hadikolcson-plakat.webp', 'w': 955, 'h': 1252, 'alt': 'Plakát: két katona aranyérmék halmában, felirat: Jegyezzetek hadikölcsönt!',
                 'credit': 'Bér Dezső · közkincs', 'source': C + 'Bér_Hadikölcsön.jpg'}),
  5: dict(description='Gróf Tisza István 1913 és 1917 között volt Magyarország miniszterelnöke. 1914 júliusában eleinte ellenezte a Szerbia elleni háborút, végül azonban beleegyezett. 1918. október 31-én, az őszirózsás forradalom napján katonák meggyilkolták.',
          caption='Gróf Tisza István (1861–1918)',
          image={'src': H + 'tisza-istvan.webp', 'w': 720, 'h': 982, 'alt': 'Tisza István ülő portréja, szemüvegben',
                 'credit': 'Szenes Adolf · közkincs', 'source': C + 'Tisza_István_portréja_(Szenes_Adolf,_1917).jpg'}),
  6: dict(description='Szarajevó Bosznia fővárosa volt, amelyet a Monarchia 1908-ban annektált. Itt lőtte le 1914. június 28-án Gavrilo Princip Ferenc Ferdinánd trónörököst és feleségét. A merénylet után a Monarchia ultimátumot küldött Szerbiának, majd július 28-án hadat üzent. A rajz egy olasz hetilap címlapján jelent meg — a művész elképzelése a jelenetről.',
          caption='A szarajevói merénylet egy olasz hetilap címlapján, 1914',
          image={'src': H + 'szarajevoi-merenylet.webp', 'w': 860, 'h': 1041, 'alt': 'Rajz: a merénylő pisztollyal lő a nyitott autóban ülő trónörökös párra',
                 'credit': 'Achille Beltrame, La Domenica del Corriere · közkincs', 'source': C + 'DC-1914-27-d-Sarajevo-cropped.jpg'}),
  7: dict(description='A Doberdói-fennsík a Karszt-hegység nyugati része az Isonzó folyó alsó szakaszánál, Görz (Gorizia) és a tenger között. 1915–1916-ban itt folytak az isonzói csaták legvéresebb harcai. Sok magyar ezred harcolt itt, ezért a Doberdó a magyar emlékezetben a háború szenvedéseinek jelképe lett.',
          caption='Harc a Doberdón — Rudolf Alfred Höger festménye, 1916',
          image={'src': H + 'harc-a-doberdon.webp', 'w': 800, 'h': 542, 'alt': 'Festmény: osztrák–magyar és olasz katonák közelharca sziklás, bokros terepen',
                 'credit': 'Rudolf Alfred Höger · közkincs', 'source': C + 'Kämpfe_auf_dem_Doberdo.JPG'}),
}

PHYS = {
  0: dict(description='A test helyét a koordináta-rendszerben két számmal adjuk meg. Itt a test az A pontból (1 m; 1 m) a B pontba (5 m; 4 m) jutott. Az elmozdulás a kék nyíl: az indulási helyről egyenesen az érkezési helyre mutat. Megmutatja, merre és mennyivel került arrébb a test — attól függetlenül, milyen úton jutott oda.',
          caption='A test közben 4 m-t haladt jobbra és 3 m-t felfelé.',
          image={'src': P + 'hely-es-elmozdulas-v2.svg', 'w': 360, 'h': 280, 'alt': 'Koordináta-rendszer: kék elmozdulásnyíl az A(1; 1) pontból a B(5; 4) pontba', 'credit': OWN}),
  1: dict(description='A kerékpáros útvonala a pálya: 500 m egyenes, egy kb. 314 m-es kanyar, majd 400 m egyenes. A pálya hossza a megtett út: kb. 1,2 km. Az elmozdulás (kék szaggatott nyíl) viszont csak kb. 0,9 km, mert egyenesen, „légvonalban” köti össze az indulást és az érkezést.',
          caption='A megtett út és az elmozdulás nagysága nem mindig egyenlő.',
          image={'src': P + 'palya.svg', 'w': 360, 'h': 290, 'alt': 'Kanyarodó sárga útvonal az indulástól az érkezésig, és egy egyenes kék szaggatott nyíl', 'credit': OWN}),
  2: dict(description='Az út–idő grafikon vízszintes tengelyén az idő, függőleges tengelyén a megtett út látható. 10 s alatt a kerékpáros 50 m-t tesz meg (5 m/s), a gyalogos 15 m-t (1,5 m/s), az álló test pedig semennyit (0 m/s).',
          caption='Minél meredekebb a vonal, annál nagyobb a sebesség.',
          image={'src': P + 'ut-ido-grafikon.svg', 'w': 360, 'h': 290, 'alt': 'Út–idő grafikon három egyenessel: kerékpáros, gyalogos, álló test', 'credit': OWN}),
  3: dict(description='Ha egy futó a 100 m-es távot 10 s alatt teszi meg, az átlagsebessége 100 m : 10 s = 10 m/s, ami 36 km/h. Az átlagsebesség nem árulja el, hogy a futó közben gyorsult vagy lassult — csak azt, hogy összesen mennyi utat mennyi idő alatt tett meg.',
          caption='átlagsebesség = megtett út : eltelt idő · 1 m/s = 3,6 km/h',
          image={'src': P + 'atlagsebesseg.svg', 'w': 360, 'h': 250, 'alt': '100 méteres futópálya, stopper 10 másodperccel, és a számítás: 100 m osztva 10 s egyenlő 10 m/s', 'credit': OWN}),
  4: dict(description='A mozgólépcső lépcsőfokai egyenletesen haladnak. Aki nyugodtan áll rajta, egyenlő idők alatt egyenlő utakat tesz meg: közel állandó sebességgel mozog. Egy szokásos mozgólépcső sebessége kb. 0,5 m/s.',
          caption='Mozgólépcső egy budapesti metróállomáson',
          image={'src': P + 'mozgolepcso-budapest.webp', 'w': 1400, 'h': 928, 'alt': 'Hosszú mozgólépcső egy budapesti metróállomás alagútjában',
                 'credit': 'Yelkrokoyade · CC BY-SA 3.0', 'source': C + 'Escalator_métro_Budapest.jpg'}),
  5: dict(description='Newton első törvénye: minden test megtartja nyugalmi állapotát vagy egyenes vonalú egyenletes mozgását, amíg egy másik test (erő) ezt meg nem változtatja. Fent: az asztalon fekvő labdára ható erők kiegyenlítik egymást, ezért nyugalomban marad. Lent: a jégkorongot a jégen alig fékezi valami, ezért egyenlő idők alatt egyenlő utakat tesz meg.',
          image={'src': P + 'newton-1-torveny.svg', 'w': 360, 'h': 272, 'alt': 'Fent egy asztalon nyugvó labda két egyforma, ellentétes erőnyíllal; lent egy jégkorong három helyzete egyforma sebességnyilakkal', 'credit': OWN}),
  6: dict(description='Ha a rekordidőből kiszámoljuk az átlagsebességet (megtett út : idő), a különböző sportágak is összehasonlíthatók. A leggyorsabb úszó átlagosan kb. 8,6 km/h-val, a leggyorsabb síkfutó kb. 37,6 km/h-val halad, a kerékpáros egyórás rekord 56,8 km/h. A sugárhajtású ThrustSSC autó 1997-ben 1228 km/h-val a hangnál is gyorsabban száguldott.',
          caption='Híres rekordok átlagsebessége km/h-ban',
          image={'src': P + 'sebessegrekordok.svg', 'w': 360, 'h': 310, 'alt': 'Vízszintes oszlopdiagram négy sportrekord átlagsebességéről', 'credit': OWN}),
}

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
    for block, changes in ((HIST_BLOCK, HIST), (PHYS_BLOCK, PHYS)):
        cards = call('GET', f'/rest/v1/content_blocks?id=eq.{block}&select=content')[0]['content']
        for i, ch in changes.items():
            before = cards[i]
            after = dict(before, **ch)
            if dry:
                print(block[:8], i, before['heading'], '→', sorted(set(after) - set(before)) or 'text only'); continue
            eid = call('POST', '/rest/v1/rpc/edit_content_card', {'p_block_id': block, 'p_card_index': i,
                       'p_before': before, 'p_after': after, 'p_editor': None})
            print(block[:8], i, before['heading'], 'edit', eid)

if __name__ == '__main__':
    main('--dry-run' in sys.argv)
