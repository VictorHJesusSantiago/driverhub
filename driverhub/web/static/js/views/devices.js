/* driverhub: views/devices */
"use strict";

import { get } from "../api.js";
import { h, append, clear, on } from "../dom.js";
import { dataTable } from "../components/table.js";
import { badge } from "../components/badge.js";
import { openModal } from "../components/modal.js";
import { toast } from "../components/toast.js";
import { spinner } from "../components/spinner.js";
import { debounce, uniq, escapeHtml } from "../utils.js";

let currentRoot = null;
let storeRef = null;
let listBox = null;
let selEl = null;
let search = "";
let kindFilter = "";
let kinds = [];

const debouncedLoad = debounce(() => load(), 300);

export function mount(root, store) {
  currentRoot = root;
  storeRef = store;
  clear(root);
  toolbar(root);
  listBox = h("div", { class: "card" });
  append(root, listBox);
  load();
}

function toolbar(root) {
  const input = h("input", { class: "input", placeholder: "Buscar dispositivo...", value: search });
  on(input, "input", () => { search = input.value.trim(); debouncedLoad(); });
  on(input, "keydown", (e) => { if (e.key === "Enter") load(); });
  selEl = h("select", { class: "input select" });
  on(selEl, "change", () => { kindFilter = selEl.value; load(); });
  append(root, h("div", { class: "toolbar" }, [input, selEl]));
}

function fillKinds() {
  if (!selEl) return;
  const prev = kindFilter;
  clear(selEl);
  append(selEl, h("option", { value: "", text: "Todas as categorias" }));
  kinds.forEach((k) => append(selEl, h("option", { value: k, text: k })));
  selEl.value = kinds.includes(prev) ? prev : "";
}

async function load() {
  if (!listBox) return;
  clear(listBox);
  append(listBox, spinner("Carregando dispositivos..."));
  const res = await get("/api/devices" + (kindFilter ? "?kind=" + encodeURIComponent(kindFilter) : ""));
  clear(listBox);
  if (!res.ok) {
    append(listBox, h("p", { class: "hint", text: "Falha ao carregar: " + res.error }));
    toast(res.error, "error");
    return;
  }
  const data = res.data || {};
  kinds = uniq(Object.keys(data.kinds || {}));
  fillKinds();
  const term = search.toLowerCase();
  const rows = (data.devices || []).filter((x) =>
    !term || [x.name, x.vendor, x.kind, x.hwid, x.id].some((v) => String(v || "").toLowerCase().includes(term)));
  if (storeRef) storeRef.set({ filters: { deviceKind: kindFilter, deviceTerm: search } });

  if (!rows.length) {
    append(listBox, h("div", { class: "empty", text: "Nenhum dispositivo encontrado." }));
    return;
  }
  append(listBox, dataTable(
    ["Tipo", "Dispositivo", "Fabricante", "Driver", "Status", "Ações"],
    rows.map((x) => [
      badge(x.kind || "other", "info"),
      { html: escapeHtml(x.name || "—") + (x.hwid ? `<div class="mono" style="color:var(--muted);font-size:11px">${escapeHtml(x.hwid)}</div>` : "") },
      x.vendor || "—",
      x.driver || "—",
      badge(statusText(x), toneOf(x.status)),
      { html: `<button class="btn small" data-act="detail">Detalhes</button>` },
    ]),
    { onRowClick: (row) => showDetail(row) },
  ));
  listBox.querySelectorAll("button[data-act='detail']").forEach((b) => {
    const tr = b.closest("tr");
    const row = rows[tr ? tr.rowIndex - 1 : -1];
    b.addEventListener("click", (e) => { e.stopPropagation(); showDetail(row); });
  });
}

function statusText(x) {
  const s = String(x.status || "ok");
  return s === "problem" ? "problema" : s;
}

function toneOf(s) {
  const st = String(s || "").toLowerCase();
  if (["ok", "loaded", "installed", "active", "working"].includes(st)) return "ok";
  if (["problem", "error", "failed", "missing", "broken"].includes(st)) return "error";
  if (!st || st === "pending" || st === "unknown") return "warn";
  return "info";
}

function showDetail(x) {
  openModal({
    title: "Dispositivo",
    body: h("div", { style: { lineHeight: "1.8" } }, [
      kv("Nome", x.name), kv("Tipo", x.kind), kv("ID", x.id),
      kv("Fabricante", x.vendor), kv("HWID", x.hwid), kv("Driver", x.driver),
      kv("Status", x.status), kv("Detalhe", x.detail), kv("Meta", x.meta ? JSON.stringify(x.meta) : ""),
    ]),
    actions: [{ label: "Fechar", class: "btn" }],
  });
}

function kv(k, v) {
  const t = v === undefined || v === null || v === "" ? "—" : String(v);
  return h("p", {}, [h("b", { text: k + ": " }), h("span", { text: t })]);
}

export const title = "Dispositivos";
export const sub = "Inventário de hardware";
export default { mount, title, sub };