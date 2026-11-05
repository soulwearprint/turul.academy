"use strict";
/* Family Secret Santa — vanilla JS front end. All data comes from /api. */

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "");

const state = { status: null, tab: "years", year: null };
try { state.tab = localStorage.getItem("santa.tab") || "years"; } catch (_) {}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
  });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    if (res.status === 401 && !opts.noAuthRedirect) { await boot(); }
    const detail = data?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || res.statusText);
  }
  return data;
}

/* ── Dialog helper: resolves with {action, form} ───────────────────────── */
function dialog(bodyHtml, buttons) {
  const dlg = $("#dlg");
  $("#dlg-body").innerHTML = bodyHtml;
  $("#dlg-actions").innerHTML = buttons
    .map((b) => `<button value="${esc(b.value)}" class="${esc(b.cls || "")}" ${b.formnovalidate ? "formnovalidate" : ""}>${esc(b.label)}</button>`)
    .join("");
  dlg.returnValue = "";
  dlg.showModal();
  return new Promise((resolve) => {
    dlg.addEventListener("close", () => resolve({ action: dlg.returnValue, form: $("#dlg-form") }), { once: true });
  });
}
const alertBox = (html) => dialog(html, [{ label: "OK", value: "ok" }]);

/* ── Boot / auth screens ───────────────────────────────────────────────── */
async function boot() {
  state.status = await api("/api/status", { noAuthRedirect: true });
  const s = state.status;
  $("#who").innerHTML = s.logged_in
    ? `Admin: <b>${esc(s.admin.name)}</b> &nbsp;<button class="small secondary" id="logout">Log out</button>`
    : "";
  if (s.logged_in) $("#logout").onclick = async () => { await api("/api/logout", { method: "POST" }); boot(); };
  if (!s.setup_done) return renderSetup();
  if (!s.logged_in) return renderLogin();
  renderMain();
}

function renderSetup() {
  $("#app").innerHTML = `
    <section class="card">
      <h2>Welcome! Create the first admin</h2>
      <p class="muted">The first admin is mandatory. Admins manage the family list, run the draw,
      send the postcards and — only if really needed — can unlock who drew whom (every unlock is logged).
      You can add up to 4 more admins later.</p>
      <form id="f">
        <div class="row">
          <div><label>Your name</label><input name="name" required maxlength="60"></div>
          <div><label>Password (min. 6 characters)</label><input name="password" type="password" required minlength="6"></div>
          <button>Create admin</button>
        </div>
        <p class="hint">⚠️ There is no password reset: the matches are encrypted with the admins' passwords.
        Add a second admin later as a backup.</p>
        <div class="err" id="err"></div>
      </form>
    </section>`;
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try { await api("/api/setup", { method: "POST", body: Object.fromEntries(fd) }); boot(); }
    catch (err) { $("#err").textContent = err.message; }
  };
}

function renderLogin() {
  $("#app").innerHTML = `
    <section class="card">
      <h2>Admin login</h2>
      <form id="f">
        <div class="row">
          <div><label>Admin name</label><input name="name" required autocomplete="username"></div>
          <div><label>Password</label><input name="password" type="password" required autocomplete="current-password"></div>
          <button>Log in</button>
        </div>
        <div class="err" id="err"></div>
      </form>
    </section>`;
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/login", { method: "POST", body: Object.fromEntries(new FormData(e.target)), noAuthRedirect: true }); boot(); }
    catch (err) { $("#err").textContent = err.message; }
  };
}

/* ── Main shell ────────────────────────────────────────────────────────── */
const TABS = { years: "🎁 Years & draw", family: "👪 Family", admins: "🔑 Admins", log: "📜 Log" };

