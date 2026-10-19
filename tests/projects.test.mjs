// Tests of the live facts of the home pages, docs/javascripts/projects.js, with Node
// alone: a small document of their own stands in for the browser's, and a fake
// fetch for the data of the dashboard. scripts/check-project.sh runs them:
//   node --test tests/*.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const projects = require("../docs/javascripts/projects.js");

const FIXTURE = JSON.parse(readFileSync(new URL("fixtures/repos.json", import.meta.url), "utf8"));
const FEED = "/repo-blueprint/dashboard/repos.json";
const HISTORY = "/repo-blueprint/dashboard/history.json";
// The day of the fixture, at noon in UTC.
const NOW = new Date("2026-10-19T12:00:00Z");
// The narrow space without a break that German puts before a percent sign.
const NBSP = " ";

// The texts of [facts] in projects.toml, as the hook writes them into the page.
const TEXTS = {
  en: {
    label: "Release and quality",
    released: "released {}",
    coverage: "{} test coverage",
    mutation: "{} mutation score",
    scorecard: "Scorecard {}",
    answer: "first answer by a person in {}",
    feed: "Releases of all projects",
  },
  de: {
    label: "Release und Qualität",
    released: "veröffentlicht {}",
    coverage: "{} Testabdeckung",
    mutation: "{} Mutations-Score",
    scorecard: "Scorecard {}",
    answer: "erste Antwort eines Menschen nach {}",
    feed: "Releases aller Projekte",
  },
};
const CARDS = {
  en: [
    ["Dennis-Otto/ha-autodarts", "Autodarts for Home Assistant"],
    ["Dennis-Otto/paperless-sync", "Paperless Sync"],
    ["Dennis-Otto/paperless-unified-search", "Paperless Unified Search"],
    ["Dennis-Otto/issue-assistant", "Issue assistant"],
    ["Dennis-Otto/repo-blueprint", "Repo Blueprint"],
  ],
};
CARDS.de = CARDS.en.map(([repo, name]) => [
  repo,
  name.replace("Autodarts for", "Autodarts für"),
]);

// An element of the document, with as much of the DOM as the script uses.
class Element {
  constructor(tag, attributes = {}, children = []) {
    this.tagName = tag;
    this.attributes = new Map(Object.entries(attributes));
    this.children = [];
    this.parent = null;
    this.append(...children);
  }

  get dataset() {
    const data = {};
    for (const [name, value] of this.attributes) {
      if (name.startsWith("data-")) {
        data[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = value;
      }
    }
    return data;
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  adopt(node) {
    if (node instanceof Element) {
      node.remove();
      node.parent = this;
    }
    return node;
  }

  append(...nodes) {
    this.children.push(...nodes.map((node) => this.adopt(node)));
  }

  prepend(...nodes) {
    this.children.unshift(...nodes.map((node) => this.adopt(node)));
  }

  replaceChildren(...nodes) {
    for (const child of [...this.children]) {
      if (child instanceof Element) {
        child.remove();
      }
    }
    this.children = [];
    this.append(...nodes);
  }

  remove() {
    if (this.parent) {
      this.parent.children = this.parent.children.filter((child) => child !== this);
      this.parent = null;
    }
  }

  get textContent() {
    return this.children
      .map((child) => (child instanceof Element ? child.textContent : child))
      .join("");
  }

  set textContent(text) {
    this.replaceChildren(String(text));
  }

  // The elements below this one, in the order of the document.
  *descendants() {
    for (const child of this.children) {
      if (child instanceof Element) {
        yield child;
        yield* child.descendants();
      }
    }
  }

  // A selector of a tag, classes and attributes, such as .project-facts[data-repo].
  matches(selector) {
    const [, tag, classes, attributes] = /^([a-z]*)((?:\.[\w-]+)*)((?:\[[\w-]+\])*)$/.exec(
      selector,
    );
    const own = (this.getAttribute("class") ?? "").split(" ");
    return (
      (!tag || tag === this.tagName) &&
      [...classes.matchAll(/\.([\w-]+)/g)].every(([, name]) => own.includes(name)) &&
      [...attributes.matchAll(/\[([\w-]+)\]/g)].every(([, name]) => this.attributes.has(name))
    );
  }

  querySelectorAll(selector) {
    return [...this.descendants()].filter((element) => element.matches(selector));
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] ?? null;
  }

  // The element as HTML, for the messages of a failed test.
  get outerHTML() {
    const attributes = [...this.attributes].map(([name, value]) => ` ${name}="${value}"`);
    const inner = this.children
      .map((child) => (child instanceof Element ? child.outerHTML : child))
      .join("");
    return `<${this.tagName}${attributes.join("")}>${inner}</${this.tagName}>`;
  }
}

class Document extends Element {
  constructor(...children) {
    super("body", {}, children);
  }

