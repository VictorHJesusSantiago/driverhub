/* DriverHub — frontend (vanilla JS, sem dependências) */
"use strict";

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const state = { boot: null, filters: {} };

/* ---------- navegação ---------- */
function switchView(name) {
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const view = $("#view-" + name);
  if (view) view.classList.add("active");
  $("#sidebar").classList.remove("open");
  const titles = {
    dashboard: ["Painel", "Visão geral do sistema"],
    devices: ["Dispositivos", "Inventário de hardware"],
    drivers: ["Drivers", "Driveres instalados e gerenciáveis"],
    catalog: ["Catálogo", "Fontes oficiais de drivers"],
    hardware: ["Hardware", "Detalhes do hardware"],
    history: ["Histórico", "Registro de operações"],
    about: ["Sobre", "DriverHub"],
  };
  const t = titles[name] || ["", ""];
  $("#page-title").textContent = t[0];
  $("#page-sub").textContent = t[1];
  loaders[name] && loaders[name]();
}

/* ---------- fetch helpers ---------- */
async function apiGet(path) {
  const r = await fetch(path);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "erro");
  return j;
}

async function apiPost(path, body = {}) {
  const sep = path.includes("?") ? "&" : "?";
  const r = await fetch(path + sep + "confirm=1", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || j.detail || "erro");
  return j;
}

async function withBusy(fn) {
  $("#busy").classList.remove("hidden");
  try { return await fn(); }
  finally { $("#busy").classList.add("hidden"); }
}

function toast(msg, type = "ok") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + type;
  clearTimeout(t._tm);
  t._tm = setTimeout(() => t.classList.add("hidden"), 6000);
}

/* ---------- tabelas ---------- */
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function table(headers, rows, opts = {}) {
  const wrap = el("div", "table-wrap");
  const t = el("table");
  const thead = el("thead");
  const tr = el("tr");
  headers.forEach((h) => tr.appendChild(el("th", null, esc(h))));
  thead.appendChild(tr);
  t.appendChild(thead);
  const tb = el("tbody");
  rows.forEach((r) => {
    const trr = el("tr");
    r.forEach((cell) => trr.appendChild(el("td", null, cell.html ?? esc(cell.v ?? cell))));
    tb.appendChild(trr);
  });
  t.appendChild(tb);
  if (!rows.length) {
    const e = el("div", "empty", "Nenhum registro encontrado.");
    wrap.appendChild(e);
    return wrap;
  }
  wrap.appendChild(t);
  return wrap;
}

function pill(status) {
  const s = String(status ?? "").toLowerCase();
  const cls = ["ok", "loaded", "published", "installed"].includes(s) ? "ok"
    : ["problem", "error"].includes(s) ? "problem"
    : "pending";
  return `<span class="pill ${cls}">${esc(status)}</span>`;
}

function renderChart(containerId, data) {
  const box = $(containerId);
  if (!box) return;
  box.innerHTML = "";
  const entries = Object.entries(data || {}).slice(0, 12);
  if (!entries.length) { box.appendChild(el("div", "empty", "Sem dados.")); return; }
  const max = Math.max(...entries.map(([, v]) => v), 1);
  entries.forEach(([name, val]) => {
    const row = el("div", "chart-row");
    row.appendChild(el("span", "name", esc(name)));
    const bg = el("div", "chart-bar-bg");
    const bar = el("div", "chart-bar");
    bar.style.width = (val / max * 100) + "%";
    bg.appendChild(bar);
    row.appendChild(bg);
    row.appendChild(el("span", "mono", String(val)));
    box.appendChild(row);
  });
}

/* ---------- views ---------- */
const loaders = {};