function renderMain() {
  const modeBanner = state.status.mail_mode === "outbox"
    ? `<div class="banner info">📭 <b>Outbox mode:</b> SMTP is not configured, so postcards are saved as .eml files
       in <code>data/outbox/</code> instead of being e-mailed. See README to set up sending.</div>` : "";
  $("#app").innerHTML = `${modeBanner}
    <nav class="tabs">${Object.entries(TABS).map(([k, v]) =>
      `<button data-tab="${k}" class="${state.tab === k ? "active" : ""}">${v}</button>`).join("")}</nav>
    <div id="view"></div>`;
  document.querySelectorAll("nav.tabs button").forEach((b) => (b.onclick = () => {
    state.tab = b.dataset.tab;
    try { localStorage.setItem("santa.tab", state.tab); } catch (_) {}
    renderMain();
  }));
  ({ years: viewYears, family: viewFamily, admins: viewAdmins, log: viewLog })[state.tab]().catch((e) => {
    $("#view").innerHTML = `<p class="err">${esc(e.message)}</p>`;
  });
}

/* ── Family ────────────────────────────────────────────────────────────── */
async function viewFamily() {
  const members = await api("/api/members");
  const active = members.filter((m) => !m.archived), archived = members.filter((m) => m.archived);
  const rowHtml = (m) => `<tr>
      <td>${esc(m.name)}</td><td>${esc(m.email)}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="small secondary" data-edit="${m.id}">${m.archived ? "Restore / edit" : "Edit"}</button>
        ${m.archived ? "" : `<button class="small secondary" data-del="${m.id}">Remove</button>`}
      </td></tr>`;
  $("#view").innerHTML = `
    <section class="card">
      <h2>Family members</h2>
      <form id="add" class="row">
        <div><label>Name</label><input name="name" required maxlength="80"></div>
        <div><label>E-mail (only this person should read it)</label><input name="email" type="email" required></div>
        <button>Add</button>
      </form>
      <div class="err" id="err"></div>
      <table style="margin-top:14px"><thead><tr><th>Name</th><th>E-mail</th><th></th></tr></thead>
        <tbody>${active.map(rowHtml).join("") || `<tr><td colspan="3" class="muted">Nobody yet.</td></tr>`}</tbody></table>
      ${archived.length ? `<h3 class="muted">Archived (kept for past years)</h3>
        <table><tbody>${archived.map(rowHtml).join("")}</tbody></table>` : ""}
    </section>`;
  $("#add").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/members", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }); viewFamily(); }
    catch (err) { $("#err").textContent = err.message; }
  };
  document.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = async () => {
    const m = members.find((x) => x.id == b.dataset.edit);
    const r = await dialog(`<h2>Edit ${esc(m.name)}</h2>
      <label>Name</label><input name="name" value="${esc(m.name)}" required>
      <label>E-mail</label><input name="email" type="email" value="${esc(m.email)}" required>`,
      [{ label: "Cancel", value: "", cls: "secondary", formnovalidate: true }, { label: "Save", value: "save" }]);
    if (r.action !== "save") return;
    try { await api(`/api/members/${m.id}`, { method: "PUT", body: Object.fromEntries(new FormData(r.form)) }); }
    catch (err) { await alertBox(`<p class="err">${esc(err.message)}</p>`); }
    viewFamily();
  }));
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    const m = members.find((x) => x.id == b.dataset.del);
    const r = await dialog(`<h2>Remove ${esc(m.name)}?</h2><p>If they took part in a past year they are archived
      (history is kept) and won't be added to new years. This does not change any existing draw —
      remove them from a year's participant list for that.</p>`,
      [{ label: "Cancel", value: "", cls: "secondary" }, { label: "Remove", value: "del" }]);
    if (r.action === "del") { await api(`/api/members/${m.id}`, { method: "DELETE" }); viewFamily(); }
  }));
}