  createElement(tag) {
    return new Element(tag);
  }
}

// The facts that the build puts into a card: the level of its OpenSSF Best Practices.
const LEVEL = { en: "OpenSSF Best Practices: silver", de: "OpenSSF Best Practices: Silber" };
const built = (language) =>
  new Element("ul", { class: "project-facts__list", "aria-label": TEXTS[language].label }, [
    new Element("li", {}, [
      new Element("a", { href: "https://www.bestpractices.dev/projects/1" }, [LEVEL[language]]),
    ]),
  ]);

// A home page in the language, as the hook writes it, with the cards of these repos;
// the build read the level of every project but the blueprint.
const homePage = (language = "en", cards = CARDS[language]) => {
  const data = Object.fromEntries(
    Object.entries(TEXTS[language]).map(([key, text]) => [`data-${key}`, text]),
  );
  const place = new Element(
    "div",
    {
      class: "projects",
      id: "projects",
      "data-facts": FEED,
      "data-history": HISTORY,
      "data-locale": language,
      ...data,
    },
    cards.map(
      ([repo, name]) =>
        new Element("div", { class: "card" }, [
          new Element(
            "div",
            { class: "project-facts", "data-repo": repo, "data-name": name },
            repo === "Dennis-Otto/repo-blueprint" ? [] : [built(language)],
          ),
        ]),
    ),
  );
  const news = new Element("div", { class: "project-news", "data-count": "5" });
  return new Document(place, news);
};

// A fetch that answers each address with its data, an error or a 404 for any other,
// and keeps the addresses that it was asked for.
const fetcher = (answers) => {
  const asked = [];
  const fetch = async (url) => {
    asked.push(url);
    const answer = answers[url];
    if (answer instanceof Error) {
      throw answer;
    }
    if (answer === undefined) {
      return { ok: false, status: 404, json: async () => assert.fail("no body") };
    }
    return { ok: true, status: 200, json: async () => structuredClone(answer) };
  };
  return Object.assign(fetch, { asked });
};

const factsOf = (document, repo) =>
  document
    .querySelectorAll(".project-facts")
    .find((element) => element.dataset.repo === repo);

const items = (element) =>
  element.querySelector(".project-facts__list")?.children.map((item) => item.textContent) ?? [];

const show = async (language = "en", answers = { [FEED]: FIXTURE }, cards = undefined) => {
  const document = homePage(language, cards);
  const fetch = fetcher(answers);
  await projects.start(document, fetch, NOW);
  return { document, fetch };
};

test("every card shows its release, its date and its quality numbers in English", async () => {
  const { document } = await show();

  const card = factsOf(document, "Dennis-Otto/ha-autodarts");
  const list = card.querySelector(".project-facts__list");
  assert.equal(list.tagName, "ul");
  assert.equal(list.getAttribute("aria-label"), "Release and quality");
  assert.deepEqual(items(card), [
    "v1.17.0",
    "released today",
    "100% test coverage",
    "90% mutation score",
    "Scorecard 7.8",
    "first answer by a person in 1 hour",
    LEVEL.en,
  ]);
  // In front of the facts of the build, in their list.
  assert.deepEqual(card.children, [list]);
  assert.equal(list.children.at(-1).getAttribute("data-live"), null);
  assert.equal(list.children[0].getAttribute("data-live"), "");
  const [release, date, , , scorecard] = list.children.map((item) => item.children[0]);
  assert.equal(
    release.getAttribute("href"),
    "https://github.com/Dennis-Otto/ha-autodarts/releases/tag/v1.17.0",
  );
  assert.equal(date.tagName, "time");
  assert.equal(date.getAttribute("datetime"), "2026-10-19");
  assert.equal(date.getAttribute("title"), "October 19, 2026");
  assert.equal(
    scorecard.getAttribute("href"),
    "https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/ha-autodarts",
  );
  assert.deepEqual(items(factsOf(document, "Dennis-Otto/paperless-sync")), [
    "v1.0.0",
    "released yesterday",
    "100% test coverage",
    "95% mutation score",
    "Scorecard 7.3",
    "first answer by a person in 8 minutes",
    LEVEL.en,
  ]);
  // A fact without its value, such as the mutation score of the blueprint, is left
  // out, and a card without facts of the build gets a list of its own.
  const blueprint = factsOf(document, "Dennis-Otto/repo-blueprint");
  assert.deepEqual(items(blueprint), [
    "v0.13.3",
    "released today",
    "100% test coverage",
    "Scorecard 7.8",
  ]);
  assert.equal(blueprint.children[0].getAttribute("aria-label"), "Release and quality");
});

test("every card shows its facts in German on the German home page", async () => {
  const { document } = await show("de");

  const card = factsOf(document, "Dennis-Otto/paperless-unified-search");
  assert.equal(
    card.querySelector(".project-facts__list").getAttribute("aria-label"),
    "Release und Qualität",
  );
  assert.deepEqual(items(card), [
    "v1.1.0",
    "veröffentlicht vorgestern",
    `100${NBSP}% Testabdeckung`,
    `96${NBSP}% Mutations-Score`,
    "Scorecard 7,4",
    LEVEL.de,
  ]);
  assert.equal(card.querySelector("time").getAttribute("title"), "17. Oktober 2026");
  assert.equal(
    items(factsOf(document, "Dennis-Otto/paperless-sync")).at(-2),
    "erste Antwort eines Menschen nach 8 Minuten",
  );
});

test("the page asks the same origin for the data of the dashboard alone", async () => {
  const { fetch } = await show();

  assert.deepEqual(fetch.asked, [FEED]);
});

test("a card whose repository the data lacks keeps what the build put into it", async () => {
  const cards = [...CARDS.en, ["Dennis-Otto/new-project", "A new project"]];
  const { document } = await show("en", { [FEED]: FIXTURE }, cards);

  assert.deepEqual(items(factsOf(document, "Dennis-Otto/new-project")), [LEVEL.en]);
});

test("a fact without its value or with a broken one is left out", async () => {
  const data = structuredClone(FIXTURE);
  const [, autodarts, issues, sync, search] = data.repos;
  Object.assign(autodarts, { release: null, released: null, health: null });
  Object.assign(issues, { released: "2026-13-45", scorecard: 11, release_url: null });
  issues.health = { coverage: "100", mutation: -1, answer_hours: Number.NaN };
  Object.assign(sync, { release_url: "javascript:alert(1)", released: "yesterday" });
  delete search.health;
  delete search.scorecard;
  const { document } = await show("en", { [FEED]: data });

  assert.deepEqual(items(factsOf(document, "Dennis-Otto/ha-autodarts")), [
    "Scorecard 7.8",
    LEVEL.en,
  ]);
  const issueFacts = factsOf(document, "Dennis-Otto/issue-assistant");
  assert.deepEqual(items(issueFacts), ["v1.5.0", LEVEL.en]);
  // A release without its address, or with one outside GitHub, is text, not a link.
  assert.equal(issueFacts.querySelector(".project-facts__list").children[0].children[0], "v1.5.0");
  const syncFacts = factsOf(document, "Dennis-Otto/paperless-sync");
  assert.equal(syncFacts.querySelector(".project-facts__list").children[0].children[0], "v1.0.0");
  assert.deepEqual(items(factsOf(document, "Dennis-Otto/paperless-unified-search")), [
    "v1.1.0",
    "released 2 days ago",
    LEVEL.en,
  ]);
});

test("a card with no fact in the data keeps the facts of the build alone", async () => {
  const data = {
    schema: 1,
    repos: [{ repo: "Dennis-Otto/ha-autodarts" }, { repo: "Dennis-Otto/repo-blueprint" }],
  };
  const { document } = await show("en", { [FEED]: data });

  assert.deepEqual(items(factsOf(document, "Dennis-Otto/ha-autodarts")), [LEVEL.en]);
  assert.deepEqual(factsOf(document, "Dennis-Otto/repo-blueprint").children, []);
  assert.equal(document.querySelector("[data-live]"), null);
});

for (const [name, answers] of [
  ["a failed request", { [FEED]: new TypeError("Failed to fetch"), [HISTORY]: new Error("x") }],
  ["no data at all", {}],
  ["data of another shape", { [FEED]: { repos: {} }, [HISTORY]: { days: [] } }],
]) {
  test(`after ${name}, the cards keep what the build put into them`, async () => {
    const { document, fetch } = await show("en", answers);

    assert.deepEqual(fetch.asked, [FEED, HISTORY]);
    assert.equal(document.querySelector("[data-live]"), null);
    assert.deepEqual(
      document.querySelectorAll(".project-facts").map(items),
      [[LEVEL.en], [LEVEL.en], [LEVEL.en], [LEVEL.en], []],
    );
    assert.deepEqual(document.querySelector(".project-news").children, []);
  });
}

const HISTORY_DAYS = [
  {
    date: "2026-10-18",
    repos: { "Dennis-Otto/ha-autodarts": { coverage: 99, mutation: 80, answer_hours: 2 } },
  },
  {
    date: "2026-10-19",
    repos: {
      "Dennis-Otto/ha-autodarts": { coverage: 100, mutation: 90.5, answer_hours: 50 },
    },
  },
  { date: "2026-10-17", repos: { "Dennis-Otto/ha-autodarts": { coverage: 1 } } },
  null,
];

for (const [name, feed] of [
  ["repos.json can't be read", new Error("offline")],
  ["repos.json has a newer shape", { ...FIXTURE, schema: 2 }],
]) {
  test(`when ${name}, the cards show the numbers of the latest day of history.json`, async () => {
    const { document, fetch } = await show("en", { [FEED]: feed, [HISTORY]: HISTORY_DAYS });

    assert.deepEqual(fetch.asked, [FEED, HISTORY]);
    assert.deepEqual(items(factsOf(document, "Dennis-Otto/ha-autodarts")), [
      "100% test coverage",
      "90% mutation score",
      "first answer by a person in 2 days",
      LEVEL.en,
    ]);
    assert.deepEqual(items(factsOf(document, "Dennis-Otto/paperless-sync")), [LEVEL.en]);
    // History has no releases, so What's new keeps its sentence alone.
    assert.deepEqual(document.querySelector(".project-news").children, []);
  });
}

test("What's new lists the five newest releases of the projects, newest first", async () => {
  const { document } = await show();

  const list = document.querySelector(".project-news").children[0];
  assert.equal(list.getAttribute("class"), "project-news__list");
  // One for each project on a card, and of a day in the order of the cards: not the
  // website itself or a repository without a card, such as player-switch-for-autodarts.
  assert.deepEqual(
    list.children.map((item) => item.textContent),
    [
      "Autodarts for Home Assistant v1.17.0 today",
      "Repo Blueprint v0.13.3 today",
      "Paperless Sync v1.0.0 yesterday",
      "Paperless Unified Search v1.1.0 2 days ago",
      "Issue assistant v1.5.0 5 days ago",
    ],
  );
  const [link, , time] = list.children[2].children;
  assert.equal(link.getAttribute("href"), FIXTURE.repos[3].release_url);
  assert.equal(time.getAttribute("datetime"), "2026-10-18");
  assert.equal(time.getAttribute("title"), "October 18, 2026");
});

test("What's new lists as many releases as its place asks for, in German", async () => {
  const document = homePage("de");
  document.querySelector(".project-news").setAttribute("data-count", "2");

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.deepEqual(
    document.querySelector(".project-news__list").children.map((item) => item.textContent),
    ["Autodarts für Home Assistant v1.17.0 heute", "Repo Blueprint v0.13.3 heute"],
  );
});

test("a second run, as after instant loading, shows every fact once", async () => {
  const { document } = await show();
  const first = document.querySelectorAll(".project-facts").map(items);

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.deepEqual(document.querySelectorAll(".project-facts").map(items), first);
  assert.equal(document.querySelectorAll(".project-facts__list").length, 5);
  assert.equal(document.querySelectorAll(".project-news__list").length, 1);
});

test("a second run without data takes the facts of the first away", async () => {
  const { document } = await show();

  await projects.start(document, fetcher({}), NOW);

  assert.equal(document.querySelector("[data-live]"), null);
  assert.deepEqual(factsOf(document, "Dennis-Otto/repo-blueprint").children, []);
  assert.deepEqual(document.querySelector(".project-news").children, []);
});

test("a page without the place of the facts asks for nothing", async () => {
  const document = new Document(new Element("div", { class: "card" }));
  const fetch = fetcher({});

  await projects.start(document, fetch, NOW);

  assert.deepEqual(fetch.asked, []);
});

test("a page without What's new still fills its cards", async () => {
  const document = homePage();
  document.querySelector(".project-news").remove();

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.equal(items(factsOf(document, "Dennis-Otto/issue-assistant"))[0], "v1.5.0");
});

// The Trust page in the language, as the hook writes it: the place of the data, and
// a cell for every value of the script of every repository, with what the build put
// into it, a link to the releases on GitHub or a dash.
const LIVE = ["release", "coverage", "mutation", "scorecard"];
const REPOS = CARDS.en.map(([repo]) => repo);
const builtCell = (repo, fact) =>
  fact === "release"
    ? [new Element("a", { href: `https://github.com/${repo}/releases/latest` }, ["GitHub"])]
    : ["—"];
const trustPage = (language = "en", repos = REPOS, facts = LIVE) => {
  const rows = facts.map(
    (fact) =>
      new Element("tr", {}, [
        new Element("th", { scope: "row" }, [fact]),
        ...repos.map(
          (repo) =>
            new Element("td", { "data-repo": repo, "data-fact": fact }, builtCell(repo, fact)),
        ),
      ]),
  );
  const place = new Element(
    "div",
    { class: "trust", "data-facts": FEED, "data-history": HISTORY, "data-locale": language },
    [new Element("table", {}, [new Element("tbody", {}, rows)])],
  );
  return new Document(place);
};

const cellOf = (document, repo, fact) =>
  document
    .querySelectorAll("td[data-fact]")
    .find((cell) => cell.dataset.repo === repo && cell.dataset.fact === fact);

const row = (document, fact) => REPOS.map((repo) => cellOf(document, repo, fact).textContent);

const cellsOf = (document) =>
  document.querySelectorAll("td[data-fact]").map((cell) => cell.outerHTML);

test("the Trust page shows the release and the numbers of every project", async () => {
  const document = trustPage();
  const fetch = fetcher({ [FEED]: FIXTURE });

  await projects.start(document, fetch, NOW);

  assert.deepEqual(fetch.asked, [FEED]);
  assert.deepEqual(row(document, "release"), ["v1.17.0", "v1.0.0", "v1.1.0", "v1.5.0", "v0.13.3"]);
  assert.deepEqual(row(document, "coverage"), ["100%", "100%", "100%", "100%", "100%"]);
  // The blueprint has no mutation score: its cell keeps the dash of the build.
  assert.deepEqual(row(document, "mutation"), ["90%", "95%", "96%", "82%", "—"]);
  assert.deepEqual(row(document, "scorecard"), ["7.8", "7.3", "7.4", "7.8", "7.8"]);
  // The value alone, without the text of a card: a link for the release and the
  // Scorecard, text for a share.
  const [release] = cellOf(document, "Dennis-Otto/ha-autodarts", "release").children;
  assert.equal(release.tagName, "a");
  assert.equal(
    release.getAttribute("href"),
    "https://github.com/Dennis-Otto/ha-autodarts/releases/tag/v1.17.0",
  );
  const [scorecard] = cellOf(document, "Dennis-Otto/paperless-sync", "scorecard").children;
  assert.equal(
    scorecard.getAttribute("href"),
    "https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/paperless-sync",
  );
  assert.deepEqual(cellOf(document, "Dennis-Otto/ha-autodarts", "coverage").children, ["100%"]);
});

test("the German Trust page shows the numbers in German", async () => {
  const document = trustPage("de");

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.equal(row(document, "coverage")[0], `100${NBSP}%`);
  assert.equal(row(document, "scorecard")[1], "7,3");
});

test("a second run on the Trust page shows every value once", async () => {
  const document = trustPage();
  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);
  const first = cellsOf(document);

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.deepEqual(cellsOf(document), first);
});

