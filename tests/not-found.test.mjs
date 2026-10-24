// Tests of the script of the 404 page, overrides/partials/not-found.js, which
// overrides/404.html includes inline, with Node alone: the script runs as the browser
// runs it, in a context of its own with a small page, its data and an address.
// scripts/check-project.sh runs them, with every line, branch and function covered:
//   node --test tests/*.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const FILE = new URL("../overrides/partials/not-found.js", import.meta.url);
const SOURCE = readFileSync(FILE, "utf8");
const TEMPLATE = readFileSync(new URL("../overrides/404.html", import.meta.url), "utf8");
const SITE = "https://dennis-otto.github.io/";

// A project of the data, as catalog.directory() of .github/mkdocs_project.py writes
// it: its website, and the same name, in English and German.
const project = (slug, name, former = [], url = `${SITE}${slug}/`) => ({
  slug,
  former,
  name: { en: name, de: name },
  url: { en: url, de: url === `${SITE}${slug}/` ? `${url}de/` : url },
});
// The projects of projects.toml on the day of these tests, in its order.
const PROJECTS = [
  project("homedarts-for-autodarts", "HomeDarts for Autodarts", ["ha-autodarts"]),
  project("player-switch-for-autodarts", "Player Switch for Autodarts"),
  project("paperless-sync", "Paperless Sync"),
  project("paperless-unified-search", "Paperless Unified Search"),
  project("issue-assistant", "Issue assistant"),
  project("repo-blueprint", "Repo Blueprint"),
  project("dashboard", "Dashboard", [], `${SITE}repo-blueprint/dashboard/`),
];
const MOVES = { "ha-autodarts": `${SITE}homedarts-for-autodarts/` };

// An element of the page, with as much of the DOM as the script uses.
class Element {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
  }

  append(...nodes) {
    this.children.push(...nodes);
  }

  // Its text, with every link as [text](address).
  get markdown() {
    return this.children
      .map((child) => (typeof child === "string" ? child : `[${child.textContent}](${child.href})`))
      .join("");
  }
}

// What the script does at address, a path with its query and its fragment, on a page
// whose #not-found-data holds data, as text: the box of its suggestion, and the
// addresses that it leads to with location.replace.
const at = (address, data = JSON.stringify({ moves: MOVES, projects: PROJECTS })) => {
  const { pathname, search, hash } = new URL(address, SITE);
  const replaced = [];
  const box = new Element("div");
  const elements = {
    "did-you-mean": box,
    "not-found-data": data === null ? null : { textContent: data },
  };
  const document = {
    createElement: (tag) => new Element(tag),
    getElementById: (id) => elements[id] ?? null,
  };
  const location = { pathname, search, hash, replace: (url) => replaced.push(url) };
  vm.runInContext(SOURCE, vm.createContext({ document, location }), { filename: FILE.href });
  return { box, replaced };
};

// What the page suggests at path: its question in each language, with every link as
// [name](address); nothing when it suggests nothing. It leads nowhere else.
const suggestion = (path, projects = PROJECTS) => {
  const { box, replaced } = at(path, JSON.stringify({ moves: MOVES, projects }));
  assert.deepEqual(replaced, []);
  if (box.children.length === 0) {
    assert.equal(box.className, undefined);
    return {};
  }
  assert.equal(box.className, "admonition question");
  const [english, german] = box.children;
  assert.equal(english.className, "admonition-title");
  assert.equal(german.className, undefined);
  assert.deepEqual(
    box.children.map((line) => [line.tagName, line.lang]),
    [
      ["p", "en"],
      ["p", "de"],
    ],
  );
  return { en: english.markdown, de: german.markdown };
};

test("an old address leads to the same path in the new folder, with its query and fragment", () => {
  // Such as a picture, or a page that the old website had not yet when its pages were
  // listed in former/ha-autodarts.txt.
  for (const [address, target] of [
    ["/ha-autodarts", ""],
    ["/ha-autodarts/", ""],
    ["/ha-autodarts/images/en/hero.webp", "images/en/hero.webp"],
    ["/ha-autodarts/de/new-name.html?h=name#why", "de/new-name.html?h=name#why"],
    ["/HA-Autodarts/demo/#cricket", "demo/#cricket"],
    ["/ha-autodarts/de/", "de/"],
    ["/ha%2Dautodarts/demo/", "demo/"],
  ]) {
    const { box, replaced } = at(address);

    assert.deepEqual(replaced, [`${SITE}homedarts-for-autodarts/${target}`], address);
    assert.deepEqual(box.children, [], address);
  }
});

test("a folder that only looks like an old one leads nowhere", () => {
  // Not a key of the moves: a name of Object.prototype, or a folder that starts like
  // an old one.
  for (const path of ["/constructor/", "/__proto__/", "/ha-autodarts-v1/x.html"]) {
    assert.deepEqual(at(path).replaced, [], path);
  }
});

