// Tests of the live facts of the home pages, the Trust page and the Releases page,
// docs/javascripts/projects.js, with Node
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
    github: "Release on GitHub",
  },
  de: {
    label: "Release und Qualität",
    released: "veröffentlicht {}",
    coverage: "{} Testabdeckung",
    mutation: "{} Mutations-Score",
    scorecard: "Scorecard {}",
    answer: "erste Antwort eines Menschen nach {}",
    github: "Release auf GitHub",
  },
};
const CARDS = {
  en: [
    ["Dennis-Otto/homedarts-for-autodarts", "HomeDarts for Autodarts"],
    ["Dennis-Otto/player-switch-for-autodarts", "Player Switch for Autodarts"],
    ["Dennis-Otto/paperless-sync", "Paperless Sync"],
    ["Dennis-Otto/paperless-unified-search", "Paperless Unified Search"],
    ["Dennis-Otto/issue-assistant", "Issue assistant"],
    ["Dennis-Otto/repo-blueprint", "Repo Blueprint"],
  ],
};
// A German name of its own, which no card of projects.toml has, shows that the script
// takes the name of the card in the language of the page.
CARDS.de = CARDS.en.map(([repo, name]) => [
  repo,
  name.replace("HomeDarts for", "HomeDarts für"),
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

  removeAttribute(name) {
    this.attributes.delete(name);
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

// The projects without a level of the OpenSSF Best Practices on the day of the build.
const WITHOUT_LEVEL = new Set(["Dennis-Otto/player-switch-for-autodarts", "Dennis-Otto/repo-blueprint"]);

// A home page in the language, as the hook writes it, with the cards of these repos
// and What's new as news; the build read the level of every project but those of
// WITHOUT_LEVEL.
const homePage = (
  language = "en",
  cards = CARDS[language],
  news = new Element("div", { class: "project-news", "data-count": "5" }),
) => {
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
            WITHOUT_LEVEL.has(repo) ? [] : [built(language)],
          ),
        ]),
    ),
  );
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

  const card = factsOf(document, "Dennis-Otto/homedarts-for-autodarts");
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
    "https://github.com/Dennis-Otto/homedarts-for-autodarts/releases/tag/v1.17.0",
  );
  assert.equal(date.tagName, "time");
  assert.equal(date.getAttribute("datetime"), "2026-10-19");
  assert.equal(date.getAttribute("title"), "October 19, 2026");
  assert.equal(
    scorecard.getAttribute("href"),
    "https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/homedarts-for-autodarts",
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
  const [, homedarts, issues, sync, search] = data.repos;
  Object.assign(homedarts, { release: null, released: null, health: null });
  Object.assign(issues, { released: "2026-13-45", scorecard: 11, release_url: null });
  issues.health = { coverage: "100", mutation: -1, answer_hours: Number.NaN };
  Object.assign(sync, { release_url: "javascript:alert(1)", released: "yesterday" });
  delete search.health;
  delete search.scorecard;
  const { document } = await show("en", { [FEED]: data });

  assert.deepEqual(items(factsOf(document, "Dennis-Otto/homedarts-for-autodarts")), [
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
    repos: [{ repo: "Dennis-Otto/homedarts-for-autodarts" }, { repo: "Dennis-Otto/repo-blueprint" }],
  };
  const { document } = await show("en", { [FEED]: data });

  assert.deepEqual(items(factsOf(document, "Dennis-Otto/homedarts-for-autodarts")), [LEVEL.en]);
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
      [[LEVEL.en], [], [LEVEL.en], [LEVEL.en], [LEVEL.en], []],
    );
    assert.deepEqual(document.querySelector(".project-news").children, []);
  });
}