test("without the data, every cell of the Trust page keeps what the build put into it", async () => {
  const document = trustPage();
  const built = cellsOf(document);
  const fetch = fetcher({});

  await projects.start(document, fetch, NOW);

  assert.deepEqual(fetch.asked, [FEED, HISTORY]);
  assert.deepEqual(cellsOf(document), built);
});

test("from history.json, the Trust page shows the numbers and keeps the releases", async () => {
  const document = trustPage();
  const answers = { [FEED]: new Error("offline"), [HISTORY]: HISTORY_DAYS };

  await projects.start(document, fetcher(answers), NOW);

  assert.deepEqual(cellOf(document, "Dennis-Otto/ha-autodarts", "coverage").children, ["100%"]);
  assert.equal(row(document, "mutation")[0], "90%");
  assert.deepEqual(row(document, "release"), REPOS.map(() => "GitHub"));
  assert.equal(row(document, "coverage")[1], "—");
});

test("a cell of a fact that the script doesn't know or of a broken repository stays", async () => {
  const data = structuredClone(FIXTURE);
  data.repos.push({ repo: "not a repository", release: "v1.0.0", scorecard: 5 });
  const document = trustPage(
    "en",
    ["Dennis-Otto/ha-autodarts", "not a repository", "Dennis-Otto/new-project"],
    ["release", "constructor", "scorecard"],
  );
  const built = cellsOf(document);

  await projects.start(document, fetcher({ [FEED]: data }), NOW);

  // Only the release and the Scorecard of the project that the data knows change.
  assert.deepEqual(
    cellsOf(document).map((cell, index) => cell === built[index]),
    [false, true, true, true, true, true, false, true, true],
  );
});

