-- ============================================================
-- Turul Academy — Migration v2: Seed Subjects + Topics
-- History (Történelem) + Physics (Fizika) — launch subjects
-- NAT 2020 aligned — Grades 5-12
-- ============================================================

-- ─── SUBJECTS ────────────────────────────────────────────────

insert into public.curriculum_subjects (code, name, name_hu, grade_min, grade_max) values
  ('HU-NAT-HISTORY-2020',  'History',  'Történelem', 5, 12),
  ('HU-NAT-PHYSICS-2020',  'Physics',  'Fizika',     7, 12);


-- ─── HISTORY TOPICS ──────────────────────────────────────────
-- Structure follows Hungarian NAT 2020 / Kerettanterv
-- Format: HIST-G{grade}-{unit}.{topic}

with subj as (select id from public.curriculum_subjects where code = 'HU-NAT-HISTORY-2020')

insert into public.curriculum_topics (subject_id, nat_id, title, title_hu, grade, semester, order_index) values

-- Grade 5: Ancient History & Early Hungarians
((select id from subj), 'HIST-G5-1.1', 'The Ancient Near East',              'Az ókori Közel-Kelet',             5, 1, 10),
((select id from subj), 'HIST-G5-1.2', 'Ancient Egypt',                      'Az ókori Egyiptom',                5, 1, 20),
((select id from subj), 'HIST-G5-1.3', 'Ancient Greece — City States',       'Az ókori Görögország — poliszok',  5, 1, 30),
((select id from subj), 'HIST-G5-1.4', 'Alexander the Great',                'Nagy Sándor',                      5, 1, 40),
((select id from subj), 'HIST-G5-2.1', 'Ancient Rome — Republic',            'Az ókori Róma — köztársaság',      5, 2, 50),
((select id from subj), 'HIST-G5-2.2', 'Ancient Rome — Empire',              'Az ókori Róma — császárkor',       5, 2, 60),
((select id from subj), 'HIST-G5-2.3', 'The Magyar Migration',               'A magyarok vándorlása',            5, 2, 70),
((select id from subj), 'HIST-G5-2.4', 'The Conquest of the Carpathians',    'A honfoglalás',                    5, 2, 80),

-- Grade 6: Medieval Hungary
((select id from subj), 'HIST-G6-1.1', 'St. Stephen and the Hungarian State','Szent István és az államalapítás', 6, 1, 10),
((select id from subj), 'HIST-G6-1.2', 'The Árpád Dynasty',                  'Az Árpád-ház',                     6, 1, 20),
((select id from subj), 'HIST-G6-1.3', 'The Mongol Invasion',                'A tatárjárás',                     6, 1, 30),
((select id from subj), 'HIST-G6-1.4', 'King Matthias and the Renaissance',  'Hunyadi Mátyás és a reneszánsz',   6, 1, 40),
((select id from subj), 'HIST-G6-2.1', 'The Ottoman Conquest',               'A török hódoltság',                6, 2, 50),
((select id from subj), 'HIST-G6-2.2', 'The Battle of Mohács',               'A mohácsi csata',                  6, 2, 60),
((select id from subj), 'HIST-G6-2.3', 'Three-Part Hungary',                 'A három részre szakadt ország',    6, 2, 70),
((select id from subj), 'HIST-G6-2.4', 'The Rákóczi War of Independence',    'A Rákóczi-szabadságharc',          6, 2, 80),

-- Grade 7: Early Modern Period
((select id from subj), 'HIST-G7-1.1', 'The Enlightenment',                  'A felvilágosodás',                 7, 1, 10),
((select id from subj), 'HIST-G7-1.2', 'The American Revolution',            'Az amerikai függetlenségi háború', 7, 1, 20),
((select id from subj), 'HIST-G7-1.3', 'The French Revolution',              'A francia forradalom',             7, 1, 30),
((select id from subj), 'HIST-G7-1.4', 'Napoleon Bonaparte',                 'Napóleon',                         7, 1, 40),
((select id from subj), 'HIST-G7-2.1', 'The Age of Reform in Hungary',       'A reformkor Magyarországon',       7, 2, 50),
((select id from subj), 'HIST-G7-2.2', 'István Széchenyi',                   'Széchenyi István',                 7, 2, 60),
((select id from subj), 'HIST-G7-2.3', 'Lajos Kossuth',                      'Kossuth Lajos',                    7, 2, 70),
((select id from subj), 'HIST-G7-2.4', 'The Hungarian Revolution of 1848',   'Az 1848-as forradalom',            7, 2, 80),