loaders.dashboard = async () => {
  const d = await apiGet("/api/dashboard");
  const os = d.os;
  $("#os-card").innerHTML = `
    <div class="os-name">${esc(os.name)}</div>
    <div class="meta">Kernel ${esc(os.kernel || os.release)} · ${esc(os.arch)} · ${esc(os.hostname)}</div>
    <div class="meta">${state.boot ? (state.boot.admin ? "Administrador ✓" : "Sem perfil de administrador — instalar/remover bloqueado") : ""}</div>`;
  const st = d.stats;
  $("#stat-cards").innerHTML = ["catalog", "devices", "drivers", "history"].map((k) =>
    `<div class="stat-card"><div class="num">${st[k] ?? 0}</div><div class="lbl">${k === "devices" ? "Dispositivos" : k === "drivers" ? "Drivers gerenciáveis" : k === "catalog" ? "Fontes oficiais" : "Operações registradas"}</div></div>`
  ).join("");
  const probBox = document.createElement("div");
  if (d.problems_count > 0) {
    probBox.id = "problems-card";
    probBox.className = "card";
    probBox.style.borderColor = "var(--red)";
    probBox.innerHTML = `<h3 style="color:var(--red)">⚠ ${d.problems_count} dispositivo(s) com problema</h3>`;
    const w = table(["Tipo", "Dispositivo", "Fabricante"],
      d.problems.map((p) => [esc(p.kind), esc(p.name), esc(p.vendor)]));
    probBox.appendChild(w);
  }
  renderChart("#chart-classes", d.drivers_classes);
  renderChart("#chart-kinds", d.devices_kinds);
  const recent = d.recent || [];
  $("#recent").innerHTML = "";
  $("#recent").appendChild(table(
    ["Quando", "Ação", "Alvo", "Resultado"],
    recent.map((r) => [esc(r.ts), esc(r.action), esc(r.target), esc(r.ok ? "ok" : "falha")]),
  ));
  const dv = document.querySelector("#view-dashboard");
  const ref = dv.querySelector(".grid.two");
  if (probBox.id) ref.before(probBox);
};

loaders.devices = async () => {
  const kind = state.filters.devKind || "";
  const d = await apiGet("/api/devices" + (kind ? "?kind=" + encodeURIComponent(kind) : ""));
  $("#devices-list").innerHTML = "";
  $("#devices-list").appendChild(table(
    ["Tipo", "Dispositivo", "Fabricante", "Driver", "Status"],
    d.devices.map((x) => [
      { v: x.kind, html: `<span class="pill pending">${esc(x.kind)}</span>` },
      { v: x.name, html: `<div>${esc(x.name)}</div>${x.driver_id ? `<div class="mono" style="color:var(--muted);font-size:11px">${esc(x.driver_id)}</div>` : ""}` },
      { v: x.vendor },
      { v: x.driver_version },
      { html: pill(x.status) },
    ]),
  ));
};

loaders.drivers = async () => {
  const term = state.filters.drvTerm || "";
  const cls = state.filters.drvClass || "";
  const q = new URLSearchParams();
  if (term) q.set("term", term);
  if (cls) q.set("class", cls);
  const d = await apiGet("/api/drivers?" + q.toString());
  const sel = $("#drv-class");
  sel.innerHTML = '<option value="">Todas as classes</option>' +
    (d.classes || []).map((c) => `<option value="${esc(c)}" ${c === cls ? "selected" : ""}>${esc(c)}</option>`).join("");
  $("#drivers-list").innerHTML = "";
  $("#drivers-list").appendChild(table(
    ["ID", "Driver", "Provedor", "Versão", "Classe", "Status", "Ações"],
    d.drivers.map((x) => [
      { v: x.id, html: `<span class="mono" style="color:var(--muted)">${esc(String(x.id).slice(0, 42))}</span>` },
      { v: x.name, html: `<div>${esc(x.name)}</div>${x.date ? `<div style="font-size:11px;color:var(--muted)">${esc(x.date)}</div>` : ""}` },
      { v: x.provider },
      { v: x.version, html: `<span class="mono">${esc(x.version)}</span>` },
      { v: x.class, html: `<span class="pill pending">${esc(x.class || "-")}</span>` },
      { html: pill(x.status) },
      { html: `
        <button class="btn small" onclick="drvUpdate('${esc(String(x.id).replace(/'/g, ""))}')">↻</button>
        <button class="btn small danger" onclick="drvRemove('${esc(String(x.id).replace(/'/g, ""))}')">✕</button>` },
    ]),
  ));
};

