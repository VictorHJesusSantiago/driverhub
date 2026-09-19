/* driverhub: router */
"use strict";

import { qs } from "./utils.js";

export const routes = [];
const listeners = new Set();
let currentName = "";
let currentParams = {};

export function register(route) {
  if (!route || !route.name) return () => {};
  routes.push(route);
  return () => {
    const i = routes.indexOf(route);
    if (i >= 0) routes.splice(i, 1);
  };
}

function hashOf(name, params = {}) {
  const route = routes.find((r) => r.name === name);
  const path = (route && route.path ? route.path : "/" + name).replace(/^#/, "");
  const query = qs(params || {});
  return "#" + path + (query ? "?" + query : "");
}

export function navigate(name, params = {}) {
  go(hashOf(name, params));
}

export function go(path) {
  const target = String(path || "#/").replace(/^#?/, "#");
  if (window.location.hash === target) {
    dispatch();
  } else {
    window.location.hash = target;
  }
}

export function parse_hash() {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const slice = raw.split("?");
  const viewPath = slice[0] || "/";
  const name = viewPath.split("/").filter(Boolean)[0] || "";
  const params = {};
  try {
    new URLSearchParams(slice[1] || "").forEach((v, k) => { params[k] = v; });
  } catch (err) {
    console.error("router params", err);
  }
  return { name, path: viewPath, params };
}

function dispatch() {
  const parsed = parse_hash();
  currentName = parsed.name;
  currentParams = parsed.params;
  listeners.forEach((fn) => {
    try {
      fn(parsed.name, parsed.params);
    } catch (err) {
      console.error("router listener", err);
    }
  });
}

export function onChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function getRoute() { return currentName; }
export function getParams() { return currentParams; }

export function start() {
  window.addEventListener("hashchange", dispatch);
  dispatch();
  return () => window.removeEventListener("hashchange", dispatch);
}

export default { routes, register, navigate, go, parse_hash, onChange, getRoute, getParams, start };