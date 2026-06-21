-- v4_seed_history_g11_g12
-- Supabase project: tqsrwhvvghryycgsxfsj (Turul ACADEMY)
--
-- Fills the curriculum gap: History was seeded only for grades 5-10. Hungarian
-- NAT 2020 history runs through grade 12, so the grade tabs were missing 11-12.
-- 16 topics (8 per grade): dualism → Trianon → WWII (G11), Cold War → 1956 →
-- regime change → EU (G12). subject_id is HU-NAT-HISTORY-2020.

INSERT INTO public.curriculum_topics (subject_id, nat_id, title, title_hu, grade, semester, order_index) VALUES
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-1.1','The Age of Dualism','A dualizmus kora',11,1,10),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-1.2','The Compromise of 1867 and Modernisation','A kiegyezés és a polgárosodás',11,1,20),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-1.3','World War I','Az első világháború',11,1,30),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-1.4','The 1918–1919 Revolutions and the Treaty of Trianon','Az 1918–1919-es forradalmak és Trianon',11,1,40),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-2.1','The Horthy Era','A Horthy-korszak',11,2,50),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-2.2','The Great Depression','A nagy gazdasági világválság',11,2,60),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-2.3','World War II','A második világháború',11,2,70),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G11-2.4','Hungary in World War II and the Holocaust','Magyarország a második világháborúban és a holokauszt',11,2,80),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-1.1','The Cold War','A hidegháború',12,1,10),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-1.2','The Emergence of the Bipolar World','A kétpólusú világ kialakulása',12,1,20),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-1.3','The Rákosi Era','A Rákosi-korszak',12,1,30),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-1.4','The 1956 Revolution and Freedom Fight','Az 1956-os forradalom és szabadságharc',12,1,40),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-2.1','The Kádár Era','A Kádár-korszak',12,2,50),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-2.2','The Regime Change','A rendszerváltás',12,2,60),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-2.3','The Third Hungarian Republic','A harmadik Magyar Köztársaság',12,2,70),
('b5122740-fbd9-4c78-b3dd-c36172565e07','HIST-G12-2.4','Hungary in the European Union and Globalisation','Magyarország az Európai Unióban és a globalizáció',12,2,80);
