"""Turul Academy physics diagrams, round 3 (2026-09-30), PHYS-78-03 lessons 2–3: redraws of the three cards that
only had the plain native sketch (card.diagram). Same style as make_physics_diagrams*.py; Hungarian labels,
numbers checked by hand (see comments).
Run from content/media: `python3 make_physics_diagrams_3.py` → staging/PHYS-78-03/*.svg
(uploaded to content-media/phys/… by lesson_images_2026_09b.py --batch 4)."""
import os
F = "font-family=\"Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif\""
BLUE, AMBER, GREEN, RED, INK, MUTED, GRID = '#2563EB', '#F59E0B', '#16A34A', '#DC2626', '#0F172A', '#475569', '#E2E8F0'

def arrow_marker(mid, col, size=5):
    return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="{size}" markerHeight="{size}" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {F}>'
            f'<title>{title}</title><rect width="{w}" height="{h}" fill="#fff"/>'
            f'<defs>{arrow_marker("ahi", INK, 6)}{arrow_marker("ahb", BLUE)}{arrow_marker("ahg", GREEN)}{arrow_marker("aha", AMBER)}'
            f'<marker id="ahd" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
            f'</defs>{body}</svg>')

def t(x, y, s, size=14, fill=INK, anchor='start', weight='normal'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'

def car_side(x, y, w=86, h=34):
    """Side view; (x, y) = top-left of the body, wheels touch y+h+12 (the ground line)."""
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#FEF3C7" stroke="#B45309" stroke-width="2"/>',
            f'<rect x="{x+w*0.62}" y="{y+6}" width="{w*0.26}" height="{h*0.36}" rx="2" fill="#E0F2FE" stroke="#B45309" stroke-width="1.3"/>',
            f'<circle cx="{x+w*0.22}" cy="{y+h+6}" r="6" fill="{INK}"/>', f'<circle cx="{x+w*0.78}" cy="{y+h+6}" r="6" fill="{INK}"/>']

out = {}

# 1. Megtett út: egyenletesen haladó autó, 5 s-onként 25 m (v = 5 m/s = 18 km/h); 20 s alatt 100 m
ox, oy, sx, sy = 52, 318, 13.5, 1.5   # graph origin, px per s, px per m  (20 s -> 270 px, 100 m -> 150 px)
G = lambda tt, s: (ox + tt*sx, oy - s*sy)
b = [t(180, 24, 'Egyenletesen haladó autó útja', 14, INK, 'middle', 'bold')]
# strip: car at 0, 25, 50, 75, 100 m (x scale: 100 m -> 270 px like the graph's time axis)
mx = lambda m: ox + m/100*20*sx
b += [f'<line x1="{ox-10}" y1="90" x2="{mx(100)+22}" y2="90" stroke="{MUTED}" stroke-width="2"/>']
for k in range(5):
    m, tt = 25*k, 5*k
    x = mx(m)
    b += [f'<rect x="{x-11}" y="62" width="22" height="14" rx="4" fill="{"#FEF3C7" if k else "#FDE68A"}" stroke="#B45309" stroke-width="1.6"/>',
          f'<circle cx="{x-6}" cy="80" r="3.6" fill="{INK}"/>', f'<circle cx="{x+6}" cy="80" r="3.6" fill="{INK}"/>',
          f'<line x1="{x}" y1="92" x2="{x}" y2="98" stroke="{MUTED}" stroke-width="1.6"/>',
          t(x, 112, f'{tt} s', 12, INK, 'middle', 'bold'), t(x, 127, f'{m} m', 11.5, MUTED, 'middle')]
