// Tests of the script that holds back the search index on every page,
// overrides/partials/search-hold.js, which overrides/main.html includes inline, with
// Node alone: the script runs as the browser runs it, in a context of its own with a
// window, a document and an XMLHttpRequest that keeps what it sends.
// scripts/check-project.sh runs them, with every line, branch and function covered:
//   node --test tests/*.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const FILE = new URL("../overrides/partials/search-hold.js", import.meta.url);
const SOURCE = readFileSync(FILE, "utf8");
const TEMPLATE = readFileSync(new URL("../overrides/main.html", import.meta.url), "utf8");
// The address at which Material for MkDocs asks for the index, from its config.base.
const INDEX = "https://dennis-otto.github.io/search/search_index.json";

// A browser with the script: its XMLHttpRequest, which keeps the requests that it
// opens and sends, its listeners of window and document, its timers, and, when idle
// is true, requestIdleCallback.
const browser = ({ idle = true } = {}) => {
  const opened = [];
  const sent = [];
  class XMLHttpRequest {
    open(...args) {
      opened.push(args);
      this.url = String(args[1]);
      return `opened ${this.url}`;
    }

    send(...args) {
      sent.push([this.url, ...args]);
      return `sent ${this.url}`;
    }
  }
  const listeners = { window: [], document: [] };
  const timers = [];
  const idles = [];
  const context = {
    XMLHttpRequest,
    addEventListener: (type, run) => listeners.window.push([type, run]),
    setTimeout: (run, delay) => timers.push([run, delay]),
    document: { addEventListener: (type, run) => listeners.document.push([type, run]) },
  };
  if (idle) {
    context.requestIdleCallback = (run, options) => idles.push([run, options]);
  }
  context.window = context;
  vm.runInContext(SOURCE, vm.createContext(context), { filename: FILE.href });
  // A request to url, opened and sent with body.
  const request = (url, body = null) => {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.send(body);
    return xhr;
  };
  // The events of the page: load, the run of every timer and idle callback, and a
  // focus on target.
  const fire = (target, type, event) => {
    for (const [name, run] of listeners[target]) {
      if (name === type) {
        run(event);
      }
    }
  };
  const load = () => fire("window", "load");
  const tick = () => timers.splice(0).forEach(([run]) => run());
  const rest = () => idles.splice(0).forEach(([run]) => run());
  const focus = (target) => fire("document", "focusin", { target });
  return { XMLHttpRequest, opened, sent, listeners, timers, idles, request, load, tick, rest, focus };
};

// A target of a focus inside the element of the search, or outside it.
const inSearch = { closest: (selector) => (selector === ".md-search" ? {} : null) };
const elsewhere = { closest: () => null };

test("the page asks for the index only when the browser is idle after the load", () => {
  const page = browser();

  page.request(INDEX);
  // Opened, as Material asks, but not sent.
  assert.deepEqual(page.opened, [["GET", INDEX, true]]);
  assert.deepEqual(page.sent, []);

  page.load();
  assert.deepEqual(
    page.timers.map(([, delay]) => delay),
    [1000],
  );
  page.tick();
  assert.deepEqual(page.sent, []);
  assert.deepEqual(
    page.idles.map(([, options]) => ({ ...options })),
    [{ timeout: 2000 }],
  );
  page.rest();
  assert.deepEqual(page.sent, [[INDEX, null]]);
});

test("without requestIdleCallback, the page asks for the index a second after the load", () => {
  const page = browser({ idle: false });

  page.request(INDEX);
  page.load();
  assert.deepEqual(page.sent, []);
  page.tick();
  assert.deepEqual(page.sent, [[INDEX, null]]);
});

test("a focus in the search box asks for the index at once", () => {
  const page = browser();

  page.request(INDEX);
  // A focus elsewhere, or on a target without closest, such as the document, holds it.
  page.focus(elsewhere);
  page.focus({});
  assert.deepEqual(page.sent, []);
  page.focus(inSearch);
  assert.deepEqual(page.sent, [[INDEX, null]]);

  // The load sends it no second time, and later requests for it go at once.
  page.load();
  page.tick();
  page.rest();
  page.focus(inSearch);
  page.request(INDEX, "again");
  assert.deepEqual(page.sent, [
    [INDEX, null],
    [INDEX, "again"],
  ]);
});

test("every other request goes at once, with what the page gives it", () => {
  const page = browser();
  const xhr = new page.XMLHttpRequest();

  // The open and the send of the browser, with their arguments and their results.
  assert.equal(xhr.open("POST", "/api/data", false), "opened /api/data");
  assert.equal(xhr.send("body", "more"), "sent /api/data");
  page.request("/search/search_index.json.gz");
  page.request("/search/search_index.json?v=2");
  page.request("/assets/javascripts/workers/search.js");

  assert.deepEqual(page.opened[0], ["POST", "/api/data", false]);
  assert.deepEqual(page.sent, [
    ["/api/data", "body", "more"],
    ["/search/search_index.json.gz", null],
    ["/search/search_index.json?v=2", null],
    ["/assets/javascripts/workers/search.js", null],
  ]);
});

test("every held request for the index goes once, in its order, with its body", () => {
  const page = browser();

  page.request(INDEX, "first");
  // An address as a URL, and one of another language of the website.
  page.request(new URL(INDEX), "second");
  page.request("/de/search/search_index.json", "third");
  assert.deepEqual(page.sent, []);
  page.focus(inSearch);
  page.focus(inSearch);

  assert.deepEqual(page.sent, [
    [INDEX, "first"],
    [INDEX, "second"],
    ["/de/search/search_index.json", "third"],
  ]);
});

test("a request for the index that opens before the release and sends after it goes at once", () => {
  const page = browser();
  const xhr = new page.XMLHttpRequest();

  xhr.open("GET", INDEX);
  page.focus(inSearch);
  assert.equal(xhr.send(), `sent ${INDEX}`);
  assert.deepEqual(page.sent, [[INDEX]]);
});

test("every page includes the script before the scripts of the theme, and nothing else", () => {
  const scripts = [...TEMPLATE.matchAll(/<script([^>]*)>(.*?)<\/script>/gs)].map(
    ([, attributes, body]) => [attributes, body.trim()],
  );

  assert.deepEqual(scripts, [["", '{% include "partials/search-hold.js" %}']]);
  assert.ok(TEMPLATE.indexOf("</script>") < TEMPLATE.indexOf("{{ super() }}"));
});

test("the script holds nothing that Jinja or the page would read as their own", () => {
  // Jinja starts a part of its own with {{, {% or {#, and the end tag of a script would
  // end the script of the page in the middle.
  for (const mark of ["{{", "{%", "{#", "</script"]) {
    assert.equal(SOURCE.toLowerCase().includes(mark), false, mark);
  }
});
