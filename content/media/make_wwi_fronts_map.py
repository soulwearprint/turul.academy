"""Run: download the source SVG (see manifest.json → frontok-1914-1918-hu.svg) as fronts_fr.svg next to
this script, then `python3 make_wwi_fronts_map.py` → out/wwi-frontok-hu.svg. Label/line coordinates are
in the source map's own units (998×593), placed on gridded zoom crops.

Hungarian derivative of historicair's „Alliances militaires en Europe 1914-1918-fr.svg” (CC BY-SA 3.0):
labels translated, main front lines (schematic) + a small legend added."""
import re
s = open('fronts_fr.svg', encoding='utf-8').read()
HU = {
 'Maroc espagnol': 'Spanyol-Marokkó', 'Maroc (Fr)': 'Marokkó (fr.)', 'Algérie (Fr)': 'Algéria (fr.)', 'Tunisie (Fr)': 'Tunézia (fr.)',
 'FRANCE': 'FRANCIAORSZÁG', 'ESPAGNE': 'SPANYOLORSZÁG', 'PORTUGAL': 'PORTUGÁLIA', 'OCÉAN': 'Atlanti-', 'ATLANTIQUE': 'óceán',
 'Mer Méditerranée': 'Földközi-tenger', 'ROYAUME-UNI': 'EGYESÜLT KIRÁLYSÁG', 'Mer du Nord': 'Északi-tenger', 'Mer': 'Balti-',
 'Baltique': 'tenger', 'ITALIE': 'OLASZORSZÁG', 'AUTRICHE-': 'OSZTRÁK–MAGYAR', 'HONGRIE': 'MONARCHIA', 'ALLEMAGNE': 'NÉMETORSZÁG',
 'RUSSIE': 'OROSZORSZÁG', 'Mer Noire': 'Fekete-tenger', 'ROUMANIE': 'ROMÁNIA', 'BULGARIE': 'BULGÁRIA', 'EMPIRE': 'OSZMÁN',
 'OTTOMAN': 'BIRODALOM', 'GRÈCE': 'GÖRÖGORSZÁG', 'GRECE': 'GÖRÖGORSZÁG', 'ALBANIE': 'ALBÁNIA', 'MONTÉNÉGRO': 'MONTENEGRÓ',
 'SERBIE': 'SZERBIA', 'Triple-Alliance': 'Központi hatalmak', 'Triple-Entente': 'Antant és szövetségesei',
 'ALLIANCES MILITAIRES': 'SZÖVETSÉGEK ÉS', 'EN EUROPE 1914-1918': 'FRONTOK 1914–1918', 'Pays neutres': 'Semleges országok',
 'NORVEGE': 'NORVÉGIA', 'SUEDE': 'SVÉDORSZÁG', 'SUISSE': 'SVÁJC', 'DANEMARK': 'DÁNIA',
}
def tr(m):
    inner = m.group(2)
    return m.group(1) + HU.get(inner, inner) + m.group(3)
s = re.sub(r'(<(?:tspan|text)[^>]*>)([^<]+)(</(?:tspan|text)>)', tr, s)
s = re.sub(r'<text\b(?=[^>]*>(?:(?!</text>).)*GÖRÖGORSZÁG)', '<text transform="translate(0,11)"', s, flags=re.S)
W, H = '998.35828', '592.88281'
s = s.replace(f'width="{W}"\n   height="{H}"', f'width="{W}"\n   height="{H}"\n   viewBox="0 0 {W} {H}"', 1)

FRONTS = {
 'nyugati': [(278,209.5),(280,216),(282,224.5),(281,232),(283,240),(286,247),(292,251),(300,253),(311,258),(314,264),(317.5,270),(321,272),(327,283),(332,291),(331,303),(334,314)],
 'keleti': [(575,95),(588,103),(600,112),(603,135),(600,160),(597,178),(598,196),(596,215),(598,232),(607,248),(612,262),(613,280),(620,293),(626,302),
            (630,318),(641,335),(652,350),(664,362),(668,369),(684,367)],
 'olasz': [(383.9,348.3),(379,353),(379.3,359.9),(382.1,358.5),(384.9,363.7),(387.7,363.3),(393.7,358.8),(397.2,356.7),(400,352.9),(401.4,347.3),
           (404.9,346.5),(409.1,343.4),(411.9,343.7),(414,348.3),(423.8,348.6),(428,350.1),(432.2,353.2),(433,359.5),(430,364),(427.5,367.3)],
 'balkani': [(519.5,500.5),(530,497),(540,493),(549.5,489),(556,489.5),(562,485),(573.5,483.5),(589,477),(603,473),(606,480),(604,489)],
}
SERB = [(556,391),(540,393.5),(528,392),(520,393),(517,405),(516.5,414),(520,421)]
def pts(p): return ' '.join(f'{x},{y}' for x, y in p)
RED = '#c8102e'
g = ['<g id="turul-frontok" font-family="DejaVu Sans, Arial, sans-serif">']
for p in FRONTS.values():
    g.append(f'<polyline points="{pts(p)}" fill="none" stroke="#fff" stroke-width="6" stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>')
    g.append(f'<polyline points="{pts(p)}" fill="none" stroke="{RED}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>')
g.append(f'<polyline points="{pts(SERB)}" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round" opacity="0.9"/>')
g.append(f'<polyline points="{pts(SERB)}" fill="none" stroke="{RED}" stroke-width="2.6" stroke-dasharray="5 3.5" stroke-linejoin="round"/>')
def label(x, y, text, anchor='start', size=12):
    common = f'x="{x}" y="{y}" font-size="{size}" font-weight="bold" text-anchor="{anchor}"'
    return (f'<text {common} fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round">{text}</text>'
            f'<text {common} fill="{RED}">{text}</text>')
g += [label(274, 238, 'Nyugati front', 'end'), label(606, 170, 'Keleti front'), label(662, 330, 'Román front'),
      label(381, 381, 'Olasz (isonzói) front', 'middle'), label(598, 506, 'Balkáni front', 'start'),
      label(506, 402, 'Szerb front', 'end', 11)]
# Legend for the lines, top-left in the Atlantic.
g.append('<rect x="8" y="46" width="150" height="58" fill="#fff" stroke="#000" stroke-width="1.2"/>')
g.append(f'<line x1="16" y1="62" x2="44" y2="62" stroke="{RED}" stroke-width="3.2"/>')
g.append('<text x="50" y="59" font-size="10.5">Fő frontvonalak</text><text x="50" y="71" font-size="9" fill="#333">1915–1917, vázlatosan</text>')
g.append(f'<line x1="16" y1="88" x2="44" y2="88" stroke="{RED}" stroke-width="2.6" stroke-dasharray="5 3.5"/>')
g.append('<text x="50" y="91" font-size="10.5">Szerb front 1914–1915</text>')
g.append('</g>')
s = s.replace('</svg>', '\n'.join(g) + '\n</svg>')
NOTE = ('<!-- Derivative of "Alliances militaires en Europe 1914-1918-fr.svg" by historicair, derivative work: Augusta 89 '
        '(https://commons.wikimedia.org/wiki/File:Alliances_militaires_en_Europe_1914-1918-fr.svg), CC BY-SA 3.0. '
        'Changes: Hungarian labels, schematic main front lines and a legend added (Turul Academy, 2026). '
        'This file is licensed under CC BY-SA 3.0. -->\n')
i = s.index('?>') + 2
s = s[:i] + '\n' + NOTE + s[i:]
import os
os.makedirs('out', exist_ok=True)
open('out/wwi-frontok-hu.svg', 'w', encoding='utf-8').write(s)
print('written', len(s))