b.append(t(ox-10, 50, 'az autó helyzete 5 másodpercenként', 11.5, MUTED))
# graph
for tt in range(0, 21, 5):
    x, _ = G(tt, 0); b += [f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{G(0,105)[1]}" stroke="{GRID}"/>', t(x, oy+18, tt, 12, MUTED, 'middle')]
for s in range(0, 101, 25):
    _, y = G(0, s); b.append(f'<line x1="{ox}" y1="{y}" x2="{G(21,0)[0]}" y2="{y}" stroke="{GRID}"/>')
    if s: b.append(t(ox-8, y+4, s, 12, MUTED, 'end'))
pts = ' '.join(f'{G(5*k, 25*k)[0]},{G(5*k, 25*k)[1]}' for k in range(5))
b += [f'<line x1="{ox}" y1="{oy}" x2="{G(21.5,0)[0]}" y2="{oy}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{G(0,112)[1]}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>']
b += [f'<circle cx="{G(5*k,25*k)[0]}" cy="{G(5*k,25*k)[1]}" r="4.2" fill="{BLUE}" stroke="#fff" stroke-width="1.5"/>' for k in range(5)]
b += [t(G(21.5,0)[0], oy+32, 'idő (s)', 12.5, INK, 'end', 'bold'), t(ox+8, G(0,112)[1]+4, 'megtett út (m)', 12.5, INK, 'start', 'bold'),
      t(G(1.2, 0)[0], G(0, 72)[1], 'minden 5 s-ban +25 m', 12, BLUE, 'start', 'bold'),
      f'<rect x="10" y="364" width="340" height="46" rx="10" fill="#EFF6FF" stroke="#BFDBFE"/>',
      t(180, 384, 'v = s : t = 100 m : 20 s = 5 m/s', 15, BLUE, 'middle', 'bold'), t(180, 401, '(5 m/s = 18 km/h)', 11.5, MUTED, 'middle')]
out['megtett-ut'] = svg(360, 420, ''.join(b), 'Megtett út: az autó 5 másodpercenként 25 métert tesz meg, 20 s alatt 100 métert')

# 2. Szabadesés: h = g·t²/2, g = 9,8 m/s²; v = g·t
g, sc = 9.8, 12          # sc: px per metre
y0, xb = 96, 112         # y of the dropped body at t = 0; x of the column
rows = [0, 0.5, 1, 1.5, 2]
fmt = lambda v: f'{v:.1f}'.replace('.', ',')
b = [f'<line x1="22" y1="22" x2="22" y2="52" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>',
     t(36, 34, 'nehézségi erő: F = m · g', 13, BLUE, 'start', 'bold'), t(36, 50, 'végig lefelé mutat, nagysága állandó', 11.5, MUTED),
     t(14, 84, 'idő', 10.5, MUTED, 'start', 'bold'), t(xb+14, 84, 'megtett út', 10.5, MUTED, 'start', 'bold'), t(214, 84, 'sebesség', 10.5, MUTED, 'start', 'bold')]
b.append(f'<line x1="{xb}" y1="{y0}" x2="{xb}" y2="{y0 + 0.5*g*4*sc}" stroke="{GRID}" stroke-width="2.4"/>')
for tt in rows:
    d = 0.5*g*tt*tt; y = y0 + d*sc; v = g*tt
    lab_t = '0 s' if tt == 0 else (f'{fmt(tt)} s' if tt % 1 else f'{int(tt)} s')
    b += [f'<circle cx="{xb}" cy="{y}" r="6.5" fill="{BLUE}" opacity="{0.35 if tt == 0 else 1}" stroke="#fff" stroke-width="1.5"/>',
          t(14, y+4, lab_t, 11.5, INK, 'start', 'bold'), t(xb+14, y+4, (f'{fmt(d)} m' if d else '0 m'), 11.5, INK)]
    if v:
        b += [f'<line x1="214" y1="{y}" x2="{214+v*4:.1f}" y2="{y}" stroke="{AMBER}" stroke-width="5" stroke-linecap="round"/>',
              t(214+v*4+6, y+4, f'{fmt(v)} m/s', 11, MUTED)]
    else:
        b.append(t(214, y+4, '0 m/s', 11, MUTED))
yg = y0 + 0.5*g*4*sc + 16
b += [f'<line x1="14" y1="{yg}" x2="346" y2="{yg}" stroke="{MUTED}" stroke-width="2.4"/>',
      f'<rect x="10" y="{yg+14}" width="340" height="62" rx="10" fill="#F1F5F9"/>',
      t(180, yg+36, 'g ≈ 9,8 m/s²: másodpercenként kb. 9,8 m/s-mal nő a sebesség', 11.5, INK, 'middle', 'bold'),
      t(180, yg+54, 'Légellenállás nélkül minden test egyformán esik.', 11.5, MUTED, 'middle'),
      t(180, yg+69, 'Egyenlő idők alatt egyre nagyobb utat tesz meg.', 11.5, MUTED, 'middle')]
H = int(yg + 76 + 10)
out['szabadeses'] = svg(360, H, ''.join(b), 'Szabadon eső test: a helyzete fél másodpercenként, a megtett út és a sebesség nő')

# 3. Fékezés és kanyarodás: súrlódási erő (kék) és gyorsulás (zöld) iránya; sebesség (borostyán)
b = [t(180, 24, '1. Fékezés egyenes úton', 14, INK, 'middle', 'bold'),
     f'<line x1="14" y1="136" x2="346" y2="136" stroke="{MUTED}" stroke-width="2.4"/>']
b += car_side(108, 78, 92, 34)
b += [f'<line x1="124" y1="58" x2="216" y2="58" stroke="{AMBER}" stroke-width="4" marker-end="url(#aha)"/>', t(222, 62, 'v (mozgás iránya)', 12, '#B45309', 'start', 'bold'),
      f'<line x1="200" y1="154" x2="110" y2="154" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>', t(206, 158, 'F súrlódási erő', 12, BLUE, 'start', 'bold'),
      f'<line x1="200" y1="176" x2="120" y2="176" stroke="{GREEN}" stroke-width="4" marker-end="url(#ahg)"/>', t(206, 180, 'a gyorsulás', 12, GREEN, 'start', 'bold'),
      t(180, 204, 'A gyorsulás a mozgással ellentétes: az autó lassul.', 12, MUTED, 'middle'),
      f'<line x1="10" y1="220" x2="350" y2="220" stroke="{GRID}" stroke-width="2"/>',
      t(180, 244, '2. Kanyarodás (felülnézet)', 14, INK, 'middle', 'bold')]
cx, cy, R = 180, 420, 130
ax1, ay1 = cx - R*0.8660, cy - R*0.5     # 150° point
ax2, ay2 = cx + R*0.8660, cy - R*0.5     # 30° point
b += [f'<path d="M{ax1:.1f},{ay1:.1f} A{R},{R} 0 0 1 {ax2:.1f},{ay2:.1f}" fill="none" stroke="#CBD5E1" stroke-width="30" stroke-linecap="butt"/>',
      f'<path d="M{ax1:.1f},{ay1:.1f} A{R},{R} 0 0 1 {ax2:.1f},{ay2:.1f}" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="9 7"/>']
topy = cy - R
b += [f'<rect x="{cx-19}" y="{topy-10}" width="38" height="20" rx="6" fill="#FEF3C7" stroke="#B45309" stroke-width="2"/>',
      f'<rect x="{cx+5}" y="{topy-7}" width="9" height="14" rx="2" fill="#E0F2FE" stroke="#B45309" stroke-width="1.2"/>',
      f'<line x1="{cx}" y1="{topy}" x2="{cx}" y2="{cy-8}" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="4 4"/>',
      f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{INK}"/>', t(cx+10, cy+4, 'a kanyar középpontja', 11.5, MUTED),
      f'<line x1="{cx+24}" y1="{topy}" x2="{cx+92}" y2="{topy}" stroke="{AMBER}" stroke-width="4" marker-end="url(#aha)"/>', t(cx+96, topy+4, 'v', 13, '#B45309', 'start', 'bold'),
      f'<line x1="{cx-16}" y1="{topy+14}" x2="{cx-16}" y2="{topy+62}" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>', t(cx-24, topy+44, 'F', 13, BLUE, 'end', 'bold'),
      f'<line x1="{cx+14}" y1="{topy+14}" x2="{cx+14}" y2="{topy+62}" stroke="{GREEN}" stroke-width="4" marker-end="url(#ahg)"/>', t(cx+22, topy+44, 'a', 13, GREEN, 'start', 'bold'),
      t(14, 262, 'F: súrlódási erő', 11.5, BLUE, 'start', 'bold'), t(14, 278, 'a: gyorsulás', 11.5, GREEN, 'start', 'bold'), t(14, 294, 'v: sebesség', 11.5, '#B45309', 'start', 'bold'),
      t(180, cy+32, 'A gyorsulás és az erő a kanyar közepe felé mutat:', 11.5, MUTED, 'middle'),
      t(180, cy+48, 'a sebesség iránya változik, még ha nagysága állandó is.', 11.5, MUTED, 'middle')]
out['fekezes-es-kanyar'] = svg(360, cy + 62, ''.join(b), 'Fékezés és kanyarodás: a súrlódási erő és a gyorsulás iránya')

dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staging', 'PHYS-78-03')
os.makedirs(dst, exist_ok=True)
for name, s in out.items():
    open(os.path.join(dst, name + '.svg'), 'w', encoding='utf-8').write(s)
    print(name, len(s), 'bytes')
