"""Turul Academy physics diagrams for PHYS-78-03 / „Mozgások megfigyelése és csoportosítása”.
Hand-authored SVG, Hungarian labels, drawn to scale where there are numbers.
Run: `python3 make_physics_diagrams.py` → final/phys/*.svg (upload to content-media/phys/mozgasok/)."""
import math
F = "font-family=\"Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif\""
BLUE, AMBER, GREEN, RED, INK, MUTED, GRID = '#2563EB', '#F59E0B', '#16A34A', '#DC2626', '#0F172A', '#475569', '#E2E8F0'

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {F}>'
            f'<title>{title}</title><rect width="{w}" height="{h}" fill="#fff"/>'
            f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker>'
            f'<marker id="ahb" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
            f'<marker id="ahi" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            f'<marker id="ahr" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>'
            f'<marker id="ahg" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN}"/></marker>'
            f'</defs>{body}</svg>')

def t(x, y, s, size=14, fill=INK, anchor='start', weight='normal', extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {extra}>{s}</text>'

out = {}

# 1. Hely és elmozdulás — A(1;1) → B(5;4), 1 m = 45 px
ox, oy, u = 50, 250, 45
P = lambda x, y: (ox + x*u, oy - y*u)
b = []
for i in range(0, 7):
    x, _ = P(i, 0); b.append(f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{P(0,4.6)[1]}" stroke="{GRID}"/>'); b.append(t(x, oy+20, i, 13, MUTED, 'middle'))
for j in range(0, 5):
    _, y = P(0, j); b.append(f'<line x1="{ox}" y1="{y}" x2="{P(6.3,0)[0]}" y2="{y}" stroke="{GRID}"/>')
    if j: b.append(t(ox-10, y+5, j, 13, MUTED, 'end'))
b.append(f'<line x1="{ox}" y1="{oy}" x2="{P(6.5,0)[0]}" y2="{oy}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>')
b.append(f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{P(0,4.9)[1]}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>')
b.append(t(P(6.5,0)[0], oy-8, 'x (m)', 13, INK, 'end', 'bold')); b.append(t(ox+8, P(0,4.8)[1]+4, 'y (m)', 13, INK, 'start', 'bold'))
(ax, ay), (bx, by), (cx, cy) = P(1, 1), P(5, 4), P(5, 1)
b.append(f'<path d="M{ax},{ay} L{cx},{cy} L{bx},{by}" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="5 4"/>')
b.append(t((ax+cx)/2, ay+18, '4 m', 13, MUTED, 'middle')); b.append(t(cx+8, (cy+by)/2+5, '3 m', 13, MUTED))
b.append(f'<line x1="{ax}" y1="{ay}" x2="{bx-7}" y2="{by+5.3}" stroke="{BLUE}" stroke-width="4" marker-end="url(#ahb)"/>')
b.append(t((ax+bx)/2-18, (ay+by)/2-10, 'elmozdulás', 15, BLUE, 'middle', 'bold', f'transform="rotate(-36.9 {(ax+bx)/2-18} {(ay+by)/2-10})"'))
b += [f'<circle cx="{ax}" cy="{ay}" r="6" fill="{INK}"/>', f'<circle cx="{bx}" cy="{by}" r="6" fill="{INK}"/>',
      t(ax+2, ay+22, 'A (1; 1)', 14, INK, 'start', 'bold'), t(ax+2, ay+37, 'indulás', 12, MUTED),
      t(bx-10, by-10, 'B (5; 4)', 14, INK, 'end', 'bold'), t(bx-10, by-28, 'érkezés', 12, MUTED, 'end')]
out['hely-es-elmozdulas-v2'] = svg(360, 280, ''.join(b), 'Hely és elmozdulás koordináta-rendszerben')

# 2. Pálya — 500 m egyenes, negyedkör r = 200 m (≈ 314 m), 400 m egyenes; elmozdulás ≈ 922 m
k, ox, oy = 0.36, 34, 262
Q = lambda x, y: (ox + x*k, oy - y*k)
(sx, sy), (p1x, p1y), (p2x, p2y), (ex, ey) = Q(0, 0), Q(500, 0), Q(700, 200), Q(700, 600)
r = 200*k
b = [f'<path d="M{sx},{sy} L{p1x},{p1y} A{r},{r} 0 0 0 {p2x},{p2y} L{ex},{ey}" fill="none" stroke="{AMBER}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
     f'<line x1="{sx}" y1="{sy}" x2="{ex-4.4}" y2="{ey+5.1}" stroke="{BLUE}" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#ahb)"/>',
     f'<circle cx="{sx}" cy="{sy}" r="7" fill="{INK}"/>', f'<circle cx="{ex}" cy="{ey}" r="7" fill="{INK}"/>',
     t(sx, sy+24, 'Indulás', 14, INK, 'start', 'bold'), t(ex+12, ey+5, 'Érkezés', 14, INK, 'start', 'bold'),
     t((sx+p1x)/2+10, sy-12, '500 m', 13, '#B45309', 'middle', 'bold'),
     t(p1x+48, p1y-6, 'kanyar ≈ 314 m', 13, '#B45309', 'start', 'bold'),
     t(ex+12, (p2y+ey)/2+5, '400 m', 13, '#B45309', 'start', 'bold'),
     t(118, 148, 'elmozdulás ≈ 920 m', 14, BLUE, 'middle', 'bold', f'transform="rotate(-40.6 118 148)"'),
     f'<rect x="10" y="10" width="206" height="54" rx="8" fill="#FFFBEB" stroke="#FCD34D"/>',
     t(20, 32, 'Megtett út (a pálya hossza):', 12.5, '#92400E', 'start', 'bold'),
     t(20, 52, '500 + 314 + 400 ≈ 1214 m ≈ 1,2 km', 12.5, '#92400E')]
out['palya'] = svg(360, 290, ''.join(b), 'A kerékpáros pályája és elmozdulása')

# 3. Út–idő grafikon — 0–10 s, 0–50 m
ox, oy, sx_, sy_ = 58, 238, 26, 3.8
G = lambda tt, s: (ox + tt*sx_, oy - s*sy_)
b = []
for tt in range(0, 11, 2):
    x, _ = G(tt, 0); b.append(f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{G(0,52)[1]}" stroke="{GRID}"/>'); b.append(t(x, oy+19, tt, 13, MUTED, 'middle'))
for s in range(0, 51, 10):
    _, y = G(0, s); b.append(f'<line x1="{ox}" y1="{y}" x2="{G(10.4,0)[0]}" y2="{y}" stroke="{GRID}"/>')
    if s: b.append(t(ox-8, y+5, s, 13, MUTED, 'end'))
b += [f'<line x1="{ox}" y1="{oy}" x2="{G(10.9,0)[0]}" y2="{oy}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{G(0,55)[1]}" stroke="{INK}" stroke-width="1.6" marker-end="url(#ahi)"/>',
      t(G(10.9,0)[0], oy+36, 'idő (s)', 13, INK, 'end', 'bold'), t(ox+8, G(0,55)[1]+4, 'megtett út (m)', 13, INK, 'start', 'bold')]
for s10, col, lab, ly in ((50, BLUE, 'kerékpáros: 5 m/s', 54), (15, GREEN, 'gyalogos: 1,5 m/s', 15), (0, RED, 'álló test: 0 m/s', 0)):
    (x1, y1), (x2, y2) = G(0, 0), G(10, s10)
    b.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{4 if s10 else 5}" stroke-linecap="round"/>')
lx = G(4.2, 0)[0]
b += [t(G(0.6,0)[0], G(0,44)[1], 'kerékpáros: 5 m/s', 14, BLUE, 'start', 'bold'),
      t(G(9.9,0)[0], G(0,19)[1], 'gyalogos: 1,5 m/s', 14, GREEN, 'end', 'bold'),
      t(G(9.9,0)[0], G(0,3)[1], 'álló test: 0 m/s', 14, RED, 'end', 'bold')]
out['ut-ido-grafikon'] = svg(360, 290, ''.join(b), 'Út–idő grafikon három különböző sebességgel')

# 4. Átlagsebesség — 100 m, 10 s
b = [f'<rect x="20" y="58" width="320" height="30" rx="6" fill="#FEE2E2"/>',
     f'<line x1="20" y1="73" x2="340" y2="73" stroke="#fff" stroke-width="2" stroke-dasharray="10 8"/>',
     f'<line x1="26" y1="44" x2="26" y2="100" stroke="{INK}" stroke-width="3"/>', f'<line x1="334" y1="44" x2="334" y2="100" stroke="{INK}" stroke-width="3"/>',
     t(26, 36, 'RAJT', 13, INK, 'middle', 'bold'), t(334, 36, 'CÉL', 13, INK, 'middle', 'bold'),
     f'<line x1="32" y1="114" x2="328" y2="114" stroke="{BLUE}" stroke-width="2" marker-end="url(#ahb)" marker-start="url(#ahb)"/>',
     f'<rect x="150" y="104" width="60" height="20" fill="#fff"/>', t(180, 119, '100 m', 15, BLUE, 'middle', 'bold'),
     f'<circle cx="62" cy="180" r="30" fill="#fff" stroke="{INK}" stroke-width="3"/>', f'<rect x="56" y="140" width="12" height="9" rx="2" fill="{INK}"/>',
     f'<line x1="62" y1="180" x2="62" y2="160" stroke="{RED}" stroke-width="3" stroke-linecap="round"/>',
     t(62, 232, '10 s', 15, INK, 'middle', 'bold'),
     t(104, 158, 'átlagsebesség =', 15, INK, 'start', 'bold'),
     t(296, 150, 'megtett út', 13.5, INK, 'middle'), f'<line x1="258" y1="155" x2="334" y2="155" stroke="{INK}" stroke-width="1.5"/>', t(296, 172, 'eltelt idő', 13.5, INK, 'middle'),
     t(112, 204, '=', 16, INK), t(150, 196, '100 m', 14, BLUE, 'middle', 'bold'), f'<line x1="128" y1="201" x2="172" y2="201" stroke="{INK}" stroke-width="1.5"/>', t(150, 217, '10 s', 14, INK, 'middle', 'bold'),
     t(182, 208, '= 10 m/s', 17, BLUE, 'start', 'bold'), t(182, 230, '= 36 km/h', 14, MUTED, 'start', 'bold')]
out['atlagsebesseg'] = svg(360, 250, ''.join(b), 'Átlagsebesség kiszámítása: 100 m, 10 s')

# 5. Newton első törvénye — nyugalom (erők kiegyenlítik egymást) / jégkorong egyenletes mozgása
b = [t(14, 26, 'Nyugalomban marad', 14, INK, 'start', 'bold'),
     f'<rect x="60" y="96" width="120" height="8" fill="#94A3B8"/>', f'<rect x="72" y="104" width="8" height="30" fill="#94A3B8"/>', f'<rect x="160" y="104" width="8" height="30" fill="#94A3B8"/>',
     f'<circle cx="120" cy="80" r="16" fill="{AMBER}"/>',
     f'<line x1="120" y1="80" x2="120" y2="130" stroke="{RED}" stroke-width="3.5" marker-end="url(#ahr)"/>',
     f'<line x1="120" y1="80" x2="120" y2="32" stroke="{GREEN}" stroke-width="3.5" marker-end="url(#ahg)"/>',
     t(190, 50, 'az asztal tartóereje', 12.5, GREEN, 'start', 'bold'), t(190, 128, 'nehézségi erő', 12.5, RED, 'start', 'bold'),
     t(190, 90, 'egyforma nagyok,', 12.5, MUTED), t(190, 106, 'kiegyenlítik egymást', 12.5, MUTED),
     f'<line x1="14" y1="152" x2="346" y2="152" stroke="{GRID}" stroke-width="2"/>',
     t(14, 178, 'Egyenes vonalú egyenletes mozgás', 14, INK, 'start', 'bold'),
     f'<rect x="14" y="222" width="332" height="12" rx="3" fill="#DBEAFE"/>', t(340, 232, 'jég — alig van súrlódás', 10.5, '#1E3A8A', 'end')]
for i, x in enumerate((40, 140, 240)):
    b.append(f'<ellipse cx="{x}" cy="214" rx="18" ry="7" fill="{INK}" opacity="{0.35 + 0.3*i:.2f}"/>')
    b.append(f'<line x1="{x}" y1="198" x2="{x+50}" y2="198" stroke="{BLUE}" stroke-width="3" marker-end="url(#ahb)"/>')
b += [t(90, 262, '1 s', 12, MUTED, 'middle'), t(190, 262, '1 s', 12, MUTED, 'middle'),
      f'<path d="M40,244 L40,250 L140,250 L140,244 M140,250 L240,250 L240,244" fill="none" stroke="{MUTED}" stroke-width="1.2"/>']
out['newton-1-torveny'] = svg(360, 272, ''.join(b), 'Newton első törvénye: nyugalom és egyenletes mozgás')

# 6. Sebességrekordok (átlagsebesség = távolság / rekordidő)
rows = [('50 m gyorsúszás', 'César Cielo, 2009 · 20,91 s', 50/20.91*3.6),
        ('Maratoni futás', 'Kelvin Kiptum, 2023 · 2:00:35', 42195/7235*3.6),
        ('100 m síkfutás', 'Usain Bolt, 2009 · 9,58 s', 100/9.58*3.6),
        ('Kerékpár, egyórás rekord', 'Filippo Ganna, 2022 · 56,792 km', 56.792)]
x0, xw, vmax = 16, 290, 60
b = [t(14, 24, 'A rekordok átlagsebessége (km/h)', 14, INK, 'start', 'bold')]
for i, v in enumerate((0, 20, 40, 60)):
    x = x0 + v/vmax*xw; b.append(f'<line x1="{x}" y1="36" x2="{x}" y2="232" stroke="{GRID}"/>'); b.append(t(x, 248, v, 12, MUTED, 'middle'))
cols = ['#0EA5E9', GREEN, AMBER, BLUE]
for i, (name, who, v) in enumerate(rows):
    y = 44 + i*48
    b.append(t(x0, y+10, name, 13, INK, 'start', 'bold')); b.append(t(x0, y+24, who, 11, MUTED))
    b.append(f'<rect x="{x0}" y="{y+29}" width="{v/vmax*xw:.1f}" height="12" rx="3" fill="{cols[i]}"/>')
    b.append(t(x0 + v/vmax*xw + 6, y+40, f'{v:.1f}'.replace('.', ','), 13, INK, 'start', 'bold'))
b += [f'<rect x="10" y="258" width="340" height="44" rx="8" fill="#F1F5F9"/>',
      t(20, 276, 'Szárazföldi sebességi rekord (ThrustSSC autó, 1997):', 11.5, INK, 'start', 'bold'),
      t(20, 293, '1228 km/h — ezen a skálán több mint 20-szor ilyen hosszú sáv!', 11.5, MUTED)]
out['sebessegrekordok'] = svg(360, 310, ''.join(b), 'Sebességrekordok átlagsebessége')

import os
os.makedirs('final/phys', exist_ok=True)
for name, s in out.items():
    open(f'final/phys/{name}.svg', 'w', encoding='utf-8').write(s)
    print(name, len(s), 'bytes')
print({n: round(v, 2) for n, _, v in rows})