const HISTORY_DAYS = [
  {
    date: "2026-10-18",
    repos: { "Dennis-Otto/homedarts-for-autodarts": { coverage: 99, mutation: 80, answer_hours: 2 } },
  },
  {
    date: "2026-10-19",
    repos: {
      "Dennis-Otto/homedarts-for-autodarts": { coverage: 100, mutation: 90.5, answer_hours: 50 },
    },
  },
  { date: "2026-10-17", repos: { "Dennis-Otto/homedarts-for-autodarts": { coverage: 1 } } },
  null,
];

for (const [name, feed] of [
  ["repos.json can't be read", new Error("offline")],
  ["repos.json has a newer shape", { ...FIXTURE, schema: 2 }],
]) {
  test(`when ${name}, the cards show the numbers of the latest day of history.json`, async () => {
    const { document, fetch } = await show("en", { [FEED]: feed, [HISTORY]: HISTORY_DAYS });

    assert.deepEqual(fetch.asked, [FEED, HISTORY]);
    assert.deepEqual(items(factsOf(document, "Dennis-Otto/homedarts-for-autodarts")), [
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
  // website itself, whose repository has no card.
  assert.deepEqual(
    list.children.map((item) => item.textContent),
    [
      "HomeDarts for Autodarts v1.17.0 today",
      "Repo Blueprint v0.13.3 today",
      "Paperless Sync v1.0.0 yesterday",
      "Paperless Unified Search v1.1.0 2 days ago",
      "Player Switch for Autodarts v0.2.0 4 days ago",
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
    ["HomeDarts für Autodarts v1.17.0 heute", "Repo Blueprint v0.13.3 heute"],
  );
});

// What's new as the build writes it from the releases that it read: one of every
// project but Player Switch, whose releases it couldn't read, each with the headline
// of its notes. The data of the fixture has a newer release of HomeDarts, the same
// ones of three projects, and an older one of the issue assistant.
const BUILT = [
  ["Dennis-Otto/repo-blueprint", "v0.13.3", "2026-10-19", "Checks that explain themselves"],
  ["Dennis-Otto/paperless-sync", "v1.0.0", "2026-10-18", "One account for the archive"],
  ["Dennis-Otto/issue-assistant", "v1.6.0", "2026-10-18", "Slash commands"],
  ["Dennis-Otto/paperless-unified-search", "v1.1.0", "2026-10-17", "Results in the viewer"],
  ["Dennis-Otto/homedarts-for-autodarts", "v1.16.0", "2026-10-16", "Cricket on the board"],
];
const builtNews = (language = "en", releases = BUILT) => {
  const names = new Map(CARDS[language]);
  return new Element("div", { class: "project-news", "data-count": "6" }, [
    new Element(
      "ul",
      { class: "project-news__list" },
      releases.map(
        ([repo, release, released, headline]) =>
          new Element("li", { "data-repo": repo, "data-release": release, "data-released": released }, [
            new Element("a", { href: `releases.html#${release}` }, [`${names.get(repo)} ${release}`]),
            " ",
            new Element("time", { datetime: released, "data-ago": "" }, [released]),
            new Element("span", { class: "project-news__headline", lang: "en" }, [headline]),
          ]),
      ),
    ),
  ]);
};
// Each release of What's new as its text, and whether it is hidden.
const news = (document) =>
  document
    .querySelector(".project-news__list")
    .children.map((item) => [item.textContent, item.getAttribute("hidden") !== null]);

test("What's new keeps the releases of the build, with a newer one of the data in place", async () => {
  const document = homePage("en", CARDS.en, builtNews());

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  // Every project, the newest first: the newer HomeDarts of the data in place of the
  // one of the build, which stays hidden, and Player Switch from the data alone.
  assert.deepEqual(news(document), [
    ["HomeDarts for Autodarts v1.17.0 today", false],
    ["Repo Blueprint v0.13.3 todayChecks that explain themselves", false],
    ["Paperless Sync v1.0.0 yesterdayOne account for the archive", false],
    ["Issue assistant v1.6.0 yesterdaySlash commands", false],
    ["Paperless Unified Search v1.1.0 2 days agoResults in the viewer", false],
    ["Player Switch for Autodarts v0.2.0 4 days ago", false],
    ["HomeDarts for Autodarts v1.16.0 3 days agoCricket on the board", true],
  ]);
  const [first, second] = document.querySelector(".project-news__list").children;
  // A release of the data links its notes on GitHub, one of the build the Releases
  // page.
  assert.equal(first.children[0].getAttribute("href"), FIXTURE.repos[1].release_url);
  assert.equal(second.children[0].getAttribute("href"), "releases.html#v0.13.3");
  assert.equal(second.children[2].getAttribute("title"), "October 19, 2026");
});

test("What's new keeps the releases of the build without the data, as of now", async () => {
  const document = homePage("de", CARDS.de, builtNews("de"));

  await projects.start(document, fetcher({}), NOW);

  const days = ["heute", "gestern", "gestern", "vorgestern", "vor 3 Tagen"];
  assert.deepEqual(
    news(document).map(([text]) => text),
    BUILT.map(
      ([repo, release, , headline], index) =>
        `${new Map(CARDS.de).get(repo)} ${release} ${days[index]}${headline}`,
    ),
  );
});

test("a second run of What's new starts from the releases of the build", async () => {
  const document = homePage("en", CARDS.en, builtNews());
  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);
  const first = news(document);

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);
  assert.deepEqual(news(document), first);

  await projects.start(document, fetcher({}), NOW);
  assert.deepEqual(
    news(document).map(([text, hidden]) => [text.split(" v")[0], hidden]),
    BUILT.map(([repo]) => [new Map(CARDS.en).get(repo), false]),
  );
  assert.equal(document.querySelector("[data-live]"), null);
});

test("What's new shows as many releases as the build names, those it leaves out hidden", async () => {
  const document = homePage("en", CARDS.en, builtNews());
  document.querySelector(".project-news").setAttribute("data-count", "2");

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.deepEqual(
    news(document).map(([text, hidden]) => `${text.split(" v")[0]}${hidden ? " (hidden)" : ""}`),
    [
      "HomeDarts for Autodarts",
      "Repo Blueprint",
      "Paperless Sync (hidden)",
      "Issue assistant (hidden)",
      "Paperless Unified Search (hidden)",
      "HomeDarts for Autodarts (hidden)",
    ],
  );
});

test("a second run, as after instant loading, shows every fact once", async () => {
  const { document } = await show();
  const first = document.querySelectorAll(".project-facts").map(items);

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.deepEqual(document.querySelectorAll(".project-facts").map(items), first);
  assert.equal(document.querySelectorAll(".project-facts__list").length, 6);
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
  assert.deepEqual(row(document, "release"), [
    "v1.17.0",
    "v0.2.0",
    "v1.0.0",
    "v1.1.0",
    "v1.5.0",
    "v0.13.3",
  ]);
  // Player Switch has no numbers of its tests yet, and the blueprint no mutation
  // score: their cells keep the dash of the build.
  assert.deepEqual(row(document, "coverage"), ["100%", "—", "100%", "100%", "100%", "100%"]);
  assert.deepEqual(row(document, "mutation"), ["90%", "—", "95%", "96%", "82%", "—"]);
  assert.deepEqual(row(document, "scorecard"), ["7.8", "7.2", "7.3", "7.4", "7.8", "7.8"]);
  // The value alone, without the text of a card: a link for the release and the
  // Scorecard, text for a share.
  const [release] = cellOf(document, "Dennis-Otto/homedarts-for-autodarts", "release").children;
  assert.equal(release.tagName, "a");
  assert.equal(
    release.getAttribute("href"),
    "https://github.com/Dennis-Otto/homedarts-for-autodarts/releases/tag/v1.17.0",
  );
  const [scorecard] = cellOf(document, "Dennis-Otto/paperless-sync", "scorecard").children;
  assert.equal(
    scorecard.getAttribute("href"),
    "https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/paperless-sync",
  );
  assert.deepEqual(cellOf(document, "Dennis-Otto/homedarts-for-autodarts", "coverage").children, ["100%"]);
});

test("the German Trust page shows the numbers in German", async () => {
  const document = trustPage("de");

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.equal(row(document, "coverage")[0], `100${NBSP}%`);
  assert.equal(row(document, "scorecard")[2], "7,3");
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

  assert.deepEqual(cellOf(document, "Dennis-Otto/homedarts-for-autodarts", "coverage").children, ["100%"]);
  assert.equal(row(document, "mutation")[0], "90%");
  assert.deepEqual(row(document, "release"), REPOS.map(() => "GitHub"));
  assert.equal(row(document, "coverage")[1], "—");
});

test("a cell of a fact that the script doesn't know or of a broken repository stays", async () => {
  const data = structuredClone(FIXTURE);
  data.repos.push({ repo: "not a repository", release: "v1.0.0", scorecard: 5 });
  const document = trustPage(
    "en",
    ["Dennis-Otto/homedarts-for-autodarts", "not a repository", "Dennis-Otto/new-project"],
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

// The Releases page in the language, as the hook writes it: the list of the projects,
// which tells where the data is, the place of a newer release of every project of
// places, with the releases of the build and the day of the newest, and the day of
// a release of the build, beside one that is no day.
const releasesPage = (language = "en", places = PLACES) =>
  new Document(
    new Element("nav", {
      class: "release-filter",
      "data-facts": FEED,
      "data-history": HISTORY,
      "data-locale": language,
      "data-github": TEXTS[language].github,
    }),
    ...places.map(
      ([repo, releases, released]) =>
        new Element("div", {
          class: "release-newer",
          "data-repo": repo,
          "data-releases": releases,
          "data-released": released,
        }),
    ),
    new Element("p", { class: "release-meta" }, [
      new Element("time", { datetime: "2026-10-12", "data-ago": "" }, ["2026-10-12"]),
      new Element("time", { datetime: "soon", "data-ago": "" }, ["soon"]),
    ]),
  );
// HomeDarts before its latest release, the blueprint with it, the issue assistant
// with a newer one than the data, Player Switch without the releases of the build,
// a project whose release in the data leads elsewhere, and a broken repository.
const PLACES = [
  ["Dennis-Otto/homedarts-for-autodarts", "v1.16.0 v1.15.0", "2026-10-16"],
  ["Dennis-Otto/repo-blueprint", "v0.13.3 v0.13.2", "2026-10-19"],
  ["Dennis-Otto/issue-assistant", "v1.6.0", "2026-10-18"],
  ["Dennis-Otto/player-switch-for-autodarts", "", ""],
  ["Dennis-Otto/paperless-sync", "v0.9.0", "2026-10-01"],
  ["not a repository", "", ""],
];
const ELSEWHERE = structuredClone(FIXTURE);
ELSEWHERE.repos[3].release_url = "https://example.org/paperless-sync/v1.0.0";
ELSEWHERE.repos.push({ repo: "not a repository", release: "v1.0.0", released: "2026-10-19" });
const newerOf = (document) =>
  document.querySelectorAll(".release-newer").map((place) => place.textContent);

test("the Releases page shows a release that came out after the build", async () => {
  const document = releasesPage();

  await projects.start(document, fetcher({ [FEED]: ELSEWHERE }), NOW);

  assert.deepEqual(newerOf(document), [
    "v1.17.0 today · Release on GitHub",
    "",
    "",
    "v0.2.0 4 days ago · Release on GitHub",
    "",
    "",
  ]);
  const [release, time, link] = document
    .querySelector(".release-meta")
    .children.filter((child) => child instanceof Element);
  assert.equal(release.tagName, "strong");
  assert.equal(time.getAttribute("title"), "October 19, 2026");
  assert.equal(link.getAttribute("href"), FIXTURE.repos[1].release_url);
  // The days of the build as the time since, but one that is no day.
  const days = document.querySelectorAll("time[data-ago]").slice(-2);
  assert.deepEqual(
    days.map((day) => [day.textContent, day.getAttribute("title")]),
    [
      ["last week", "October 12, 2026"],
      ["soon", null],
    ],
  );
});

test("the German Releases page shows a newer release in German, once", async () => {
  const document = releasesPage("de");
  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  assert.equal(newerOf(document)[0], "v1.17.0 heute · Release auf GitHub");
  assert.equal(document.querySelectorAll(".release-meta").length, 4);
});

test("without the data, the Releases page shows the releases of the build alone", async () => {
  const document = releasesPage();
  await projects.start(document, fetcher({ [FEED]: FIXTURE }), NOW);

  await projects.start(
    document,
    fetcher({ [FEED]: new Error("offline"), [HISTORY]: HISTORY_DAYS }),
    NOW,
  );

  assert.deepEqual(newerOf(document), PLACES.map(() => ""));
  assert.equal(document.querySelector("time[data-ago]").textContent, "last week");
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

test("a release of the data takes the place of one of the build when it is no older", () => {
  const cards = new Map([
    ["a/one", { order: 0 }],
    ["a/two", { order: 1 }],
  ]);
  const built = new Map([
    ["a/one", { repo: "a/one", release: "v1", released: "2026-10-18" }],
    ["a/two", { repo: "a/two", release: "v2", released: "2026-10-18" }],
    ["a/three", { repo: "a/three", release: "v3", released: "2026-10-18" }],
  ]);
  const entries = [
    // The same day, another release: the data is newer.
    { repo: "a/one", release: "v1.1", released: "2026-10-18" },
    // An older one, as from data that is behind the build.
    { repo: "a/two", release: "v1.9", released: "2026-10-17" },
    // One without a release of the build, whose day the build can't read.
    { repo: "a/three", release: "v3.1", released: "2026-10-19" },
  ];

  // a/three has no card, so the data can't replace its release, which keeps its
  // place after those of the projects on the cards.
  assert.deepEqual(
    projects.newest(entries, cards, 5, built).map((entry) => entry.release),
    ["v1.1", "v2", "v3"],
  );
});

test("a release of the data that the build read never takes the place of a newer one", () => {
  const cards = new Map([
    ["a/one", { order: 0 }],
    ["a/two", { order: 1 }],
  ]);
  const built = new Map([
    // The build read v1.0.6 and v1.0.5, both of the same day.
    ["a/one", { repo: "a/one", release: "v1.0.6", released: "2026-10-23", releases: ["v1.0.6", "v1.0.5"] }],
    ["a/two", { repo: "a/two", release: "v2.0.0", released: "2026-10-23", releases: ["v2.0.0"] }],
  ]);
  const entries = [
    // Data that is behind the build, with an older release of the same day.
    { repo: "a/one", release: "v1.0.5", released: "2026-10-23" },
    // A release of the same day that the build doesn't know: the data is newer.
    { repo: "a/two", release: "v2.0.1", released: "2026-10-23" },
  ];

  assert.deepEqual(
    projects.newest(entries, cards, 5, built).map((entry) => entry.release),
    ["v1.0.6", "v2.0.1"],
  );
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
  assert.equal(items(factsOf(document, "Dennis-Otto/homedarts-for-autodarts"))[0], "v1.17.0");
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
  assert.equal(items(factsOf(document, "Dennis-Otto/homedarts-for-autodarts"))[0], "v1.17.0");
});

test("in the browser, the script fills a document that is ready at once", async () => {
  const document = Object.assign(homePage(), { readyState: "complete" });
  const fetch = browser(document);
  await settled();

  assert.deepEqual(fetch.asked, [FEED]);
  assert.equal(document.querySelectorAll(".project-news__list").length, 1);
});
