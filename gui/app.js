import sqlite3InitModule from "./jswasm/index.mjs";

const TYPE_FLAGS = ["bookmark", "post", "reply", "repost", "like"];
const TYPE_COL = {
  bookmark: "is_bookmark",
  post: "is_post",
  reply: "is_reply",
  repost: "is_repost",
  like: "is_like",
};
const COLS = [
  "id",
  "created_at",
  "author_username",
  "author_name",
  "url",
  "summary",
  "keywords",
  "text",
  "enriched_at",
  "folder",
  "bookmark_category",
  "is_bookmark",
  "is_post",
  "is_reply",
  "is_repost",
  "is_like",
];
const ALL = 105;

globalThis.sqlite3ApiConfig = {
  disable: {
    vfs: {
      opfs: true,
      "opfs-sahpool": true,
      "opfs-wl": true,
      kvvfs: true,
    },
  },
};

const $ = (id) => document.getElementById(id);

let db = null;
let shown = 0;

function sliderIsAll() {
  return Number($("limit").value) >= ALL;
}
function pageSize() {
  return sliderIsAll() ? 0 : Number($("limit").value);
}
function limitLabel() {
  return sliderIsAll() ? "all" : String($("limit").value);
}

function selectedTypes() {
  return [...document.querySelectorAll(".type:checked")].map((el) => el.value);
}
function bookmarkOn() {
  const el = document.querySelector('.type[value="bookmark"]');
  return !!(el && el.checked);
}
function syncCatWrap() {
  $("catwrap").style.display = bookmarkOn() ? "flex" : "none";
}

function exec(sql, bind) {
  const rows = [];
  const args = { sql, rowMode: "object", resultRows: rows };
  if (bind && bind.length) args.bind = bind;
  db.exec(args);
  return rows;
}

function scalar(sql, bind) {
  const rows = exec(sql, bind);
  if (!rows.length) return 0;
  return Object.values(rows[0])[0];
}

function typeAndCategoryClause(types, categories) {
  const wanted = types.filter((t) => t in TYPE_COL);
  if (!wanted.length) return { sql: " AND 0 ", bind: [] };
  const useCats = wanted.includes("bookmark") && categories.length > 0;
  if (wanted.length >= TYPE_FLAGS.length && !useCats) return { sql: "", bind: [] };
  const parts = [];
  const bind = [];
  if (wanted.includes("bookmark")) {
    if (useCats) {
      parts.push(
        `(b.is_bookmark = 1 AND b.bookmark_category IN (${categories.map(() => "?").join(",")}))`,
      );
      bind.push(...categories);
    } else {
      parts.push("b.is_bookmark = 1");
    }
  }
  for (const t of wanted) {
    if (t === "bookmark") continue;
    parts.push(`b.${TYPE_COL[t]} = 1`);
  }
  if (!parts.length) return { sql: " AND 0 ", bind: [] };
  return { sql: " AND (" + parts.join(" OR ") + ") ", bind };
}

function dateClause(dateFrom, dateTo, includeUndated) {
  const bind = [];
  let sql = `
    AND (
      (
        b.created_at IS NOT NULL AND b.created_at != ''
  `;
  if (dateFrom) {
    sql += " AND b.created_at >= ? ";
    bind.push(dateFrom);
  }
  if (dateTo) {
    sql += " AND b.created_at <= ? ";
    bind.push(dateTo);
  }
  sql += ")";
  if (includeUndated) {
    sql += " OR (b.created_at IS NULL OR b.created_at = '') ";
  }
  sql += ")";
  return { sql, bind };
}

function orderSql(sort, fts) {
  if (sort === "oldest") {
    return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at ASC ";
  }
  if (sort === "newest") {
    return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at DESC ";
  }
  if (fts) return " ORDER BY rank ";
  return " ORDER BY CASE WHEN b.created_at IS NULL OR b.created_at = '' THEN 1 ELSE 0 END, b.created_at DESC ";
}

function formState() {
  const categories = bookmarkOn()
    ? [...$("category").selectedOptions].map((o) => o.value).filter(Boolean)
    : [];
  return {
    q: $("q").value.trim(),
    dateFrom: $("date_from").value || "",
    dateTo: $("date_to").value || "",
    includeUndated: $("include_undated").checked,
    author: $("author").value.trim(),
    categories,
    types: selectedTypes(),
    limit: pageSize(),
    sort: $("sort").value,
  };
}