test("the age of a release is told in days, weeks, months and years", () => {
  const day = (text) => Date.parse(`${text}T00:00:00Z`);
  const ages = Object.fromEntries(
    ["2026-10-21", "2026-10-19", "2026-10-18", "2026-10-13", "2026-10-05", "2026-09-10"]
      .concat(["2026-07-01", "2025-10-19", "2023-01-01"])
      .map((text) => [text, projects.ago(day(text), NOW, "en")]),
  );

  assert.deepEqual(ages, {
    // A clock that is behind the data counts as today.
    "2026-10-21": "today",
    "2026-10-19": "today",
    "2026-10-18": "yesterday",
    "2026-10-13": "6 days ago",
    "2026-10-05": "2 weeks ago",
    "2026-09-10": "last month",
    "2026-07-01": "3 months ago",
    "2025-10-19": "last year",
    "2023-01-01": "3 years ago",
  });
  assert.equal(projects.ago(day("2026-10-05"), NOW, "de"), "vor 2 Wochen");
});

test("a time to answer is told in minutes, hours or days", () => {
  assert.equal(projects.duration(0, "en"), "1 minute");
  assert.equal(projects.duration(0.129, "en"), "8 minutes");
  assert.equal(projects.duration(1.5, "en"), "2 hours");
  assert.equal(projects.duration(47, "de"), "47 Stunden");
  assert.equal(projects.duration(50, "de"), "2 Tage");
});

