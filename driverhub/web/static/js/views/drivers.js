/* driverhub: views/drivers */
"use strict";

import { get, post } from "../api.js";
import { h, append, clear, on, el } from "../dom.js";
import { dataTable } from "../components/table.js";
import { badge } from "../components/badge.js";
import { openModal } from "../components/modal.js";
import { toast } from "../components/toast.js";
import { spinner } from "../components/spinner.js";
import { debounce } from "../utils.js";

let currentRoot = null;
let listBox = null;
let term = "";
let statusFilter = "";

const debounced = debounce(() => load(), 300);

export function mount(root, store) {
  currentRoot = root;
  clear(root);
  toolbar(root);
  listBox = h("div", { class: "card" });
  append(root, listBox);
  load();
}

function toolbar(root) {
  const input = h("input", { class: "input", placeholder: "Buscar driver...", value: term });
  on(input, "input", () => { term = input.value.trim(); debounced(); });
  on(input, "keydown", (e) => { if (e.key === "Enter") load(); });
  const status = h("select", { class: "input select" }, [
    h("option", { value: "", text: "Todos os status" }),
    h("option", { value: "ok", text: "ok" }),
    h("option", { value: "problem", text: "problem" }),
    h("option", { value: "pending", text: "pending" }),
  ]);
  on(status, "change", () => { statusFilter = status.value; load(); });
  append(root, h("div", { class: "toolbar" }, [
    input, status,
    h("button", { class: "btn success", onclick: installOpen }, [h("span", { text: "+" }), " Instalar"]),
  ]));
}

async function load() {
  if (!listBox) return;
  clear(listBox);
  append(listBox, spinner("Carregando drivers..."));
  const res = await get("/api/drivers" + (term ? "?term=" + encodeURIComponent(term) : ""));
  clear(listBox);
  if (!res.ok) {
    append(listBox, h("p", { class: "hint", text: "Falha ao carregar: " + res.error }));
    toast(res.error, "error");
    return;
  }
  let rows = res.data.drivers || [];
  const st = statusFilter.toLowerCase();
  if (st) rows = rows.filter((x) => String(x.status || "").toLowerCase() === st);

  if (!rows.length) {
    append(listBox, h("div", { class: "empty", text: "Nenhum driver encontrado." }));
    return;
  }
  append(listBox, dataTable(
    ["Driver", "Provedor", "Versão", "Classe", "Status", "Ações"],
    rows.map((x) => [
      { html: `<b>${String(x.name || x.id)}</b>` + (x.date ? `<div style="font-size:11px;color:var(--muted)">${String(x.date)}</div>` : "") },
      x.provider || "—",
      x.version || "—",
      badge(x.class || "outros", "info"),
      badge(String(x.status || "pending"), toneOf(x.status)),
      { html:
        `<button class="btn small" data-act="update" title="Atualizar">↻</button> ` +
        `<button class="btn small danger" data-act="remove" title="Remover">✕</button>` },
    ]),
    { onRowClick: (r) => detail(r) },
  ));
  listBox.querySelectorAll("button[data-act]").forEach((b) => {
    const tr = b.closest("tr");
    const row = rows[tr ? tr.rowIndex - 1 : -1];
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      if (b.dataset.act === "remove") removeDriver(row);
      else updateDriver(row);
    });
  });
}

function toneOf(s) {
  const st = String(s || "").toLowerCase();
  if (["ok", "loaded", "installed", "active", "working"].includes(st)) return "ok";
  if (["problem", "error", "failed", "missing", "broken"].includes(st)) return "error";
  if (!st || st === "pending" || st === "unknown") return "warn";
  return "info";
}

function detail(x) {
  openModal({
    title: x.name || "Driver",
    body: h("div", { style: { lineHeight: "1.8" } }, [
      kv("ID", x.id), kv("Provedor", x.provider), kv("Versão", x.version),
      kv("Classe", x.class), kv("Status", x.status), kv("Data", x.date),
    ]),
    actions: [{ label: "Fechar", class: "btn" }],
  });
}

function kv(k, v) {
  const t = v === undefined || v === null || v === "" ? "—" : String(v);
  return h("p", {}, [h("b", { text: k + ": " }), h("span", { text: t })]);
}

function installOpen() {
  openModal({
    title: "Instalar driver",
    body: h("div", {}, [
      h("p", { class: "hint", text: "Informe o caminho de um arquivo .inf (Windows) ou .run/módulo (Linux)." }),
      h("input", { class: "input", id: "install-target", placeholder: "C:\\drivers\\oem.inf ou /tmp/driver.run", style: { width: "100%" } }),
    ]),
    actions: [
      { label: "Cancelar", class: "btn" },
      { label: "Instalar", class: "btn success", onClick: async () => {
        const input = el("install-target");
        const target = (input ? input.value : "").trim();
        if (!target) { toast("Caminho obrigatório.", "error"); return false; }
        const res = await post("/api/actions/install", { target });
        if (!res.ok) { toast(res.error || "Falha na instalação.", "error"); return false; }
        toast(res.data.detail || ("Instalado: " + target), "ok");
        load();
      } },
    ],
  });
}

function updateDriver(x) { return doAction("update", x); }
function removeDriver(x) { return doAction("remove", x); }

async function doAction(kind, x) {
  const id = x.id || "";
  const label = kind === "remove" ? "Remover" : "Atualizar";
  openModal({
    title: label + " driver",
    body: kind === "remove"
      ? "Tem certeza que deseja remover o driver \"" + id + "\"?\nRequer privilégios de administrador."
      : "Enviar atualização/recarregamento para o driver \"" + id + "\"?",
    actions: [
      { label: "Cancelar", class: "btn" },
      { label, class: kind === "remove" ? "btn danger" : "btn primary", onClick: async () => {
        const res = await post("/api/actions/" + kind, { target: id });
        if (!res.ok) { toast(res.error || ("Falha ao " + label.toLowerCase() + "."), "error"); return false; }
        toast(res.data.detail || (label + "."), "ok");
        load();
      } },
    ],
  });
}

export const title = "Drivers";
export const sub = "Drivers instalados e gerenciáveis";
export default { mount, title, sub };