loaders.catalog = async () => {
  const term = state.filters.catTerm || "";
  const cat = state.filters.catCategory || "";
  const q = new URLSearchParams();
  if (term) q.set("term", term);
  if (cat) q.set("category", cat);
  const d = await apiGet("/api/catalog?" + q.toString());
  const sel = $("#cat-category");
  sel.innerHTML = '<option value="">Todas as categorias</option>' +
    d.categories.map((c) => `<option value="${esc(c)}" ${c === cat ? "selected" : ""}>${esc(c)}</option>`).join("");
  $("#catalog-list").innerHTML = "";
  $("#catalog-list").appendChild(table(
    ["Fabricante", "Categoria", "Dispositivo", "SO", "Download oficial"],
    d.catalog.map((x) => [
      { v: x.vendor, html: `<b>${esc(x.vendor)}</b>` },
      { v: x.category, html: `<span class="pill pending">${esc(x.category)}</span>` },
      { v: x.device, html: `${esc(x.device)}${x.notes ? `<div style="font-size:11px;color:var(--muted)">${esc(x.notes)}</div>` : ""}` },
      { v: x.os },
      { v: x.url, html: `<a class="link url-cell" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.url)} ⇗</a>` },
    ]),
  ));
};

loaders.hardware = async () => {
  const d = await apiGet("/api/hardware");
  $("#hardware-box").textContent = JSON.stringify(d.hardware, null, 2);
};

loaders.history = async () => {
  const term = state.filters.histTerm || "";
  const d = await apiGet("/api/history?limit=200" + (term ? "&term=" + encodeURIComponent(term) : ""));
  $("#history-list").innerHTML = "";
  $("#history-list").appendChild(table(
    ["Quando", "Ação", "Alvo", "Detalhe", "Resultado"],
    d.history.map((r) => [
      esc(r.ts),
      esc(r.action),
      esc(r.target),
      { v: r.detail, html: `<div class="mono" style="color:var(--muted)">${esc(r.detail)}</div>` },
      esc(r.ok ? "ok" : "falha"),
    ]),
  ));
};

loaders.about = () => {
  const b = state.boot || {};
  $("#about-box").innerHTML = `
    <div style="font-size:20px;font-weight:800;margin-bottom:8px">DriverHub v${esc(b.version || "0.9.0")}</div>
    <p class="hint" style="line-height:1.7">
      Gerenciador universal de drivers: lista, instala, atualiza e remove drivers
      do sistema (Windows via pnputil, Linux via kernel modules) e mantém um
      catálogo de <b>fontes 100% oficiais</b> dos fabricantes para download.<br><br>
      Funciona no terminal e nesta interface web — acessível de computador e
      celular na mesma rede.<br><br>
      Aviso: operações de instalação/remoção exigem privilégios de administrador
      e são registradas no histórico.
    </p>`;
};

/* ---------- ações ---------- */
function modal(title, text, onOk, inputs = [], okLabel = "Confirmar") {
  $("#modal-title").textContent = title;
  $("#modal-text").textContent = text;
  const box = $("#modal-inputs");
  box.innerHTML = "";
  inputs.forEach((i) => {
    const l = el("label");
    l.textContent = i.label;
    const inp = el("input", "input");
    inp.type = i.type || "text";
    inp.value = i.value || "";
    inp.placeholder = i.placeholder || "";
    l.appendChild(inp);
    box.appendChild(l);
  });
  $("#modal-ok").textContent = okLabel;
  $("#modal").classList.remove("hidden");
  $("#modal-ok").onclick = async () => {
    const vals = {};
    [...box.querySelectorAll("input")].forEach((inp, ix) => { vals[inputs[ix].name] = inp.value; });
    $("#modal").classList.add("hidden");
    await onOk(vals);
  };
  $("#modal-cancel").onclick = () => { $("#modal").classList.add("hidden"); };
}