test("a share never reads as more than it is, and a score keeps its decimal", () => {
  assert.equal(projects.share(99.6, "en"), "99%");
  assert.equal(projects.share(100, "de"), `100${NBSP}%`);
  assert.equal(projects.score(8, "en"), "8.0");
  assert.equal(projects.score(7.25, "de"), "7,3");
});

test("a $ in a text stays as it is", () => {
  const facts = projects.facts(
    "Dennis-Otto/tool",
    { release: "v1.0.0", health: { coverage: 50 } },
    { locale: "en", coverage: "$& {} $1" },
    NOW,
  );

  assert.deepEqual(
    facts.map((fact) => fact.text),
    ["v1.0.0", "$& 50% $1"],
  );
});

test("the newest releases take only projects on the cards with a release", () => {
  const cards = new Map([
    ["a/one", { order: 0 }],
    ["a/two", { order: 1 }],
  ]);
  const entries = [
    { repo: "a/two", release: "v2", released: "2026-10-19" },
    { repo: "a/one", release: "v1", released: "2026-10-19" },
    { repo: "a/one", release: "", released: "2026-10-20" },
    { repo: "a/other", release: "v3", released: "2026-10-20" },
    { repo: "a/two", release: "v4", released: null },
  ];

  assert.deepEqual(
    projects.newest(entries, cards, 5).map((entry) => entry.release),
    ["v1", "v2"],
  );
  assert.equal(projects.newest(entries, cards, 1).length, 1);
});

