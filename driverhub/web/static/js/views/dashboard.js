/* driverhub: views/dashboard */
"use strict";

import { get, post } from "../api.js";
import { h, append, clear } from "../dom.js";
import { dataTable } from "../components/table.js";
import { badge } from "../components/badge.js";
import { toast } from "../components/toast.js";
import { spinner, withSpinner } from "../components/spinner.js";
import { bars } from "../components/chart.js";
import { fmtDate } from "../format.js";
import { navigate } from "../router.js";
import { icon } from "../icons.js";

let currentRoot = null;
let storeRef = null;

export function mount(root, store) {
  currentRoot = root;
  storeRef = store;
  clear(root);
  append(root, h("div", { class: "card" }, spinner("Carregando painel...")));

  get("/api/dashboard").then((res) => {
    clear(currentRoot);
    if (!res.ok) {
      append(currentRoot, h("div", { class: "card" }, h("p", { class: "hint", text: "Falha ao carregar painel: " + res.error })));
      toast(res.error, "error");
      return;
    }
    if (storeRef) storeRef.set({ stats: res.data.stats || {}, boot: res.data.os || null });
    render(currentRoot, res.data);
  });
}

function render(root, d) {
  const os = d.os || {};
  append(root, h("div", { class: "card hero" }, [
    h("div", { class: "os-name", text: os.name || "Sistema" }),
    h("div", { class: "meta", text: ["Kernel " + (os.kernel || os.release || ""), os.arch, os.hostname].filter(Boolean).join(" · ") }),
    h("div", { class: "meta", text: (os.admin ? "Administrador" : "Acesso limitado") + (d.device_class ? " · " + d.device_class : "") }),
  ]));

  const st = d.stats || {};
  const cards = h("div", { class: "grid cards" });
  [
    ["catalog", "Fontes oficiais"],
    ["devices", "Dispositivos"],
    ["drivers", "Drivers gerenciáveis"],
    ["history", "Operações registradas"],
  ].forEach(([k, lbl]) => append(cards, h("div", { class: "stat-card" }, [
    h("div", { class: "num", text: String(st[k] ?? 0) }),
    h("div", { class: "lbl", text: lbl }),
  ])));
  append(root, cards);

  append(root, h("div", { class: "toolbar" }, [
    h("button", { class: "btn primary", onclick: () => runAction("scan") }, [h("span", { class: "ico", html: icon("refresh") }), " Escanear"]),
    h("button", { class: "btn", onclick: () => runAction("catalog-update") }, [h("span", { class: "ico", html: icon("download") }), " Atualizar catálogo"]),
    h("button", { class: "btn", onclick: () => navigate("catalog") }, [h("span", { class: "ico", html: icon("box") }), " Catálogo"]),
    h("button", { class: "btn", onclick: () => navigate("history") }, [h("span", { class: "ico", html: icon("clock") }), " Histórico"]),
  ]));

  if ((d.problems_count || 0) > 0) {
    append(root, h("div", { class: "card", style: { borderColor: "var(--red)" } }, [
      h("h3", { style: { color: "var(--red)" } }, [
        h("span", { html: icon("alert", 16) }),
        " " + d.problems_count + " dispositivo(s) com problema",
      ]),
      dataTable(["Tipo", "Dispositivo", "Fabricante"],
        (d.problems || []).map((p) => [badge(p.kind || "-", "warn"), p.name || "-", p.vendor || "-"])),
    ]));
  }

  append(root, h("div", { class: "grid two" }, [
    h("div", { class: "card" }, [
      h("h3", { text: "Drivers por categoria" }),
      h("div", { class: "chart", html: bars(d.drivers_classes || {}) }),
    ]),
    h("div", { class: "card" }, [
      h("h3", { text: "Dispositivos por tipo" }),
      h("div", { class: "chart", html: bars(d.devices_kinds || {}) }),
    ]),
  ]));

  const recent = d.recent || [];
  append(root, h("div", { class: "card" }, [
    h("h3", { text: "Atividade recente" }),
    dataTable(["Quando", "Ação", "Alvo", "Resultado"],
      recent.map((r) => [
        fmtDate(r.ts),
        r.action || "-",
        r.target || "-",
        badge(r.ok ? "ok" : "falha", r.ok ? "ok" : "error"),
      ])),
  ]));
}

async function runAction(kind) {
  const res = await withSpinner(async () => {
    return kind === "scan"
      ? await post("/api/actions/scan", {})
      : await post("/api/actions/catalog-update", {});
  });
  if (res.ok) {
    if (kind === "scan") {
      toast("Varredura concluída: " + (res.data.devices_count || 0) + " dispositivos, " + (res.data.drivers_count || 0) + " drivers.", "ok");
    } else {
      toast(res.data.message || "Catálogo atualizado.", "ok");
    }
    if (currentRoot) mount(currentRoot, storeRef);
  } else {
    toast(res.error || "Falha na operação.", "error");
  }
}

export const title = "Painel";
export const sub = "Visão geral do sistema";
export default { mount, title, sub };