test("both projects for Autodarts are suggested for /autodarts/", () => {
  for (const path of ["/autodarts/", "/Autodarts"]) {
    assert.deepEqual(suggestion(path), {
      en: `Did you mean [HomeDarts for Autodarts](${SITE}homedarts-for-autodarts/)` +
        ` or [Player Switch for Autodarts](${SITE}player-switch-for-autodarts/)?`,
      de: `Meintest du [HomeDarts for Autodarts](${SITE}homedarts-for-autodarts/de/)` +
        ` oder [Player Switch for Autodarts](${SITE}player-switch-for-autodarts/de/)?`,
    });
  }
});

test("a project is suggested for its slug, a word of it, a typo or an old folder", () => {
  const cases = [
    ["/player-switch/", ["player-switch-for-autodarts"]],
    ["/playerswitch-for-autodarts", ["player-switch-for-autodarts"]],
    ["/homedarts/", ["homedarts-for-autodarts"]],
    ["/homedarts-for-autodart/", ["homedarts-for-autodarts"]],
    // Like the folder where its website lived before.
    ["/ha-autodart/", ["homedarts-for-autodarts"]],
    ["/ha-autodarts-v1/x.html", ["homedarts-for-autodarts"]],
    ["/paperless/", ["paperless-sync", "paperless-unified-search"]],
    ["/search/", ["paperless-unified-search"]],
    ["/blueprint/", ["repo-blueprint"]],
    ["/dashbord/", ["dashboard"]],
    ["/issue-asistant/", ["issue-assistant"]],
  ];
  const projects = new Map(PROJECTS.map((item) => [item.slug, item]));
  for (const [path, slugs] of cases) {
    const links = slugs.map((slug) => projects.get(slug)).map((item) => [
      `[${item.name.en}](${item.url.en})`,
      `[${item.name.de}](${item.url.de})`,
    ]);

    assert.deepEqual(
      suggestion(path),
      {
        en: `Did you mean ${links.map(([en]) => en).join(" or ")}?`,
        de: `Meintest du ${links.map(([, de]) => de).join(" oder ")}?`,
      },
      path,
    );
  }
});

test("the closest project comes first, and a list of three takes a comma", () => {
  const projects = ["ketchup", "kitten", "kitchen"].map((slug) =>
    project(slug, slug, [], `https://example.org/${slug}/`),
  );

  // 1, 2 and 3 letters differ.
  assert.deepEqual(suggestion("/kitchn/", projects), {
    en: "Did you mean [kitchen](https://example.org/kitchen/), " +
      "[kitten](https://example.org/kitten/) or [ketchup](https://example.org/ketchup/)?",
    de: "Meintest du [kitchen](https://example.org/kitchen/), " +
      "[kitten](https://example.org/kitten/) oder [ketchup](https://example.org/ketchup/)?",
  });
});

test("the name and the website of a project are those of each language", () => {
  const projects = [
    {
      slug: "tool",
      former: [],
      name: { en: "The tool", de: "Das Werkzeug" },
      url: { en: "https://example.org/tool/", de: "https://example.org/werkzeug/" },
    },
  ];

  assert.deepEqual(suggestion("/tol/", projects), {
    en: "Did you mean [The tool](https://example.org/tool/)?",
    de: "Meintest du [Das Werkzeug](https://example.org/werkzeug/)?",
  });
});

test("an address unlike every project suggests nothing", () => {
  for (const path of ["/", "/a/", "/xyz/", "/de/foo.html", "/impressum.html"]) {
    assert.deepEqual(suggestion(path), {}, path);
  }
});

test("an address that is no valid URI leaves the page as it is", () => {
  for (const path of ["/%E0%A4%A/", "/ha-autodarts%E0/x.html", "/%/"]) {
    const { box, replaced } = at(path);

    assert.deepEqual([box.children, replaced], [[], []], path);
  }
});

test("a page without its data, or with broken data, leaves the page as it is", () => {
  for (const data of [null, "", "{not json", "null"]) {
    const { box, replaced } = at("/ha-autodarts/", data);

    assert.deepEqual([box.children, replaced], [[], []], String(data));
  }
});

test("the 404 page gives the script its data and includes it, and nothing else", () => {
  const scripts = [...TEMPLATE.matchAll(/<script([^>]*)>(.*?)<\/script>/gs)].map(
    ([, attributes, body]) => [attributes, body.trim()],
  );

  assert.deepEqual(scripts, [
    [
      ' type="application/json" id="not-found-data"',
      '{{ {"moves": catalog.moves(), "projects": catalog.directory()} | tojson }}',
    ],
    ["", '{% include "partials/not-found.js" %}'],
  ]);
  assert.match(TEMPLATE, /<div id="did-you-mean"><\/div>/);
});

test("the script holds nothing that Jinja or the page would read as their own", () => {
  // Jinja starts a part of its own with {{, {% or {#, and the end tag of a script would
  // end the script of the page in the middle.
  for (const mark of ["{{", "{%", "{#", "</script"]) {
    assert.equal(SOURCE.toLowerCase().includes(mark), false, mark);
  }
});