/* ── Admins ────────────────────────────────────────────────────────────── */
async function viewAdmins() {
  const admins = await api("/api/admins");
  $("#view").innerHTML = `
    <section class="card">
      <h2>Admins (${admins.length}/5)</h2>
      <p class="muted">Admins can manage everything and unlock the matches. Admin #1 is permanent.
        Each unlock is recorded in the log, so everyone can see if somebody peeked.</p>
      <table><thead><tr><th>#</th><th>Name</th><th>Since</th><th></th></tr></thead><tbody>
        ${admins.map((a) => `<tr><td>${a.slot}</td><td>${esc(a.name)}${a.slot === 1 ? ' <span class="pill">mandatory</span>' : ""}</td>
          <td class="muted">${fmt(a.created_at)}</td>
          <td style="text-align:right">${a.slot === 1 ? "" : `<button class="small secondary" data-del="${a.id}">Remove</button>`}</td></tr>`).join("")}
      </tbody></table>
      ${admins.length < 5 ? `<h3>Add an admin</h3>
        <form id="add" class="row">
          <div><label>Name</label><input name="name" required maxlength="60"></div>
          <div><label>Initial password (they should change it)</label><input name="password" type="password" minlength="6" required></div>
          <button>Add admin</button>
        </form>` : ""}
      <div class="err" id="err"></div>
    </section>
    <section class="card">
      <h2>Change my password</h2>
      <form id="pw" class="row">
        <div><label>Current password</label><input name="current" type="password" required></div>
        <div><label>New password</label><input name="new" type="password" minlength="6" required></div>
        <button>Change</button>
      </form>
      <div id="pwmsg" class="hint"></div>
    </section>`;
  if ($("#add")) $("#add").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/admins", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }); viewAdmins(); }
    catch (err) { $("#err").textContent = err.message; }
  };
  $("#pw").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/admins/me/password", { method: "POST", body: Object.fromEntries(new FormData(e.target)) });
      e.target.reset(); $("#pwmsg").textContent = "Password changed."; }
    catch (err) { $("#pwmsg").textContent = err.message; }
  };
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    const r = await dialog(`<h2>Remove this admin?</h2>`, [{ label: "Cancel", value: "", cls: "secondary" }, { label: "Remove", value: "del" }]);
    if (r.action === "del") { await api(`/api/admins/${b.dataset.del}`, { method: "DELETE" }); viewAdmins(); }
  }));
}

