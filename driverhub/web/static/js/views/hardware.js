/* driverhub: views/hardware */
"use strict";

import { get } from "../api.js";
import { h, append, clear } from "../dom.js";
import { badge } from "../components/badge.js";
import { dataTable } from "../components/table.js";
import { toast } from "../components/toast.js";
import { spinner } from "../components/spinner.js";
import { fmtBytes, fmtPercent, fmtDate } from "../format.js";
import { bars, sparkline } from "../components/chart.js";

let currentRoot = null;

export function mount(root, store) {
  currentRoot = root;
  clear(root);
  append(root, h("div", { class: "card" }, spinner("Lendo hardware...")));
  get("/api/hardware").then((res) => {
    clear(currentRoot);
    if (!res.ok) {
      append(currentRoot, h("div", { class: "card" }, h("p", { class: "hint", text: "Falha ao ler hardware: " + res.error })));
      toast(res.error, "error");
      return;
    }
    render(currentRoot, res.data.hardware || {});
  });
}

function render(root, hw) {
  const os = hw.os || {};
  append(root, h("div", { class: "card hero" }, [
    h("div", { class: "os-name", text: os.name || "Sistema" }),
    h("div", { class: "meta", text: ["Kernel " + (os.kernel || os.release || ""), "Python " + os.python, os.arch, os.hostname].filter(Boolean).join(" · ") }),
    h("div", { class: "meta", text: "Classe: " + (hw.device_class || "?") + " · Coletado em " + fmtDate(hw.timestamp) }),
  ]));

  const cpu = hw.cpu || {};
  const ram = hw.ram || {};
  const ramPct = ram.total ? ram.used / ram.total : 0;
  const disks = hw.disks || [];
  const gpus = hw.gpu || [];
  const nics = hw.network || [];
  const sensors = hw.sensors || {};

  append(root, h("div", { class: "grid two" }, [
    card("Processador", [
      h("p", { text: cpu.name || "—" }),
      h("p", { class: "hint", text: "Núcleos: " + (cpu.cores || 0) + " · Threads: " + (cpu.threads || 0) + (cpu.freq_mhz ? " · " + cpu.freq_mhz + " MHz" : "") }),
    ]),
    card("Memória (RAM)", [
      h("p", { text: "Total " + fmtBytes(ram.total) + " · Usado " + fmtBytes(ram.used) }),
      h("div", { class: "chart", html: bars(ram.total ? { "usado": ram.used, "livre": Math.max(0, ram.total - ram.used) } : {}) }),
      h("p", { class: "hint", text: fmtPercent(ramPct) + " em uso" }),
    ]),
  ]));

  if (disks.length) {
    append(root, card("Discos", dataTable(
      ["Ponto de montagem", "Sistema de arquivos", "Tamanho", "Usado", "Uso"],
      disks.map((d) => [
        d.mount || d.device || "-",
        d.fstype || "-",
        fmtBytes(d.total),
        fmtBytes(d.used),
        d.total ? badge(fmtPercent(d.used / d.total), usageTone(d.used / d.total)) : badge("—", "info"),
      ]),
    )));
  }

  if (gpus.length) {
    append(root, card("Placas de vídeo", dataTable(
      ["Nome", "Fabricante", "Versão do driver"],
      gpus.map((g) => [g.name || "-", g.vendor || "-", g.driver_version || "-"]),
    )));
  }

  if (nics.length) {
    append(root, card("Rede", dataTable(
      ["Interface", "IP", "Velocidade", "Estado"],
      nics.map((n) => [n.name || "-", n.ip || "-", n.speed_mbps ? n.speed_mbps + " Mbps" : "—", badge(n.up ? "ativa" : "inativa", n.up ? "ok" : "warn")]),
    )));
  }

  renderSensors(root, sensors);
}

function renderSensors(root, sensors) {
  const temps = (sensors && sensors.temperatures) || {};
  const fans = (sensors && sensors.fans) || {};
  const bat = (sensors && sensors.battery) || null;
  const rows = [];
  Object.keys(temps).forEach((k) => rows.push(["Temperatura", k, temps[k] + " °C"]));
  Object.keys(fans).forEach((k) => rows.push(["Ventilador", k, fans[k] + " RPM"]));
  if (bat && bat.percent !== undefined) rows.push(["Bateria", "carga", (bat.plugged ? "na tomada · " : "") + bat.percent + "%"]);

  if (!rows.length) {
    append(root, card("Sensores", h("p", { class: "hint", text: "Nenhum sensor detectado." })));
    return;
  }
  const tempsOnly = Object.keys(temps).map((k) => temps[k]);
  append(root, card("Sensores", [
    tempsOnly.length ? h("div", { class: "chart" }, [
      h("div", { html: sparkline(tempsOnly) }),
      h("span", { class: "hint", text: "Temperaturas (°C)" }),
    ]) : null,
    dataTable(["Tipo", "Item", "Valor"], rows),
  ]));
}

function usageTone(ratio) {
  if (ratio >= 0.95) return "error";
  if (ratio >= 0.8) return "warn";
  return "ok";
}

function card(title, body) {
  return h("div", { class: "card" }, [h("h3", { text: title }), body]);
}

export const title = "Hardware";
export const sub = "Detalhes do hardware real";
export default { mount, title, sub };