function searchPage(opts) {
  const limit = opts.limit <= 0 ? 0 : Math.max(1, Math.min(100, opts.limit));
  const offset = Math.max(0, opts.offset || 0);
  const q = (opts.q || "").trim();
  const author = (opts.author || "").trim();
  const type = typeAndCategoryClause(opts.types || TYPE_FLAGS, opts.categories || []);
  const dates = dateClause(opts.dateFrom, opts.dateTo, opts.includeUndated);
  let extra = "";
  const extraBind = [];
  if (author) {
    extra += " AND b.author_username LIKE ? ";
    extraBind.push("%" + author + "%");
  }
  const colSql = COLS.map((c) => "b." + c).join(", ");
  const lim = limit === 0 ? -1 : limit;

  const run = (fromWhere, bind, fts) => {
    const total = Number(scalar("SELECT COUNT(*) " + fromWhere, bind));
    const rows = exec(
      `SELECT ${colSql} ${fromWhere} ${orderSql(opts.sort, fts)} LIMIT ? OFFSET ?`,
      bind.concat([lim, offset]),
    );
    return {
      rows: rows.map((r) => ({
        ...r,
        snippet: String(r.text || "").replace(/\n/g, " ").slice(0, 280),
      })),
      total,
    };
  };

  if (q) {
    const fromFts = `
      FROM bookmarks_fts f
      JOIN bookmarks b ON b.rowid = f.rowid
      WHERE bookmarks_fts MATCH ?
      ${dates.sql} ${extra} ${type.sql}
    `;
    const bindFts = [q, ...dates.bind, ...extraBind, ...type.bind];
    try {
      return run(fromFts, bindFts, true);
    } catch {
      const fromLike = `
        FROM bookmarks b
        WHERE (b.text LIKE ? OR IFNULL(b.summary,'') LIKE ? OR IFNULL(b.keywords,'') LIKE ?)
        ${dates.sql} ${extra} ${type.sql}
      `;
      const like = "%" + q + "%";
      const bindLike = [like, like, like, ...dates.bind, ...extraBind, ...type.bind];
      return run(fromLike, bindLike, false);
    }
  }
  const fromAll = `
    FROM bookmarks b
    WHERE 1=1
    ${dates.sql} ${extra} ${type.sql}
  `;
  return run(fromAll, [...dates.bind, ...extraBind, ...type.bind], false);
}

function loadStats() {
  const total = Number(scalar("SELECT COUNT(*) FROM bookmarks"));
  const enriched = Number(
    scalar("SELECT COUNT(*) FROM bookmarks WHERE enriched_at IS NOT NULL AND enriched_at != ''"),
  );
  const undated = Number(
    scalar("SELECT COUNT(*) FROM bookmarks WHERE created_at IS NULL OR created_at = ''"),
  );
  const counts = {};
  for (const [flag, col] of Object.entries(TYPE_COL)) {
    counts["is_" + flag] = Number(scalar(`SELECT COUNT(*) FROM bookmarks WHERE ${col}=1`));
  }
  const catRows = exec(
    "SELECT DISTINCT bookmark_category AS c FROM bookmarks WHERE IFNULL(bookmark_category,'') != '' ORDER BY 1",
  );
  $("stats").textContent =
    `${total} in db · ${enriched} enriched · ${undated} undated · ` +
    `bookmarks ${counts.is_bookmark} · posts ${counts.is_post} · replies ${counts.is_reply} · ` +
    `reposts ${counts.is_repost} · likes ${counts.is_like}`;
  const sel = $("category");
  const keep = new Set([...sel.selectedOptions].map((o) => o.value));
  sel.innerHTML = "";
  catRows.forEach((row) => {
    const o = document.createElement("option");
    o.value = row.c;
    o.textContent = row.c;
    if (keep.has(row.c)) o.selected = true;
    sel.appendChild(o);
  });
  syncCatWrap();
}

function flagBits(r) {
  const bits = [];
  if (r.is_bookmark) bits.push("bookmark");
  if (r.is_post) bits.push("post");
  if (r.is_reply) bits.push("reply");
  if (r.is_repost) bits.push("repost");
  if (r.is_like) bits.push("like");
  return bits.join(" · ");
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );
}

function cardHtml(r) {
  const when = (r.created_at || "?").slice(0, 10);
  const who = r.author_username ? "@" + r.author_username : "@_";
  const cat = r.bookmark_category ? ` · ${esc(r.bookmark_category)}` : "";
  const sum = r.summary ? `<div class="summary">${esc(r.summary)}</div>` : "";
  const kw = r.keywords ? `<div class="kw">${esc(r.keywords)}</div>` : "";
  const snip = r.snippet ? `<div class="snip">${esc(r.snippet)}</div>` : "";
  const href = r.url || "https://x.com/i/web/status/" + r.id;
  return `<article class="card">
        <div class="meta">${esc(when)} · ${esc(who)}${cat}
          <span class="flags"> · ${esc(flagBits(r))}</span></div>
        ${sum}${kw}${snip}
        <div><a href="${esc(href)}" target="_blank" rel="noopener">Open on X</a></div>
      </article>`;
}

