/* driverhub: store */
"use strict";

import { deepClone } from "./utils.js";

export function createStore(initial = {}) {
  const base = deepClone(initial);
  let state = deepClone(base);
  const subs = new Set();

  function emit() {
    subs.forEach((fn) => {
      try { fn(state); } catch (err) { console.error("store listener", err); }
    });
  }

  return {
    getState() { return state; },
    set(partial) {
      state = Object.assign({}, state, deepClone(partial || {}));
      emit();
      return state;
    },
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    reset() {
      state = deepClone(base);
      emit();
      return state;
    },
  };
}

export const store = createStore({
  route: "",
  loading: false,
  boot: null,
  stats: null,
  filters: {},
  params: {},
});

export default store;