-- Grade 8: 19th Century & Dual Monarchy
((select id from subj), 'HIST-G8-1.1', 'The Austro-Hungarian Compromise',    'Az Osztrák-Magyar Kiegyezés',      8, 1, 10),
((select id from subj), 'HIST-G8-1.2', 'The Dual Monarchy',                  'Az Osztrák-Magyar Monarchia',      8, 1, 20),
((select id from subj), 'HIST-G8-1.3', 'Industrialisation in Hungary',       'Iparosodás Magyarországon',        8, 1, 30),
((select id from subj), 'HIST-G8-1.4', 'The Millennium Celebrations 1896',   'Az ezredévi ünnepségek',           8, 1, 40),
((select id from subj), 'HIST-G8-2.1', 'World War I — Causes',               'Az I. világháború okai',           8, 2, 50),
((select id from subj), 'HIST-G8-2.2', 'World War I — Hungary',              'Az I. világháború Magyarországon', 8, 2, 60),
((select id from subj), 'HIST-G8-2.3', 'The Treaty of Trianon',              'A trianoni békeszerződés',         8, 2, 70),
((select id from subj), 'HIST-G8-2.4', 'The Interwar Period in Hungary',     'A két világháború közötti idő',    8, 2, 80),

-- Grade 9: WW2 & Communist Hungary
((select id from subj), 'HIST-G9-1.1', 'The Rise of Fascism',                'A fasizmus terjeszkedése',         9, 1, 10),
((select id from subj), 'HIST-G9-1.2', 'World War II — Europe',              'A II. világháború Európában',      9, 1, 20),
((select id from subj), 'HIST-G9-1.3', 'World War II — Hungary',             'A II. világháború Magyarországon', 9, 1, 30),
((select id from subj), 'HIST-G9-1.4', 'The Holocaust',                      'A holokauszt',                     9, 1, 40),
((select id from subj), 'HIST-G9-2.1', 'The Cold War',                       'A hidegháború',                    9, 2, 50),
((select id from subj), 'HIST-G9-2.2', 'Communist Hungary — Rákosi Era',     'A Rákosi-korszak',                 9, 2, 60),
((select id from subj), 'HIST-G9-2.3', 'The 1956 Revolution',                'Az 1956-os forradalom',            9, 2, 70),
((select id from subj), 'HIST-G9-2.4', 'The Kádár Era',                      'A Kádár-korszak',                  9, 2, 80),

-- Grade 10: Contemporary History
((select id from subj), 'HIST-G10-1.1','The Fall of Communism',              'A kommunizmus bukása',             10, 1, 10),
((select id from subj), 'HIST-G10-1.2','The Transition of 1989 in Hungary',  'A rendszerváltás 1989-ben',        10, 1, 20),
((select id from subj), 'HIST-G10-1.3','Hungary in the European Union',      'Magyarország az Európai Unióban',  10, 1, 30),
((select id from subj), 'HIST-G10-2.1','Globalisation',                      'A globalizáció',                   10, 2, 40),
((select id from subj), 'HIST-G10-2.2','21st Century Challenges',            'A 21. század kihívásai',           10, 2, 50);


-- ─── PHYSICS TOPICS ──────────────────────────────────────────
-- Format: PHYS-G{grade}-{unit}.{topic}
-- Physics starts Grade 7 in Hungarian curriculum

with subj as (select id from public.curriculum_subjects where code = 'HU-NAT-PHYSICS-2020')

insert into public.curriculum_topics (subject_id, nat_id, title, title_hu, grade, semester, order_index) values

-- Grade 7: Introduction to Physics & Mechanics
((select id from subj), 'PHYS-G7-1.1', 'What is Physics? Measurement',        'Mi a fizika? Mérés',               7, 1, 10),
((select id from subj), 'PHYS-G7-1.2', 'Motion — Speed and Velocity',         'Mozgás — sebesség',                7, 1, 20),
((select id from subj), 'PHYS-G7-1.3', 'Uniform Motion',                      'Egyenletes mozgás',                7, 1, 30),
((select id from subj), 'PHYS-G7-1.4', 'Accelerated Motion',                  'Egyenletesen változó mozgás',      7, 1, 40),
((select id from subj), 'PHYS-G7-2.1', 'Force and Newton''s First Law',        'Erő és Newton I. törvénye',        7, 2, 50),
((select id from subj), 'PHYS-G7-2.2', 'Newton''s Second Law — F = ma',        'Newton II. törvénye — F = ma',     7, 2, 60),
((select id from subj), 'PHYS-G7-2.3', 'Newton''s Third Law',                  'Newton III. törvénye',             7, 2, 70),
((select id from subj), 'PHYS-G7-2.4', 'Gravity and Free Fall',                'Gravitáció és szabadesés',         7, 2, 80),