/* ── Log ───────────────────────────────────────────────────────────────── */
async function viewLog() {
  const rows = await api("/api/audit");
  $("#view").innerHTML = `<section class="card"><h2>Activity log</h2>
    <table><thead><tr><th>When</th><th>Admin</th><th>What</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td class="muted" style="white-space:nowrap">${fmt(r.at)}</td><td>${esc(r.admin_name)}</td>
      <td>${r.action === "MATCHES REVEALED" ? `<span class="pill bad">🔓 ${esc(r.action)}</span>` : esc(r.action)}
      <span class="muted">${esc(r.detail)}</span></td></tr>`).join("")}
    </tbody></table></section>`;
}

/* ── Years ─────────────────────────────────────────────────────────────── */
async function viewYears() {
  const years = await api("/api/years");
  const thisYear = new Date().getFullYear();
  if (!state.year || !years.some((y) => y.year === state.year)) state.year = years[0]?.year ?? null;
  $("#view").innerHTML = `
    <section class="card">
      <div class="row">
        <div><label>Year</label>
          <select id="ysel">${years.map((y) => `<option value="${y.year}" ${y.year === state.year ? "selected" : ""}>
            ${y.year} — ${y.participants} people${y.drawn ? (y.in_sync ? " · drawn" : " · ⚠ list changed") : ""}</option>`).join("")
            || "<option>No years yet</option>"}</select></div>
        <form id="newy" class="row" style="flex:2 1 260px">
          <div><label>Start a new year (copies the last year's list)</label>
            <input name="year" type="number" min="2000" max="2200" value="${years.some((y) => y.year === thisYear) ? thisYear + 1 : thisYear}"></div>
          <button class="secondary">Create</button>
        </form>
      </div>
      <div class="err" id="err"></div>
    </section>
    <div id="year"></div>`;
  $("#ysel").onchange = (e) => { state.year = +e.target.value; renderYear(); };
  $("#newy").onsubmit = async (e) => {
    e.preventDefault();
    const year = +new FormData(e.target).get("year");
    try { await api("/api/years", { method: "POST", body: { year } }); state.year = year; viewYears(); }
    catch (err) { $("#err").textContent = err.message; }
  };
  if (state.year) renderYear();
}

async function renderYear() {
  const [y, members] = await Promise.all([api(`/api/years/${state.year}`), api("/api/members")]);
  const inYear = new Set(y.participants.map((p) => p.id));
  const choosable = members.filter((m) => !m.archived || inYear.has(m.id));
  const pending = y.participants.filter((p) => p.has_match && !p.notified_at).length;

  let statusHtml;
  if (!y.drawn) {
    statusHtml = `<div class="banner info">Names have not been drawn yet for ${y.year}.</div>
      <button id="draw" ${y.participants.length < 2 ? "disabled" : ""}>🎲 Draw names for ${y.participants.length} people</button>`;
  } else if (!y.in_sync) {
    statusHtml = `<div class="banner">⚠ The participant list changed after the draw.
      ${y.added.length ? `<br>Joined: <b>${y.added.map((p) => esc(p.name)).join(", ")}</b>` : ""}
      ${y.removed.length ? `<br>Left: <b>${y.removed.map((p) => esc(p.name)).join(", ")}</b>` : ""}
      <br>Choose who should be reshuffled before sending postcards.</div>
      <button id="reshuffle">Choose who to reshuffle…</button>`;
  } else {
    statusHtml = `<div class="banner info">✅ Names are drawn and secret. ${pending ? `${pending} postcard(s) not sent yet.` : "All postcards sent."}</div>
      <div class="actions">
        <button id="sendall" ${pending ? "" : "disabled"}>📮 Send ${pending} pending postcard(s)</button>
        <button id="reshuffle" class="secondary">Reshuffle…</button>
        <button id="reveal" class="secondary">🔓 Unlock matches</button>
      </div>`;
  }

  $("#year").innerHTML = `
    <section class="card">
      <h2>Christmas ${y.year}</h2>
      ${statusHtml}
    </section>

    <section class="card">
      <h2>Who takes part in ${y.year}?</h2>
      <form id="parts">
        <div class="checks">${choosable.map((m) => `<label><input type="checkbox" name="m" value="${m.id}" ${inYear.has(m.id) ? "checked" : ""}>
          ${esc(m.name)}</label>`).join("") || `<span class="muted">Add family members in the Family tab first.</span>`}</div>
        <div class="actions"><button class="secondary">Save participant list</button></div>
      </form>
    </section>

    ${y.drawn ? `<section class="card">
      <h2>Postcards</h2>
      <p class="hint">Each person gets their own e-mail; nobody else is in To/CC/BCC.
        The admin sending them never sees the content.</p>
      <table><thead><tr><th>Name</th><th>Status</th><th></th></tr></thead><tbody>
      ${y.participants.map((p) => `<tr><td>${esc(p.name)}</td>
        <td>${!p.has_match ? '<span class="pill bad">not in draw</span>'
          : p.notified_at ? `<span class="pill ok">sent ${fmt(p.notified_at)}</span>` : '<span class="pill wait">not sent</span>'}</td>
        <td style="text-align:right">${p.has_match && y.in_sync ? `<button class="small secondary" data-send="${p.id}">${p.notified_at ? "Resend" : "Send"}</button>` : ""}</td></tr>`).join("")}
      </tbody></table>
      <p class="hint"><a href="/api/postcard/preview" target="_blank" rel="noopener">Preview the postcard design</a> (sample names only)</p>
    </section>` : ""}

    <section class="card">
      <h2>Details on the postcard</h2>
      <form id="details">
        <div class="row">
          <div><label>Gift budget</label><input name="budget" value="${esc(y.budget)}" placeholder="e.g. €30"></div>
          <div><label>Gift exchange</label><input name="exchange_date" value="${esc(y.exchange_date)}" placeholder="e.g. 24 Dec, at Grandma's"></div>
        </div>
        <label>Extra note from Santa (optional)</label><textarea name="note" rows="2" maxlength="600">${esc(y.note)}</textarea>
        <div class="actions"><button class="secondary">Save details</button><span id="dmsg" class="hint"></span></div>
      </form>
      <p class="hint" style="margin-top:14px"><button class="small secondary" id="dely">Delete ${y.year}</button></p>
    </section>`;

  $("#details").onsubmit = async (e) => {
    e.preventDefault();
    await api(`/api/years/${y.year}`, { method: "PUT", body: Object.fromEntries(new FormData(e.target)) });
    $("#dmsg").textContent = "Saved.";
  };
  $("#parts").onsubmit = async (e) => {
    e.preventDefault();
    const ids = [...e.target.querySelectorAll("input[name=m]:checked")].map((i) => +i.value);
    const res = await api(`/api/years/${y.year}/participants`, { method: "PUT", body: { member_ids: ids } });
    await viewYears();
    if (res.needs_reshuffle) await reshuffleDialog();
  };
  $("#dely").onclick = async () => {
    const r = await dialog(`<h2>Delete ${y.year}?</h2><p>This removes the participant list and all matches for ${y.year}. It cannot be undone.</p>`,
      [{ label: "Cancel", value: "", cls: "secondary" }, { label: "Delete", value: "del" }]);
    if (r.action === "del") { await api(`/api/years/${y.year}`, { method: "DELETE" }); state.year = null; viewYears(); }
  };
  if ($("#draw")) $("#draw").onclick = async () => {
    const r = await dialog(`<h2>Draw names for ${y.year}?</h2><p>Everyone in the list (${y.participants.length} people) gets exactly one
      giftee, never themselves. Nobody — including you — will see the result.</p>`,
      [{ label: "Cancel", value: "", cls: "secondary" }, { label: "🎲 Draw", value: "go" }]);
    if (r.action !== "go") return;
    try { await api(`/api/years/${y.year}/draw`, { method: "POST", body: {} }); }
    catch (err) { return alertBox(`<p class="err">${esc(err.message)}</p>`); }
    await viewYears();
    await offerSend("Names drawn! 🎉");
  };
  if ($("#reshuffle")) $("#reshuffle").onclick = reshuffleDialog;
  if ($("#sendall")) $("#sendall").onclick = () => sendPostcards(null);
  if ($("#reveal")) $("#reveal").onclick = revealDialog;
  document.querySelectorAll("[data-send]").forEach((b) => (b.onclick = () => sendPostcards([+b.dataset.send])));
}

async function reshuffleDialog() {
  const y = await api(`/api/years/${state.year}`);
  const added = new Set(y.added.map((p) => p.id));
  const others = y.participants.filter((p) => !added.has(p.id));
  const r = await dialog(`
    <h2>Who should be reshuffled?</h2>
    ${y.added.length || y.removed.length ? `<div class="banner">
      ${y.added.length ? `Joined: <b>${y.added.map((p) => esc(p.name)).join(", ")}</b> — always included.<br>` : ""}
      ${y.removed.length ? `Left: <b>${y.removed.map((p) => esc(p.name)).join(", ")}</b> — whoever was giving to them must
        get a new giftee. They are included automatically <b>without being shown</b>, mixed with a few random people,
        so nobody can work out who had whom.` : ""}</div>` : ""}
    <label style="display:flex;gap:8px;align-items:center;color:inherit;margin:10px 0">
      <input type="checkbox" name="everyone" style="width:auto"> <b>Reshuffle everyone</b> (completely new draw)</label>
    <p class="hint">…or tick the people who should get a new giftee. Everyone else keeps theirs (useful if gifts are already bought).</p>
    <div class="checks" id="rs-checks">
      ${y.added.map((p) => `<label><input type="checkbox" checked disabled> ${esc(p.name)} <span class="pill">new</span></label>`).join("")}
      ${others.map((p) => `<label><input type="checkbox" name="sel" value="${p.id}"> ${esc(p.name)}</label>`).join("")}
    </div>
    <p class="hint">Everyone who is reshuffled gets a fresh postcard (even if they happen to draw the same person again).</p>`,
    [{ label: "Cancel", value: "", cls: "secondary" }, { label: "Reshuffle", value: "go" }]);
  if (r.action !== "go") return;
  const everyone = r.form.elements.everyone.checked;
  const selected_ids = [...r.form.querySelectorAll("input[name=sel]:checked")].map((i) => +i.value);
  let res;
  try { res = await api(`/api/years/${state.year}/draw`, { method: "POST", body: { everyone, selected_ids, confirm: true } }); }
  catch (err) { return alertBox(`<p class="err">${esc(err.message)}</p>`); }
  await viewYears();
  await offerSend(`Reshuffled ${res.reshuffled} of ${res.total} people${res.hidden_count ? ` (including ${res.hidden_count} not shown, for secrecy)` : ""}.`);
}

async function offerSend(headline) {
  const y = await api(`/api/years/${state.year}`);
  const pending = y.participants.filter((p) => p.has_match && !p.notified_at).length;
  if (!pending) return alertBox(`<h2>${esc(headline)}</h2>`);
  const r = await dialog(`<h2>${esc(headline)}</h2><p>${pending} postcard(s) are ready. Send them now?</p>`,
    [{ label: "Later", value: "", cls: "secondary" }, { label: `📮 Send ${pending}`, value: "send" }]);
  if (r.action === "send") await sendPostcards(null);
}

async function sendPostcards(ids) {
  let res;
  try { res = await api(`/api/years/${state.year}/notify`, { method: "POST", body: { member_ids: ids } }); }
  catch (err) { return alertBox(`<p class="err">${esc(err.message)}</p>`); }
  const ok = res.results.filter((x) => x.ok), bad = res.results.filter((x) => !x.ok);
  await alertBox(`<h2>${res.mode === "outbox" ? "📭 Saved to outbox" : "📮 Postcards sent"}</h2>
    <p>${ok.length} ${res.mode === "outbox" ? "saved" : "sent"}${bad.length ? `, <span class="err">${bad.length} failed</span>` : ""}.</p>
    ${bad.map((b) => `<p class="err">${esc(b.name)}: ${esc(b.error)}</p>`).join("")}`);
  renderYear();
}

async function revealDialog() {
  const r = await dialog(`<h2>🔓 Unlock the matches for ${state.year}?</h2>
    <p>This shows who drew whom — the secret is spoiled for you. It is recorded in the log, visible to all admins.</p>
    <label>Re-enter your password</label><input name="password" type="password" required autocomplete="current-password">`,
    [{ label: "Cancel", value: "", cls: "secondary", formnovalidate: true }, { label: "Unlock", value: "go" }]);
  if (r.action !== "go") return;
  let pairs;
  try { pairs = await api(`/api/years/${state.year}/reveal`, { method: "POST", body: { password: r.form.elements.password.value } }); }
  catch (err) { return alertBox(`<p class="err">${esc(err.message)}</p>`); }
  await alertBox(`<h2>Matches ${state.year}</h2>
    <table class="reveal"><thead><tr><th>Secret Santa</th><th>gives to</th></tr></thead><tbody>
    ${pairs.map((p) => `<tr><td>${esc(p.giver)}</td><td>${esc(p.receiver)}</td></tr>`).join("")}</tbody></table>`);
}

boot();
