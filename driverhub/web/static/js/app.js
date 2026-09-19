/* driverhub: app */
"use strict";

import { createStore } from "./store.js";
import { register, navigate, onChange, start } from "./router.js";
import { h, append, clear, el } from "./dom.js";
import { toast } from "./components/toast.js";
import { withSpinner } from "./components/spinner.js";
import { icon } from "./icons.js";
import { post } from "./api.js";

import dashboard from "./views/dashboard.js";
import devices from "./views/devices.js";
import drivers from "./views/drivers.js";
import catalog from "./views/catalog.js";
import history from "./views/history.js";
import hardware from "./views/hardware.js";
import settings from "./views/settings.js";

const store = createStore({ route: "", boot: null, loading: false, filters: {} });

const NAV = [
  { name: "dashboard", label: "Painel", icon: "home" },
  { name: "devices", label: "Dispositivos", icon: "drive" },
  { name: "drivers", label: "Drivers", icon: "box" },
  { name: "catalog", label: "Catálogo", icon: "download" },
  { name: "hardware", label: "Hardware", icon: "settings" },
  { name: "history", label: "Histórico", icon: "clock" },
  { name: "settings", label: "Configurações", icon: "settings" },
];

const VIEWS = { dashboard, devices, drivers, catalog, history, hardware, settings };

let content = null;
let titleEl = null;
let subEl = null;
let activeName = "";

function setActive(name) {
  activeName = name;
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
}

function renderView(name, params) {
  const view = VIEWS[name];
  if (!view) { navigate("dashboard"); return; }
  store.set({ route: name, params: params || {} });
  setActive(name);
  if (titleEl) titleEl.textContent = view.title || name;
  if (subEl) subEl.textContent = view.sub || "";
  clear(content);
  try {
    view.mount(content, store);
  } catch (err) {
    console.error("view", name, err);
    append(content, h("div", { class: "card", style: { borderColor: "var(--red)" } },
      h("p", { text: "Erro ao renderizar " + name + ": " + ((err && err.message) || err) })));
  }
}

function sidebar() {
  const nav = h("nav", { class: "nav" });
  NAV.forEach((item) => {
    append(nav, h("button", {
      class: "nav-item",
      "data-view": item.name,
      onclick: () => navigate(item.name),
    }, [h("span", { class: "ico", html: icon(item.icon) }), item.label]));
  });
  const foot = h("div", { class: "sidebar-foot" }, [
    h("div", { class: "badge muted", text: "DriverHub web" }),
  ]);
  return h("aside", { class: "sidebar" }, [
    h("div", { class: "brand" }, [
      h("div", { class: "logo", text: "DH" }),
      h("div", { class: "brand-text" }, [
        h("h1", { text: "DriverHub" }),
        h("span", { text: "gerenciador de drivers" }),
      ]),
    ]),
    nav,
    foot,
  ]);
}

function topbar() {
  titleEl = h("h2", { text: "Painel" });
  subEl = h("p", { text: "" });
  return h("header", { class: "topbar" }, [
    h("div", {}, [titleEl, subEl]),
    h("div", { class: "topbar-actions" }, [
      h("button", { class: "btn primary", onclick: () => quickAction("scan") },
        [h("span", { class: "ico", html: icon("refresh") }), " Escanear"]),
      h("button", { class: "btn", onclick: () => quickAction("catalog-update") },
        [h("span", { class: "ico", html: icon("download") }), " Catálogo"]),
    ]),
  ]);
}

async function quickAction(kind) {
  const res = await withSpinner(async () => {
    return kind === "scan"
      ? await post("/api/actions/scan", {})
      : await post("/api/actions/catalog-update", {});
  });
  if (res.ok) {
    if (kind === "scan") {
      toast("Varredura: " + (res.data.devices_count || 0) + " dispositivos, " + (res.data.drivers_count || 0) + " drivers.", "ok");
    } else {
      toast(res.data.message || "Catálogo atualizado.", "ok");
    }
    store.set({ lastAction: kind, lastActionAt: Date.now() });
    renderView(activeName, (store.getState() || {}).params);
  } else {
    toast(res.error || "Falha na operação.", "error");
  }
}

function layout() {
  let app = el("app");
  if (!app) {
    app = h("div", { id: "app", class: "app" });
    append(document.body, app);
  }
  const main = h("main", { class: "main" });
  append(main, topbar());
  content = h("section", { id: "view" });
  append(main, content);
  append(app, sidebar(), main);
}

function init() {
  layout();
  Object.keys(VIEWS).forEach((name) => register({ name, path: "/" + name }));
  onChange((name, params) => { if (name) renderView(name, params); });
  start();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}