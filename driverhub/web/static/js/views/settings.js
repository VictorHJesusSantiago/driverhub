/* driverhub: views/settings */
"use strict";

import { post } from "../api.js";
import { h, append, clear, el } from "../dom.js";
import { badge } from "../components/badge.js";
import { toast } from "../components/toast.js";
import { withSpinner } from "../components/spinner.js";

let currentRoot = null;
let resultBox = null;

const DEFAULTS = {
  auto_scan_interval: "60",
  language: "pt-BR",
  theme: "auto",
  notifications: true,
};

export function mount(root, store) {
  currentRoot = root;
  clear(root);
  append(root, h("div", { style: { display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "16px", alignItems: "start" } }, [
    h("div", { class: "card" }, [
      h("h3", { text: "Configurações do painel" }),
      field("Intervalo de varredura automática (minutos)",
        h("input", { class: "input", id: "set-interval", type: "number", min: "1", value: DEFAULTS.auto_scan_interval })),
      field("Idioma",
        h("select", { class: "input select", id: "set-language" }, [
          h("option", { value: "pt-BR", text: "Português (Brasil)" }),
          h("option", { value: "en", text: "English" }),
        ])),
      field("Tema",
        h("select", { class: "input select", id: "set-theme" }, [
          h("option", { value: "auto", text: "Auto" }),
          h("option", { value: "dark", text: "Escuro" }),
          h("option", { value: "neon", text: "Neon" }),
        ])),
      field("Notificações",
        h("label", { style: { display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" } }, [
          h("input", { id: "set-notifications", type: "checkbox", checked: DEFAULTS.notifications }),
          " Habilitar avisos de problema",
        ])),
      h("div", { class: "toolbar" }, [
        h("button", { class: "btn primary", onclick: save }, [h("span", { text: "✓" }), " Salvar"]),
        h("button", { class: "btn", text: "Restaurar padrão", onclick: resetForm }),
      ]),
      (resultBox = h("div", { style: { marginTop: "8px" } })),
    ]),
    h("div", { class: "card" }, [
      h("h3", { text: "Informações" }),
      h("p", { class: "hint", text: "As configurações são enviadas ao servidor por POST /api/settings e lidas pelo painel." }),
      h("p", {}, [badge("beta", "warn"), " Função em desenvolvimento."]),
    ]),
  ]));
}

async function save() {
  const payload = {
    auto_scan_interval: (el("set-interval") || {}).value || "60",
    language: (el("set-language") || {}).value || "pt-BR",
    theme: (el("set-theme") || {}).value || "auto",
    notifications: !!(el("set-notifications") || {}).checked,
  };
  clear(resultBox);
  append(resultBox, h("p", { class: "hint", text: "Salvando..." }));
  const res = await withSpinner(() => post("/api/settings", payload, true));
  clear(resultBox);
  if (res.ok) {
    append(resultBox, h("p", {}, [badge("salvo", "ok"), " Configurações salvas no servidor."]));
    toast("Configurações salvas.", "ok");
  } else {
    append(resultBox, h("p", {}, [badge("erro", "error"), " " + (res.error || "Não foi possível salvar.")]));
    toast("Falha ao salvar: " + (res.error || "erro desconhecido"), "error");
  }
}

function resetForm() {
  const maps = { "set-interval": DEFAULTS.auto_scan_interval, "set-language": DEFAULTS.language, "set-theme": DEFAULTS.theme };
  for (const id of Object.keys(maps)) {
    const inp = el(id);
    if (inp) inp.value = maps[id];
  }
  const notif = el("set-notifications");
  if (notif) notif.checked = DEFAULTS.notifications;
}

function field(labelText, widget) {
  return h("p", { style: { marginBottom: "14px" } }, [
    h("label", { text: labelText, style: { display: "block", color: "var(--muted)", fontSize: "13px", marginBottom: "6px" } }),
    widget,
  ]);
}

export const title = "Configurações";
export const sub = "Preferências do painel";
export default { mount, title, sub };