-- Grade 8: Energy, Heat & Waves
((select id from subj), 'PHYS-G8-1.1', 'Work and Energy',                     'Munka és energia',                 8, 1, 10),
((select id from subj), 'PHYS-G8-1.2', 'Kinetic and Potential Energy',        'Mozgási és helyzeti energia',      8, 1, 20),
((select id from subj), 'PHYS-G8-1.3', 'Conservation of Energy',              'Energiamegmaradás törvénye',       8, 1, 30),
((select id from subj), 'PHYS-G8-1.4', 'Power',                               'Teljesítmény',                     8, 1, 40),
((select id from subj), 'PHYS-G8-2.1', 'Temperature and Heat',                'Hőmérséklet és hő',                8, 2, 50),
((select id from subj), 'PHYS-G8-2.2', 'States of Matter',                    'Az anyag halmazállapotai',         8, 2, 60),
((select id from subj), 'PHYS-G8-2.3', 'Waves — Basics',                      'Hullámok alapjai',                 8, 2, 70),
((select id from subj), 'PHYS-G8-2.4', 'Sound and Acoustics',                 'Hang és akusztika',                8, 2, 80),

-- Grade 9: Optics & Electrostatics
((select id from subj), 'PHYS-G9-1.1', 'Light — Reflection and Refraction',   'Fény — visszaverődés, törés',      9, 1, 10),
((select id from subj), 'PHYS-G9-1.2', 'Lenses and Mirrors',                  'Lencsék és tükrök',                9, 1, 20),
((select id from subj), 'PHYS-G9-1.3', 'The Human Eye and Optical Devices',   'A szem és optikai eszközök',       9, 1, 30),
((select id from subj), 'PHYS-G9-2.1', 'Electric Charge',                     'Elektromos töltés',                9, 2, 40),
((select id from subj), 'PHYS-G9-2.2', 'Electric Field',                      'Elektromos mező',                  9, 2, 50),
((select id from subj), 'PHYS-G9-2.3', 'Electric Current and Voltage',        'Elektromos áram és feszültség',    9, 2, 60),
((select id from subj), 'PHYS-G9-2.4', 'Ohm''s Law and Resistance',            'Ohm törvénye és ellenállás',       9, 2, 70),

-- Grade 10: Circuits & Magnetism
((select id from subj), 'PHYS-G10-1.1','Series and Parallel Circuits',        'Soros és párhuzamos kapcsolás',    10, 1, 10),
((select id from subj), 'PHYS-G10-1.2','Electrical Power and Energy',         'Elektromos teljesítmény és energia',10, 1, 20),
((select id from subj), 'PHYS-G10-1.3','Magnetic Field',                      'Mágneses mező',                    10, 1, 30),
((select id from subj), 'PHYS-G10-1.4','Electromagnetic Induction',           'Elektromágneses indukció',         10, 1, 40),
((select id from subj), 'PHYS-G10-2.1','Alternating Current',                 'Váltóáram',                        10, 2, 50),
((select id from subj), 'PHYS-G10-2.2','Transformers',                        'Transzformátor',                   10, 2, 60),
((select id from subj), 'PHYS-G10-2.3','Electric Motors and Generators',      'Villanymotor és generátor',        10, 2, 70),

-- Grade 11: Modern Physics
((select id from subj), 'PHYS-G11-1.1','Special Relativity — basics',         'Speciális relativitás alapjai',    11, 1, 10),
((select id from subj), 'PHYS-G11-1.2','Photoelectric Effect',                'Fotoelektromos hatás',             11, 1, 20),
((select id from subj), 'PHYS-G11-1.3','Atomic Models',                       'Atommodellek',                     11, 1, 30),
((select id from subj), 'PHYS-G11-2.1','Radioactivity',                       'Radioaktivitás',                   11, 2, 40),
((select id from subj), 'PHYS-G11-2.2','Nuclear Fission and Fusion',          'Maghasadás és magfúzió',           11, 2, 50),
((select id from subj), 'PHYS-G11-2.3','Nuclear Energy',                      'Atomenergia',                      11, 2, 60);
