/* driverhub: views/catalog */
"use strict";

import { get } from "../api.js";
import { h, append, clear, on } from "../dom.js";
import { dataTable } from "../components/table.js";
import { badge } from "../components/badge.js";
import { toast } from "../components/toast.js";
import { spinner } from "../components/spinner.js";
import { debounce, escapeHtml } from "../utils.js";

let currentRoot = null;
let listBox = null;
let selEl = null;
let term = "";
let category = "";
let categories = [];

const debounced = debounce(() => load(), 300);

export function mount(root, store) {
  currentRoot = root;
  clear(root);
  const input = h("input", { class: "input", placeholder: "Buscar no catálogo (ex.: nvidia)", value: term });
  on(input, "input", () => { term = input.value.trim(); debounced(); });
  on(input, "keydown", (e) => { if (e.key === "Enter") load(); });
  selEl = h("select", { class: "input select" });
  on(selEl, "change", () => { category = selEl.value; load(); });
  append(root, h("div", { class: "toolbar" }, [input, selEl]));
  append(root, h("p", { class: "hint", text: "Fontes 100% oficiais. Clique em um link para abrir o download oficial do fabricante no navegador." }));
  listBox = h("div", { class: "card" });
  append(root, listBox);
  load();
}

function fillCategories() {
  if (!selEl) return;
  const prev = category;
  clear(selEl);
  append(selEl, h("option", { value: "", text: "Todas as categorias" }));
  categories.forEach((c) => append(selEl, h("option", { value: c, text: c })));
  selEl.value = categories.includes(prev) ? prev : "";
}

async function load() {
  if (!listBox) return;
  clear(listBox);
  append(listBox, spinner("Buscando no catálogo..."));
  const params = new URLSearchParams();
  if (term) params.set("term", term);
  if (category) params.set("category", category);
  const res = await get("/api/catalog?" + params.toString());
  clear(listBox);
  if (!res.ok) {
    append(listBox, h("p", { class: "hint", text: "Falha ao buscar: " + res.error }));
    toast(res.error, "error");
    return;
  }
  categories = res.data.categories || [];
  fillCategories();
  const rows = res.data.catalog || [];

  if (!rows.length) {
    append(listBox, h("div", { class: "empty", text: "Nenhuma entrada encontrada no catálogo." }));
    return;
  }
  append(listBox, dataTable(
    ["Fabricante", "Categoria", "Dispositivo", "SO", "Fonte", "Download oficial"],
    rows.map((x) => [
      { html: `<b>${escapeHtml(x.vendor || "-")}</b>` },
      badge(x.category || "-", "info"),
      { html: escapeHtml(x.device || "-") + (x.notes ? `<div style="font-size:11px;color:var(--muted)">${escapeHtml(x.notes)}</div>` : "") },
      x.os || "-",
      badge("oficial", "ok"),
      { html: x.url
        ? `<a class="link url-cell" href="${escapeHtml(x.url)}" target="_blank" rel="noopener">${escapeHtml(x.url)} ⇗</a>`
        : "—" },
    ]),
  ));
}

export const title = "Catálogo";
export const sub = "Fontes oficiais de drivers";
export default { mount, title, sub };