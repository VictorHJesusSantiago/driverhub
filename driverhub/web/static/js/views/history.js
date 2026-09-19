/* driverhub: views/history */
"use strict";

import { get } from "../api.js";
import { h, append, clear, on } from "../dom.js";
import { dataTable } from "../components/table.js";
import { badge } from "../components/badge.js";
import { toast } from "../components/toast.js";
import { spinner } from "../components/spinner.js";
import { fmtDate } from "../format.js";
import { debounce } from "../utils.js";

const PAGE = 25;

let currentRoot = null;
let listBox = null;
let pager = null;
let page = 0;
let term = "";
let typeFilter = "";
let okFilter = "";
let items = [];

const debounced = debounce(() => { page = 0; load(); }, 300);

export function mount(root, store) {
  currentRoot = root;
  clear(root);
  toolbar(root);
  listBox = h("div", { class: "card" });
  pager = h("div", { class: "toolbar" });
  append(root, pager, listBox);
  load();
}

function toolbar(root) {
  const input = h("input", { class: "input", placeholder: "Buscar no histórico...", value: term });
  on(input, "input", () => { term = input.value.trim(); debounced(); });
  on(input, "keydown", (e) => { if (e.key === "Enter") { page = 0; load(); } });
  const type = h("select", { class: "input select" }, [
    h("option", { value: "", text: "Todos os tipos" }),
    h("option", { value: "install", text: "install" }),
    h("option", { value: "remove", text: "remove" }),
    h("option", { value: "update", text: "update" }),
    h("option", { value: "scan", text: "scan" }),
  ]);
  on(type, "change", () => { typeFilter = type.value; page = 0; load(); });
  const ok = h("select", { class: "input select" }, [
    h("option", { value: "", text: "Todos os resultados" }),
    h("option", { value: "1", text: "ok" }),
    h("option", { value: "0", text: "falha" }),
  ]);
  on(ok, "change", () => { okFilter = ok.value; page = 0; load(); });
  append(root, h("div", { class: "toolbar" }, [input, type, ok]));
}

async function load() {
  if (!listBox) return;
  clear(listBox);
  append(listBox, spinner("Carregando histórico..."));
  const params = new URLSearchParams();
  params.set("limit", "1000");
  if (term) params.set("term", term);
  const res = await get("/api/history?" + params.toString());
  clear(listBox);
  if (!res.ok) {
    append(listBox, h("p", { class: "hint", text: "Falha ao carregar: " + res.error }));
    toast(res.error, "error");
    return;
  }
  let rows = (res.data.history || []).slice();
  if (typeFilter) rows = rows.filter((r) => String(r.action || "").toLowerCase() === typeFilter);
  if (okFilter !== "") rows = rows.filter((r) => (r.ok ? "1" : "0") === okFilter);
  rows.sort((a, b) => String(b.ts || "").localeCompare(String(a.ts || "")));
  items = rows;
  page = Math.min(page, Math.max(0, Math.ceil(items.length / PAGE) - 1));
  renderList();
  renderPager();
}

function renderList() {
  clear(listBox);
  const slice = items.slice(page * PAGE, page * PAGE + PAGE);
  if (!slice.length) {
    append(listBox, h("div", { class: "empty", text: "Nenhuma operação encontrada." }));
    return;
  }
  append(listBox, dataTable(
    ["Quando", "Ação", "Alvo", "Detalhe", "Resultado"],
    slice.map((r) => [
      fmtDate(r.ts),
      badge(r.action || "-", "info"),
      r.target || "—",
      { text: r.detail || "—" },
      badge(r.ok ? "ok" : "falha", r.ok ? "ok" : "error"),
    ]),
  ));
}

function renderPager() {
  if (!pager) return;
  clear(pager);
  if (items.length <= PAGE) return;
  const totalPages = Math.ceil(items.length / PAGE);
  append(pager,
    h("button", { class: "btn small", disabled: page <= 0, text: "← Anterior", onclick: () => { page--; renderList(); renderPager(); } }),
    h("span", { class: "hint", text: (page + 1) + " / " + totalPages + " (" + items.length + " registros)" }),
    h("button", { class: "btn small", disabled: page >= totalPages - 1, text: "Próxima →", onclick: () => { page++; renderList(); renderPager(); } }),
  );
}

export const title = "Histórico";
export const sub = "Registro de operações";
export default { mount, title, sub };