// The script as the browser runs it: without module, with window and document.
const SOURCE = readFileSync(new URL("../docs/javascripts/projects.js", import.meta.url), "utf8");

const browser = (document, globals = {}) => {
  const fetch = fetcher({ [FEED]: FIXTURE });
  const context = vm.createContext({ AbortSignal, document, fetch, ...globals });
  context.window = context;
  vm.runInContext(SOURCE, context);
  return fetch;
};

const settled = () => new Promise((resolve) => setTimeout(resolve, 10));

test("in the browser, the script follows every page of Material's document$", async () => {
  const pages = [];
  const document = homePage();
  const fetch = browser(document, { document$: { subscribe: (run) => pages.push(run) } });

  assert.equal(pages.length, 1);
  assert.deepEqual(fetch.asked, []);
  await pages[0]();
  assert.deepEqual(fetch.asked, [FEED]);
  assert.equal(items(factsOf(document, "Dennis-Otto/ha-autodarts"))[0], "v1.17.0");
});

test("in the browser without document$, the script waits for the document", async () => {
  const listeners = [];
  const document = Object.assign(homePage(), {
    readyState: "loading",
    addEventListener: (type, run) => listeners.push([type, run]),
  });
  const fetch = browser(document);

  assert.deepEqual(
    listeners.map(([type]) => type),
    ["DOMContentLoaded"],
  );
  assert.deepEqual(fetch.asked, []);
  await listeners[0][1]();
  assert.equal(items(factsOf(document, "Dennis-Otto/ha-autodarts"))[0], "v1.17.0");
});

test("in the browser, the script fills a document that is ready at once", async () => {
  const document = Object.assign(homePage(), { readyState: "complete" });
  const fetch = browser(document);
  await settled();

  assert.deepEqual(fetch.asked, [FEED]);
  assert.equal(document.querySelectorAll(".project-news__list").length, 1);
});