async function doScan() {
  await withBusy(async () => {
    const r = await apiPost("/api/actions/scan", {});
    toast(`Varredura concluída: ${r.devices_count} dispositivos, ${r.drivers_count} drivers.`);
    loaders.dashboard();
  });
}

async function doCatalogUpdate() {
  await withBusy(async () => {
    try {
      const r = await apiPost("/api/actions/catalog-update", {});
      toast(r.message || "Catálogo atualizado.");
    } catch (e) { toast(e.message, "err"); }
    loaders.catalog();
  });
}

function drvInstallOpen() {
  modal("Instalar driver", "Informe o caminho de um arquivo .inf (Windows) ou .run/módulo (Linux).", async (v) => {
    if (!v.target) { toast("Caminho obrigatório.", "err"); return 0; }
    await withBusy(async () => {
      try { const r = await apiPost("/api/actions/install", { target: v.target }); toast(r.detail || "Instalado.", r.ok ? "ok" : "err"); }
      catch (e) { toast(e.message || "Falha na instalação.", "err"); }
      loaders.drivers(); loaders.dashboard();
    });
  }, [{ name: "target", label: "Caminho do driver", placeholder: "C:\\drivers\\oem.inf ou /tmp/driver.run" }], "Instalar");
}

function drvUpdate(id) {
  modal("Atualizar driver", "Solicitar atualização/recarregamento do driver " + id, async () => {
    await withBusy(async () => {
      try { const r = await apiPost("/api/actions/update", { target: id }); toast(r.detail || "Atualizado.", r.ok ? "ok" : "err"); }
      catch (e) { toast(e.message, "err"); }
      loaders.drivers(); loaders.dashboard();
    });
  }, [], "Atualizar");
}

function drvRemove(id) {
  modal("Remover driver", "Tem certeza que deseja remover o driver " + id + "?\nRequer privilégios de administrador.", async () => {
    await withBusy(async () => {
      try { const r = await apiPost("/api/actions/remove", { target: id }); toast(r.detail || "Removido.", r.ok ? "ok" : "err"); }
      catch (e) { toast(e.message, "err"); }
      loaders.drivers(); loaders.dashboard();
    });
  }, [], "Remover");
}

window.drvUpdate = drvUpdate;
window.drvRemove = drvRemove;

/* ---------- binding ---------- */
function bind() {
  document.querySelectorAll(".nav-item[data-view]").forEach((b) =>
    b.addEventListener("click", () => switchView(b.dataset.view)));
  $("#burger").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $("#btn-scan").addEventListener("click", doScan);
  $("#btn-cat-update").addEventListener("click", doCatalogUpdate);

  $("#dev-apply").addEventListener("click", () => { state.filters.devKind = $("#dev-filter-kind").value.trim(); loaders.devices(); });
  $("#dev-filter-kind").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#dev-apply").click(); });
  $("#drv-apply").addEventListener("click", () => { state.filters.drvTerm = $("#drv-search").value.trim(); state.filters.drvClass = $("#drv-class").value; loaders.drivers(); });
  $("#drv-search").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#drv-apply").click(); });
  $("#drv-install").addEventListener("click", drvInstallOpen);
  $("#cat-apply").addEventListener("click", () => { state.filters.catTerm = $("#cat-search").value.trim(); state.filters.catCategory = $("#cat-category").value; loaders.catalog(); });
  $("#cat-search").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#cat-apply").click(); });
  $("#hist-apply").addEventListener("click", () => { state.filters.histTerm = $("#hist-term").value.trim(); loaders.history(); });
  $("#hist-term").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#hist-apply").click(); });
}

async function boot() {
  try { state.boot = await apiGet("/api/boot"); } catch (e) { /* offline */ }
  const badge = $("#admin-badge");
  if (state.boot) {
    badge.textContent = state.boot.admin ? "Administrador ✓" : "Acesso limitado";
    badge.className = "badge " + (state.boot.admin ? "on" : "off");
    $("#os-badge").textContent = state.boot.os.name || "";
  }
  bind();
  switchView("dashboard");
}

document.addEventListener("DOMContentLoaded", boot);