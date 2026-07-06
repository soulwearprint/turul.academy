/**
 * Turul Academy — translations
 * Primary: Hungarian (hu)
 * Secondary: English (en)
 *
 * Usage:
 *   const { t, lang, setLang } = useLang()
 *   t('nav.home')  →  'Ma' (hu) or 'Today' (en)
 */

export const translations = {
  // ── Navigation ───────────────────────────────────────────
  'nav.home':          { hu: 'Ma',          en: 'Today' },
  'nav.subjects':      { hu: 'Tananyag',    en: 'Study' },
  'nav.progress':      { hu: 'Haladás',     en: 'Progress' },
  'nav.turul':         { hu: 'Turul',       en: 'Turul' },
  'nav.profile':       { hu: 'Profil',      en: 'Profile' },

  // ── Auth ─────────────────────────────────────────────────
  'auth.login':        { hu: 'Bejelentkezés',    en: 'Sign in' },
  'auth.register':     { hu: 'Regisztráció',     en: 'Register' },
  'auth.email':        { hu: 'E-mail',           en: 'Email' },
  'auth.password':     { hu: 'Jelszó',           en: 'Password' },
  'auth.submit.login': { hu: 'Bejelentkezés',    en: 'Sign in' },
  'auth.submit.reg':   { hu: 'Fiók létrehozása', en: 'Create account' },
  'auth.loading':      { hu: '...',              en: '...' },
  'auth.tagline':      { hu: 'A te AI tanulótársad, aki együtt fejlődik veled — az 5. osztálytól az érettségiig.',
                         en: 'Your AI study companion that grows with you — from Grade 5 to graduation.' },
  'auth.legal':        { hu: 'A folytatással elfogadod a feltételeket és az adatkezelési tájékoztatót.',
                         en: 'By continuing you accept the Terms and Privacy Policy.' },

  // ── Onboarding ───────────────────────────────────────────
  'onboard.name.q':       { hu: 'Hogy szólítsunk?',           en: 'What should we call you?' },
  'onboard.name.ph':      { hu: 'Beceneved',                  en: 'Your nickname' },
  'onboard.grade.q':      { hu: 'Melyik osztályba jársz?',    en: 'Which grade are you in?' },
  'onboard.mode.q':       { hu: 'Hogyan tanulsz szívesebben?',en: 'How do you prefer to learn?' },
  'onboard.mode.hint':    { hu: 'Ezt bármikor megváltoztathatod.', en: 'You can change this any time.' },
  'onboard.next':         { hu: 'Tovább →',    en: 'Next →' },
  'onboard.back':         { hu: '← Vissza',    en: '← Back' },
  'onboard.start':        { hu: 'Kezdjük el! 🚀', en: "Let's go! 🚀" },

  // ── Mode names ───────────────────────────────────────────
  'mode.text':    { hu: 'Szöveg',   en: 'Text' },
  'mode.story':   { hu: 'Történet', en: 'Story' },
  'mode.visual':  { hu: 'Vizuális', en: 'Visual' },
  'mode.quiz':    { hu: 'Kvíz',     en: 'Quiz' },

  // ── Mode descriptions ────────────────────────────────────
  'mode.text.desc':   { hu: 'Strukturált magyarázat — lépésről lépésre',         en: 'Structured explanation — step by step' },
  'mode.story.desc':  { hu: 'Ugyanaz az anyag, élményszerű elbeszélésként',       en: 'Same content told as a living narrative' },
  'mode.visual.desc': { hu: 'Térképek, diagramok, idővonalak magyarázattal',      en: 'Maps, diagrams, timelines with explanations' },
  'mode.quiz.desc':   { hu: '4 kérdés az anyag ellenőrzéséhez',                  en: '4 questions to check your understanding' },

  // ── Home ─────────────────────────────────────────────────
  'home.greeting':      { hu: 'Üdv vissza,',   en: 'Welcome back,' },
  'home.signout':       { hu: 'Kijelentkezés',  en: 'Sign out' },
  'home.streak':        { hu: '{n} napos sorozat', en: '{n}-day streak' },
  'home.continue.label':{ hu: 'Folytasd ott, ahol abbahagytad', en: 'Pick up where you left off' },
  'home.continue.start':{ hu: 'Kezdj el tanulni', en: 'Start learning' },
  'home.continue.cta':  { hu: 'Tanulás folytatása', en: 'Continue learning' },
  'home.turul.new':     { hu: 'Szia! Én Turul vagyok. Tanuljunk együtt!', en: "Hi! I'm Turul. Let's learn together!" },
  'home.turul.back':    { hu: 'Jó újra látni! Készen állsz a mai leckére?', en: 'Good to see you! Ready for today?' },
  'home.turul.streak':  { hu: 'Szuper sorozat! Így tovább! 🔥', en: 'Amazing streak! Keep it up! 🔥' },
  'home.xp.total':      { hu: 'XP összesen',    en: 'Total XP' },
  'home.lessons.done':  { hu: 'Lecke kész',     en: 'Lessons done' },
  'home.subjects.title':{ hu: 'Tantárgyaim',    en: 'My subjects' },
  'home.subjects.add':  { hu: '+ Hozzáadás',    en: '+ Add' },
  'home.no.subjects':   { hu: 'Még nem iratkoztál be egy tantárgyra sem.', en: "You haven't enrolled in any subjects yet." },
  'home.choose.subject':{ hu: 'Tantárgy választás', en: 'Choose a subject' },
  'home.daily.tip.title':{ hu: '💡 Napi tipp',  en: '💡 Daily tip' },
  'home.daily.tip.body': { hu: 'Próbáld ki a Történet módot — ugyanazt az anyagot élményszerű narratívában tanulhatod meg!',
                           en: 'Try Story mode — learn the same content as an immersive narrative!' },

  // ── Subjects ─────────────────────────────────────────────
  'subjects.title':     { hu: 'Tantárgyak',       en: 'Subjects' },
  'subjects.subtitle':  { hu: 'Válassz, ami érdekel', en: 'Choose what interests you' },
  'subjects.open':      { hu: 'Megnyitás →',      en: 'Open →' },
  'subjects.enrol':     { hu: '+ Feliratkozás',   en: '+ Enrol' },
  'subjects.grade.range': { hu: '. osztály',      en: '. grade' },

  // ── Topics ───────────────────────────────────────────────
  'topics.all':         { hu: 'Összes',    en: 'All' },
  'topics.count':       { hu: 'téma',      en: 'topics' },
  'topics.grade':       { hu: '. osztály', en: '. grade' },
  'topics.empty':       { hu: 'Nincs elérhető téma.', en: 'No topics available.' },

  // ── Topic detail ─────────────────────────────────────────
  'topic.modes.title':  { hu: 'Tanulási módok',   en: 'Learning modes' },
  'topic.no.lessons':   { hu: 'Ehhez a témához még nincs jóváhagyott lecke.', en: 'No approved lessons for this topic yet.' },
  'topic.coming.soon':  { hu: 'Hamarosan!',        en: 'Coming soon!' },
  'topic.minutes':      { hu: 'kb. {n} perc',      en: 'approx. {n} min' },
  'topic.semester':     { hu: '. félév',            en: '. semester' },
  'topic.done':         { hu: 'Kész',               en: 'Done' },
  'topic.progress':     { hu: '{done}/{total} kész', en: '{done}/{total} done' },

  // ── Lesson player ────────────────────────────────────────
  'lesson.key.term':    { hu: 'Kulcsfogalom',  en: 'Key term' },
  'lesson.next':        { hu: '→',             en: '→' },
  'lesson.prev':        { hu: '←',             en: '←' },
  'lesson.finish':      { hu: 'Kész ✓',        en: 'Done ✓' },
  'lesson.done.title':  { hu: 'Kész!',         en: 'Done!' },
  'lesson.done.sub':    { hu: 'Lecke befejezve', en: 'Lesson complete' },
  'lesson.empty':       { hu: 'Nincs megjeleníthető tartalom.', en: 'No content to display.' },
  'lesson.loading':     { hu: 'Betöltés...',    en: 'Loading...' },

  // ── Quiz ─────────────────────────────────────────────────
  'quiz.question.label': { hu: '. kérdés',    en: '. question' },
  'quiz.next':           { hu: 'Következő →', en: 'Next →' },
  'quiz.submit':         { hu: 'Beadás ✓',    en: 'Submit ✓' },
  'quiz.back':           { hu: '←',           en: '←' },
  'quiz.results.correct':{ hu: ' / {total} helyes válasz', en: ' / {total} correct' },
  'quiz.results.back':   { hu: 'Vissza a témához', en: 'Back to topic' },
  'quiz.your.answer':    { hu: 'Te:',           en: 'You:' },
  'quiz.right.answer':   { hu: 'Helyes:',       en: 'Correct:' },
  'quiz.no.answer':      { hu: '(nem válaszoltál)', en: '(no answer)' },

  // ── Progress ─────────────────────────────────────────────
  'progress.title':     { hu: 'Haladásom',     en: 'My progress' },
  'progress.level':     { hu: '. szint',        en: '. level' },
  'progress.xp.total':  { hu: 'XP összesen',   en: 'Total XP' },
  'progress.xp.to.next':{ hu: '/100 XP a következő szintig', en: '/100 XP to next level' },
  'progress.lessons':   { hu: 'Kész lecke',    en: 'Done lessons' },
  'progress.badges':    { hu: 'Kitűző',        en: 'Badges' },
  'progress.subjects.title': { hu: 'Tantárgyak szerint', en: 'By subject' },
  'progress.badges.title':   { hu: 'Kitűzők',            en: 'Badges' },

  // ── Profile ──────────────────────────────────────────────
  'profile.title':       { hu: 'Profil',                 en: 'Profile' },
  'profile.name':        { hu: 'Neved',                  en: 'Your name' },
  'profile.grade':       { hu: 'Évfolyam',               en: 'Grade' },
  'profile.mode':        { hu: 'Kedvenc tanulási mód',   en: 'Preferred learning mode' },
  'profile.save':        { hu: 'Mentés',                 en: 'Save' },
  'profile.saved':       { hu: 'Mentve',                 en: 'Saved' },
  'profile.stage.hint':  { hu: 'A Turulod fejlődési szintje az évfolyamodhoz igazodik.',
                           en: "Your Turul's stage follows your grade." },

  // ── Turul companion ──────────────────────────────────────
  'companion.grade.title': { hu: 'Évfolyam módosítása',  en: 'Change your grade' },
  'companion.grade.hint':  { hu: 'A Turulod ettől fejlődik a következő szintre.',
                             en: 'This is what evolves your Turul to the next stage.' },
  'companion.stage':     { hu: 'Jelenlegi fejlődési szint', en: 'Current evolution stage' },
  'companion.journey':   { hu: 'A Turulod útja',  en: "Your Turul's journey" },
  'companion.journey.sub': { hu: 'A Turul veled együtt fejlődik az 5. osztálytól az érettségiig.',
                             en: 'Your Turul grows with you from Grade 5 to graduation.' },
  'companion.customize.title': { hu: 'Szabd személyre a Turulod', en: 'Make your Turul yours' },
  'companion.customize.soon':  { hu: 'Színek, kiegészítők és hátterek hamarosan — tanulással oldhatod fel őket.',
                                 en: 'Colours, accessories and backgrounds coming soon — unlock them by learning.' },
  'companion.color':     { hu: 'Szín',            en: 'Colour' },
  'companion.accessory': { hu: 'Kiegészítő',      en: 'Accessory' },
  'companion.more.soon': { hu: 'Több kiegészítő és háttér hamarosan — tanulással oldhatod fel őket.',
                           en: 'More accessories and backgrounds coming soon — unlock them by learning.' },

  // ── Common ───────────────────────────────────────────────
  'common.loading':     { hu: 'Betöltés...',   en: 'Loading...' },
  'common.back':        { hu: '←',             en: '←' },
  'common.close':       { hu: '✕',             en: '✕' },
  'common.grade':       { hu: '. osztály',     en: '. grade' },
  'common.cancel':      { hu: 'Mégse',         en: 'Cancel' },

  // ── Profile ──────────────────────────────────────────────
  'profile.signout.confirm': { hu: 'Biztosan kijelentkezel?', en: 'Sign out of your account?' },
  'profile.signout.confirm.cta': { hu: 'Igen, kijelentkezés', en: 'Yes, sign out' },
}

/** Resolve a translation key, with optional {n}, {total} interpolation */
export function translate(key, lang, vars = {}) {
  const entry = translations[key]
  if (!entry) return key  // fallback: show the key itself
  let str = entry[lang] ?? entry['hu'] ?? key
  for (const [k, v] of Object.entries(vars)) {
    str = str.replace(`{${k}}`, v)
  }
  return str
}