function renderMore(total) {
  let bar = document.getElementById("more");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "more";
    bar.className = "more";
    $("results").appendChild(bar);
  }
  const moreLeft = shown < total;
  bar.innerHTML =
    `<span class="shown">Showing ${shown} of ${total}</span>` +
    (moreLeft ? `<button type="button" id="continue">Continue</button>` : "");
  const btn = document.getElementById("continue");
  if (btn) btn.addEventListener("click", () => search({ append: true }));
}

function search(opts = {}) {
  if (!db) return;
  const append = !!opts.append;
  $("toast").textContent = "";
  const st = formState();
  const offset = append ? shown : 0;
  if (!append) shown = 0;
  let data;
  try {
    data = searchPage({ ...st, offset });
  } catch (e) {
    $("toast").textContent = String(e && e.message ? e.message : e);
    return;
  }
  const box = $("results");
  const rows = data.rows || [];
  const total = Number(data.total || 0);
  if (!append) {
    if (!rows.length) {
      box.innerHTML = '<p class="empty">no hits</p>';
      shown = 0;
      return;
    }
    box.innerHTML = rows.map(cardHtml).join("");
    shown = rows.length;
  } else {
    if (!rows.length) {
      renderMore(total);
      return;
    }
    const bar = document.getElementById("more");
    if (bar) bar.remove();
    box.insertAdjacentHTML("beforeend", rows.map(cardHtml).join(""));
    shown += rows.length;
  }
  renderMore(total);
}

function cfg() {
  return window.THAT_POST || { dbUrl: "/ideas.sqlite", encrypted: false, kdfIters: 210000 };
}

async function decryptIndex(buf, password, iters) {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const magic = new TextDecoder().decode(u8.slice(0, 9));
  if (magic !== "THATPOST1") throw new Error("Not a That Post locked index");
  const salt = u8.slice(9, 25);
  const nonce = u8.slice(25, 37);
  const data = u8.slice(37);
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: iters, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"],
  );
  try {
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, key, data);
    return new Uint8Array(pt);
  } catch {
    throw new Error("Wrong password");
  }
}

function waitPassword() {
  return new Promise((resolve) => {
    const form = $("gateform");
    const onSubmit = (e) => {
      e.preventDefault();
      form.removeEventListener("submit", onSubmit);
      resolve($("gatepw").value);
    };
    form.addEventListener("submit", onSubmit);
    $("gatepw").focus();
  });
}

async function loadIndexBytes() {
  const c = cfg();
  const res = await fetch(c.dbUrl, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load the index (" + res.status + ")");
  const raw = new Uint8Array(await res.arrayBuffer());
  if (!c.encrypted) return raw;
  const gate = $("gate");
  if (!gate) throw new Error("Locked index, but this page has no password box");
  gate.hidden = false;
  if ($("gateerr")) $("gateerr").textContent = "";
  $("toast").textContent = "";
  for (;;) {
    const password = await waitPassword();
    try {
      const bytes = await decryptIndex(raw, password, c.kdfIters || 210000);
      gate.hidden = true;
      $("gatepw").value = "";
      if ($("gateerr")) $("gateerr").textContent = "";
      return bytes;
    } catch {
      if ($("gateerr")) $("gateerr").textContent = "Wrong password";
      else $("toast").textContent = "Wrong password";
      $("gatepw").value = "";
      $("gatepw").focus();
    }
  }
}

async function openDb() {
  $("toast").textContent = "Loading index…";
  const sqlite3 = await sqlite3InitModule();
  const fts = Number(
    (() => {
      const probe = new sqlite3.oo1.DB(":memory:");
      try {
        const rows = [];
        probe.exec({
          sql: "SELECT sqlite_compileoption_used('ENABLE_FTS5') AS n",
          rowMode: "object",
          resultRows: rows,
        });
        return rows[0]?.n;
      } finally {
        probe.close();
      }
    })(),
  );
  if (!fts) {
    throw new Error("This SQLite build has no FTS5 — search cannot run in the browser.");
  }
  const bytes = await loadIndexBytes();
  const p = sqlite3.wasm.allocFromTypedArray(bytes);
  db = new sqlite3.oo1.DB(":memory:");
  const rc = sqlite3.capi.sqlite3_deserialize(
    db.pointer,
    "main",
    p,
    bytes.byteLength,
    bytes.byteLength,
    sqlite3.capi.SQLITE_DESERIALIZE_FREEONCLOSE,
  );
  db.checkRc(rc);
}

$("limit").addEventListener("input", () => {
  $("limitn").textContent = limitLabel();
});
$("f").addEventListener("submit", (e) => {
  e.preventDefault();
  search();
});
document.querySelectorAll(".type").forEach((el) => {
  el.addEventListener("change", syncCatWrap);
});
syncCatWrap();

openDb()
  .then(() => {
    loadStats();
    search();
    $("toast").textContent = "";
  })
  .catch((e) => {
    $("toast").textContent = String(e && e.message ? e.message : e);
  });
