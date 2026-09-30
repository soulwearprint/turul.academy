"""Turul Academy physics diagrams, round 2 (2026-09-30), PHYS-78-03 lessons 2–4: graphs and two
illustrative phone screens (they are drawings, NOT screenshots of a real app). Same style as
make_physics_diagrams.py; Hungarian labels, numbers checked by hand (see comments).
Run from content/media: `python3 make_physics_diagrams_2.py` → staging/PHYS-78-03/*.svg
(uploaded to content-media/phys/… by lesson_images_2026_09b.py --batch 3)."""
import os
F = "font-family=\"Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif\""
BLUE, AMBER, GREEN, RED, INK, MUTED, GRID = '#2563EB', '#F59E0B', '#16A34A', '#DC2626', '#0F172A', '#475569', '#E2E8F0'

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {F}>'
            f'<title>{title}</title><rect width="{w}" height="{h}" fill="#fff"/>'
            f'<defs><marker id="ahi" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            f'<marker id="ahb" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
            f'<marker id="ahg" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN}"/></marker>'
            f'<marker id="ahd" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
            f'</defs>{body}</svg>')

def t(x, y, s, size=14, fill=INK, anchor='start', weight='normal'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'

out = {}

# 1. Átlagsebesség két szakaszon: 40 km / 0,5 h = 80 km/h; 60 km / 1,5 h = 40 km/h; összesen 100 km / 2 h = 50 km/h
k = 3.2  # px per km
x1, x2, x3 = 20, 20 + 40*k, 20 + 100*k
b = [t(180, 26, 'Két szakaszból álló út', 14, INK, 'middle', 'bold'),
     t((x1+x2)/2, 58, '1. szakasz', 12, MUTED, 'middle', 'bold'), t((x1+x2)/2, 74, '40 km · 0,5 óra', 12, INK, 'middle'),
     t((x2+x3)/2, 58, '2. szakasz', 12, MUTED, 'middle', 'bold'), t((x2+x3)/2, 74, '60 km · 1,5 óra', 12, INK, 'middle'),
     f'<rect x="{x1}" y="86" width="{x2-x1}" height="26" rx="5" fill="{BLUE}"/>', f'<rect x="{x2}" y="86" width="{x3-x2}" height="26" rx="5" fill="{GREEN}"/>',
     t((x1+x2)/2, 104, '80 km/h', 13, '#fff', 'middle', 'bold'), t((x2+x3)/2, 104, '40 km/h', 13, '#fff', 'middle', 'bold'),
     f'<line x1="{x1}" y1="134" x2="{x3}" y2="134" stroke="{MUTED}" stroke-width="1.6" marker-start="url(#ahd)" marker-end="url(#ahd)"/>',
     f'<rect x="130" y="124" width="100" height="20" fill="#fff"/>', t(180, 139, '100 km · 2 óra', 13, INK, 'middle', 'bold'),
     f'<rect x="10" y="158" width="340" height="112" rx="10" fill="#EFF6FF" stroke="#BFDBFE"/>',
     t(180, 184, 'átlagsebesség = összes út : összes idő', 13.5, INK, 'middle', 'bold'),
     t(180, 214, '= 100 km : 2 óra = 50 km/h', 18, BLUE, 'middle', 'bold'),
     t(180, 246, 'Nem a két sebesség számtani közepe:', 11.5, RED, 'middle'), t(180, 261, '(80 + 40) : 2 = 60 km/h — ez most hibás lenne!', 11.5, RED, 'middle')]
out['atlagsebesseg-ket-szakasz'] = svg(360, 282, ''.join(b), 'Átlagsebesség egy két szakaszból álló úton')

# 2. Útvonaltervező képernyő (szemléltető rajz): 96 km, 80 km/h átlag -> 1,2 óra = 1 óra 12 perc
b = [f'<rect x="90" y="10" width="180" height="384" rx="28" fill="{INK}"/>',
     f'<rect x="98" y="38" width="164" height="330" rx="14" fill="#F8FAFC"/>', f'<rect x="150" y="18" width="60" height="10" rx="5" fill="#334155"/>',
     f'<rect x="98" y="38" width="164" height="206" rx="14" fill="#E2E8F0"/>', f'<rect x="98" y="150" width="164" height="94" fill="#E2E8F0"/>']
for d in ('M98,90 L262,110', 'M98,170 L262,150', 'M140,38 L150,244', 'M215,38 L205,244', 'M98,205 L262,215'):
    b.append(f'<path d="{d}" stroke="#fff" stroke-width="7" fill="none"/>')
b += [f'<path d="M124,222 C124,170 200,182 192,132 S238,108 238,72" stroke="{BLUE}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
      f'<circle cx="124" cy="222" r="8" fill="{GREEN}" stroke="#fff" stroke-width="2.5"/>', f'<circle cx="238" cy="72" r="8" fill="{RED}" stroke="#fff" stroke-width="2.5"/>',
      t(136, 232, 'A', 12, INK, 'start', 'bold'), t(224, 64, 'B', 12, INK, 'end', 'bold'),
      t(112, 266, 'A → B', 12, MUTED, 'start', 'bold'),
      t(112, 296, '1 óra 12 perc', 22, GREEN, 'start', 'bold'),
      t(112, 318, '96 km', 13, INK, 'start', 'bold'), t(112, 338, 'átlagsebesség: 80 km/h', 11.5, MUTED),
      t(112, 356, '96 km : 80 km/h = 1,2 óra', 10.5, MUTED),
      t(180, 414, 'Szemléltető rajz, nem valódi alkalmazás', 10.5, MUTED, 'middle')]
out['utvonaltervezo-kepernyo'] = svg(360, 424, ''.join(b), 'Szemléltető útvonaltervező képernyő: 96 km, 1 óra 12 perc')

# 3. Sebesség–idő grafikon: állandó 20 m/s, 10 s -> terület 200 m
ox, oy, sx, sy = 58, 238, 21, 8
G = lambda tt, v: (ox + tt*sx, oy - v*sy)
b = []
for tt in range(0, 13, 2):
    x, _ = G(tt, 0); b += [f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{G(0,26)[1]}" stroke="{GRID}"/>', t(x, oy+19, tt, 13, MUTED, 'middle')]
for v in range(0, 26, 5):
    _, y = G(0, v); b.append(f'<line x1="{ox}" y1="{y}" x2="{G(12.4,0)[0]}" y2="{y}" stroke="{GRID}"/>')
    if v: b.append(t(ox-8, y+5, v, 13, MUTED, 'end'))
(rx0, ry0), (rx1, ry1) = G(0, 20), G(10, 0)
b += [f'<rect x="{rx0}" y="{ry0}" width="{rx1-rx0}" height="{ry1-ry0}" fill="#DBEAFE" stroke="{BLUE}" stroke-width="3"/>',
      f'<line x1="{ox}" y1="{oy}" x2="{G(12.9,0)[0]}" y2="{oy}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{G(0,27.5)[1]}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      t(G(12.9,0)[0], oy+36, 'idő (s)', 13, INK, 'end', 'bold'), t(ox+8, G(0,27.5)[1]+4, 'sebesség (m/s)', 13, INK, 'start', 'bold'),
      t((rx0+rx1)/2, ry0+58, 'terület = megtett út', 14, BLUE, 'middle', 'bold'),
      t((rx0+rx1)/2, ry0+84, 's = v · t', 17, INK, 'middle', 'bold'),
      t((rx0+rx1)/2, ry0+108, '20 m/s · 10 s = 200 m', 14, INK, 'middle')]
out['sebesseg-ido-terulet'] = svg(360, 290, ''.join(b), 'Sebesség–idő grafikon: a téglalap területe a megtett út')

# 4. 120 km megtételéhez szükséges idő: 30 km/h -> 4 h; 60 -> 2 h; 90 -> 1 h 20 perc; 120 -> 1 h
rows = [(30, 4.0, '4 óra', '#0EA5E9'), (60, 2.0, '2 óra', GREEN), (90, 120/90, '1 óra 20 perc', AMBER), (120, 1.0, '1 óra', BLUE)]
x0, xw = 16, 250
b = [t(14, 24, '120 km megtételéhez szükséges idő', 14, INK, 'start', 'bold')]
for h in range(0, 5):
    x = x0 + h/4*xw; b += [f'<line x1="{x}" y1="38" x2="{x}" y2="250" stroke="{GRID}"/>', t(x, 266, h, 12, MUTED, 'middle')]
b.append(t(x0 + xw + 14, 266, 'óra', 12, MUTED, 'start', 'bold'))
for i, (v, tt, lab, col) in enumerate(rows):
    y = 48 + i*52
    b += [t(x0, y+10, f'{v} km/h', 13, INK, 'start', 'bold'), f'<rect x="{x0}" y="{y+16}" width="{tt/4*xw:.1f}" height="20" rx="4" fill="{col}"/>',
          t(x0 + tt/4*xw + 8, y+32, lab, 13, INK, 'start', 'bold')]
b.append(t(180, 296, 'kétszer akkora sebesség → feleannyi idő', 12, MUTED, 'middle'))
out['ido-es-tavolsag'] = svg(360, 306, ''.join(b), 'Ugyanaz a 120 km különböző sebességgel, különböző idő alatt')

# 5. Newton II.: F = 2 N mindkét kocsira; 1 kg -> a = 2 m/s^2; 2 kg -> a = 1 m/s^2
def cart(x, y, w, h, lab):
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#FEF3C7" stroke="#B45309" stroke-width="2"/>',
            f'<circle cx="{x+w*0.22}" cy="{y+h+6}" r="6" fill="{INK}"/>', f'<circle cx="{x+w*0.78}" cy="{y+h+6}" r="6" fill="{INK}"/>',
            t(x+w/2, y+h/2+5, lab, 14, INK, 'middle', 'bold')]
b = [t(180, 26, 'Ugyanaz az erő, különböző tömeg', 14, INK, 'middle', 'bold'),
     f'<line x1="14" y1="98" x2="346" y2="98" stroke="{MUTED}" stroke-width="2"/>', f'<line x1="14" y1="206" x2="346" y2="206" stroke="{MUTED}" stroke-width="2"/>']
b += cart(30, 46, 60, 40, '1 kg') + cart(30, 140, 90, 54, '2 kg')
b += [f'<line x1="90" y1="66" x2="180" y2="66" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>', t(135, 57, 'F = 2 N', 13, BLUE, 'middle', 'bold'),
      f'<line x1="120" y1="167" x2="210" y2="167" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>', t(165, 158, 'F = 2 N', 13, BLUE, 'middle', 'bold'),
      f'<line x1="30" y1="118" x2="150" y2="118" stroke="{GREEN}" stroke-width="4" marker-end="url(#ahg)"/>', t(158, 123, 'a = 2 m/s²', 14, GREEN, 'start', 'bold'),
      f'<line x1="30" y1="226" x2="90" y2="226" stroke="{GREEN}" stroke-width="4" marker-end="url(#ahg)"/>', t(98, 231, 'a = 1 m/s²', 14, GREEN, 'start', 'bold'),
      f'<rect x="10" y="246" width="340" height="52" rx="10" fill="#F1F5F9"/>', t(180, 268, 'F = m · a    →    a = F : m', 15, INK, 'middle', 'bold'),
      t(180, 287, 'kétszer akkora tömeg → feleakkora gyorsulás', 12, MUTED, 'middle')]
out['newton-2-torveny'] = svg(360, 308, ''.join(b), 'Newton második törvénye: ugyanaz az erő, különböző tömeg')

# 6. Mozgáselemző képernyő (szemléltető rajz): 1250 m / 500 s = 2,5 m/s = 9 km/h
b = [f'<rect x="90" y="10" width="180" height="384" rx="28" fill="{INK}"/>', f'<rect x="98" y="38" width="164" height="330" rx="14" fill="#F8FAFC"/>',
     f'<rect x="150" y="18" width="60" height="10" rx="5" fill="#334155"/>',
     t(180, 62, 'Mozgáselemző', 13, INK, 'middle', 'bold')]
for i, (lab, val) in enumerate((('Idő', '8 perc 20 s'), ('Megtett út', '1,25 km'), ('Átlagsebesség', '9,0 km/h'))):
    y = 84 + i*40
    b += [f'<rect x="108" y="{y}" width="144" height="32" rx="8" fill="#E0F2FE"/>', t(116, y+13, lab, 9.5, MUTED), t(116, y+27, val, 13, INK, 'start', 'bold')]
gx, gy, gw, gh = 118, 340, 130, 100   # graph area bottom-left, width, height
b += [t(108, 226, 'sebesség (km/h)', 10, MUTED, 'start', 'bold'),
      f'<line x1="200" y1="223" x2="216" y2="223" stroke="{RED}" stroke-width="1.3" stroke-dasharray="4 3"/>', t(220, 226, 'átlag: 9', 10, RED, 'start', 'bold'),
      f'<line x1="{gx}" y1="{gy}" x2="{gx+gw}" y2="{gy}" stroke="{INK}" stroke-width="1.3"/>', f'<line x1="{gx}" y1="{gy}" x2="{gx}" y2="{gy-gh+8}" stroke="{INK}" stroke-width="1.3"/>']
for v in (0, 5, 10, 15):
    y = gy - v*6
    b += [f'<line x1="{gx}" y1="{y}" x2="{gx+gw}" y2="{y}" stroke="{GRID}"/>', t(gx-4, y+3.5, v, 9, MUTED, 'end')]
pts = [(0, 0), (0.4, 8), (1, 10), (2, 9.5), (3, 8), (4, 9.5), (5, 9), (6, 10), (7, 8.5), (8, 9.5)]
xs = gw / 8.33
b += [f'<polyline points="' + ' '.join(f'{gx+p*xs:.1f},{gy-v*6:.1f}' for p, v in pts) + f'" fill="none" stroke="{BLUE}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>',
      f'<line x1="{gx}" y1="{gy-54}" x2="{gx+gw}" y2="{gy-54}" stroke="{RED}" stroke-width="1.3" stroke-dasharray="4 3"/>',
      t(gx+gw, gy+13, 'idő (perc)', 9, MUTED, 'end'),
      t(180, 414, 'Szemléltető rajz, nem valódi alkalmazás', 10.5, MUTED, 'middle')]
out['mozgaselemzo-kepernyo'] = svg(360, 424, ''.join(b), 'Szemléltető mozgáselemző képernyő: 8 perc 20 s, 1,25 km, 9 km/h')

dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staging', 'PHYS-78-03')
os.makedirs(dst, exist_ok=True)
for name, s in out.items():
    open(os.path.join(dst, name + '.svg'), 'w', encoding='utf-8').write(s)
    print(name, len(s), 'bytes')
