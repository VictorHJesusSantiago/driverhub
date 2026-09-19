/* driverhub: format */
"use strict";

export function fmtBytes(n) {
  if (n === undefined || n === null || !isFinite(Number(n))) return "—";
  let v = Number(n);
  const neg = v < 0;
  v = Math.abs(v);
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  const digits = v >= 100 || i === 0 ? 0 : v >= 10 ? 1 : 2;
  return (neg ? "-" : "") + v.toFixed(digits).replace(".", ",") + " " + units[i];
}

export function fmtDuration(sec) {
  let s = Math.max(0, Math.round(Number(sec) || 0));
  const days = Math.floor(s / 86400); s %= 86400;
  const hours = Math.floor(s / 3600); s %= 3600;
  const mins = Math.floor(s / 60); s %= 60;
  if (days) return days + "d " + hours + "h " + mins + "m";
  if (hours) return hours + "h " + mins + "m";
  if (mins) return mins + "m " + s + "s";
  return s + "s";
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleString("pt-BR");
}

export function fmtPercent(n) {
  if (n === undefined || n === null || !isFinite(Number(n))) return "—";
  const raw = Math.abs(Number(n)) <= 1 ? Number(n) * 100 : Number(n);
  const digits = Math.abs(raw) >= 10 ? 0 : 1;
  return Number.isFinite(raw) ? raw.toFixed(digits).replace(".", ",") + "%" : "—";
}

export function ptBR(n) {
  const v = Number(n);
  return isFinite(v) ? new Intl.NumberFormat("pt-BR").format(v) : "0";
}

export default { fmtBytes, fmtDuration, fmtDate, fmtPercent, ptBR };