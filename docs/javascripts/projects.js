// The live facts of the home pages and of the Trust page: the latest release and the
// quality numbers on the card of every project with a repository, the newest
// releases under What's new, and the same release and numbers in the table of the
// guarantees of the Trust page. The dashboard of the blueprint publishes its data at
// the same address every few hours, and this script reads it from there as the page
// loads: no token, no request to another origin and no limit of an API, and the
// numbers stay current without a new build of the website. Without the data, as in a
// preview of the website, or without the script, every card and every cell keeps
// what the build put into it.
//
// .github/mkdocs_project.py writes the parts that it fills, with the texts of
// [facts] in projects.toml in the language of the page, where {} stands for a value:
//
//   <div class="projects" data-facts="/repo-blueprint/dashboard/repos.json"
//        data-history="/repo-blueprint/dashboard/history.json" data-locale="en"
//        data-label="Release and quality" data-released="released {}" …>
//     … <div class="project-facts" data-repo="Dennis-Otto/homedarts-for-autodarts"
//            data-name="HomeDarts for Autodarts">the facts of the build</div> …
//   </div>
//   <div class="project-news" data-count="5"></div>
//
// and on the Trust page, with a cell for each value of release, coverage, mutation
// and scorecard of every project, which takes the value alone:
//
//   <div class="trust" data-facts="…" data-history="…" data-locale="en">
//     … <td data-repo="Dennis-Otto/homedarts-for-autodarts" data-fact="coverage">—</td> …
//   </div>
//
// overrides/facts.html loads it on the pages with live facts alone.
// tests/projects.test.mjs runs it with Node, on a document of its own:
//   node --test tests/*.test.mjs
(() => {
  "use strict";

  const DAY = 86_400_000;
  // The shape of repos.json that the script knows. The dashboard counts it up when
  // it takes a field away or changes one, and the script then takes the numbers of
  // history.json alone, until it learns the new shape.
  const SCHEMA = 1;
  // How long a request may take, in milliseconds, before the cards stay as they are.
  const TIMEOUT = 10_000;
  const DATE = /^\d{4}-\d{2}-\d{2}$/;
  const REPO = /^[\w.-]+\/[\w.-]+$/;
  // The links of the facts lead to GitHub alone, whatever the data says.
  const GITHUB = "https://github.com/";
  const SCORECARD = "https://scorecard.dev/viewer/?uri=github.com/";

  const within = (value, low, high) =>
    typeof value === "number" && Number.isFinite(value) && value >= low && value <= high;

  // A day of the data, such as 2026-10-19, as the time of its start in UTC, or NaN.
  const day = (text) =>
    typeof text === "string" && DATE.test(text) ? Date.parse(`${text}T00:00:00Z`) : NaN;

  const github = (url) => (typeof url === "string" && url.startsWith(GITHUB) ? url : null);

  // text with value in place of its {}; a function, so that a $ of the value stays.
  const fill = (text, value) => String(text ?? "{}").replace("{}", () => value);

  // A share of 100 in the language of the page, such as 100% or 100 %, rounded down,
  // so that 99.6 % of the code never reads as all of it.
  const share = (value, locale) =>
    new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(
      Math.floor(value) / 100,
    );

  // A score of 10 with one decimal, such as 7.8 or 7,8.
  const score = (value, locale) =>
    new Intl.NumberFormat(locale, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(value);

  // A number of hours in words: minutes below an hour, days from two days on.
  const duration = (hours, locale) => {
    let value = Math.round(hours / 24);
    let unit = "day";
    if (hours < 1) {
      [value, unit] = [Math.max(1, Math.round(hours * 60)), "minute"];
    } else if (hours < 48) {
      [value, unit] = [Math.round(hours), "hour"];
    }
    return new Intl.NumberFormat(locale, { style: "unit", unit, unitDisplay: "long" }).format(
      value,
    );
  };

  // How long ago a day was, from the day of now in UTC, as the data counts its days:
  // "today", "3 days ago", "last week" or "vor 2 Monaten". A day after today, from a
  // clock that is behind, counts as today.
  const ago = (start, now, locale) => {
    const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    const days = Math.max(0, Math.round((today - start) / DAY));
    let value = Math.floor(days / 365);
    let unit = "year";
    if (days < 7) {
      [value, unit] = [days, "day"];
    } else if (days < 30) {
      [value, unit] = [Math.floor(days / 7), "week"];
    } else if (days < 365) {
      [value, unit] = [Math.floor(days / 30), "month"];
    }
    return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
      value === 0 ? 0 : -value,
      unit,
    );
  };

  // The day itself, such as "19 October 2026", for the title of its time.
  const longDate = (start, locale) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "UTC" }).format(start);

  // The values of a repository, from its entry in repos.json, or in history.json,
  // which has its health alone, by the name of each fact, in the order of a card:
  // each a text in the language of the page, with the address that it links or the
  // day that it names, if any. A fact without its value is left out.
  const values = (repo, entry, locale, now) => {
    const found = new Map();
    if (typeof entry.release === "string" && entry.release) {
      found.set("release", { text: entry.release, href: github(entry.release_url) });
    }
    const released = day(entry.released);
    if (!Number.isNaN(released)) {
      found.set("released", {
        text: ago(released, now, locale),
        date: entry.released,
        title: longDate(released, locale),
      });
    }
    const health = entry.health && typeof entry.health === "object" ? entry.health : {};
    if (within(health.coverage, 0, 100)) {
      found.set("coverage", { text: share(health.coverage, locale) });
    }
    if (within(health.mutation, 0, 100)) {
      found.set("mutation", { text: share(health.mutation, locale) });
    }
    if (within(entry.scorecard, 0, 10)) {
      found.set("scorecard", {
        text: score(entry.scorecard, locale),
        href: `${SCORECARD}${repo}`,
      });
    }
    if (within(health.answer_hours, 0, Infinity)) {
      found.set("answer", { text: duration(health.answer_hours, locale) });
    }
    return found;
  };

  // The facts of a repository on its card: its values, each but the release in the
  // text of the page for it, such as "100% test coverage".
  const facts = (repo, entry, labels, now) => {
    const texts = {
      released: labels.released,
      coverage: labels.coverage,
      mutation: labels.mutation,
      scorecard: labels.scorecard,
      answer: labels.answer,
    };
    return [...values(repo, entry, labels.locale, now)].map(([name, value]) =>
      name in texts ? { ...value, text: fill(texts[name], value.text) } : value,
    );
  };

  // The latest releases of the projects on the cards, the newest first, and of a day
  // in the order of the cards: count of them at most, one for each project.
  const newest = (entries, cards, count) =>
    entries
      .filter(
        (entry) =>
          cards.has(entry.repo) &&
          typeof entry.release === "string" &&
          entry.release &&
          !Number.isNaN(day(entry.released)),
      )
      .sort(
        (a, b) =>
          day(b.released) - day(a.released) || cards.get(a.repo).order - cards.get(b.repo).order,
      )
      .slice(0, count);

  const element = (document, tag, text, attributes = {}) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value !== null && value !== undefined) {
        node.setAttribute(name, value);
      }
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  };

  // A fact as what its place shows: a link, the time of a release, or text.
  const content = (document, fact) => {
    if (fact.href) {
      return element(document, "a", fact.text, { href: fact.href });
    }
    if (fact.date) {
      return element(document, "time", fact.text, { datetime: fact.date, title: fact.title });
    }
    return fact.text;
  };

  // A fact as an item of the list of its card.
  const item = (document, fact) => {
    const node = document.createElement("li");
    node.append(content(document, fact));
    return node;
  };

  // The cells of the table of the Trust page, each with the value of its fact for its
  // repository alone, such as 100% or 7.8. A cell whose value the data lacks keeps
  // what it holds: what the build put into it, or the value of an earlier run.
  const cells = (document, data, locale, now) => {
    for (const cell of document.querySelectorAll("td[data-fact][data-repo]")) {
      const { fact, repo } = cell.dataset;
      const entry = data.repos.get(repo);
      const value = entry && REPO.test(repo) ? values(repo, entry, locale, now).get(fact) : null;
      if (value) {
        cell.replaceChildren(content(document, value));
      }
    }
  };

  // Fetch the JSON at url, or fail.
  const get = async (fetch, url) => {
    const response = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT) });
    if (!response.ok) {
      throw new Error(`${url} answered ${response.status}`);
    }
    return response.json();
  };

  // The data of the repositories: the entries of repos.json, with each by its name,
  // or else the health of the latest day of history.json by the name of each
  // repository, or nothing, when neither can be read.
  const load = async (fetch, place) => {
    try {
      const data = await get(fetch, place.dataset.facts);
      if (data && data.schema === SCHEMA && Array.isArray(data.repos)) {
        const entries = data.repos.filter(
          (entry) => entry && typeof entry === "object" && typeof entry.repo === "string",
        );
        return { entries, repos: new Map(entries.map((entry) => [entry.repo, entry])) };
      }
    } catch {
      // The numbers of history.json, as below.
    }
    try {
      const days = await get(fetch, place.dataset.history);
      const latest = (Array.isArray(days) ? days : [])
        .filter((entry) => entry && entry.repos && typeof entry.repos === "object")
        .reduce(
          (last, entry) => (!last || String(entry.date) > String(last.date) ? entry : last),
          null,
        );
      if (latest) {
        const repos = Object.entries(latest.repos).map(([repo, health]) => [repo, { health }]);
        return { entries: [], repos: new Map(repos) };
      }
    } catch {
      // No data: the cards and the cells stay as they are.
    }
    return { entries: [], repos: new Map() };
  };

  // Fill the cards, the cells of the Trust page and What's new of document from the
  // data, as of now.
  const render = (document, place, data, now) => {
    const labels = place.dataset;
    const cards = new Map();
    for (const card of document.querySelectorAll(".project-facts[data-repo]")) {
      const repo = card.dataset.repo;
      cards.set(repo, { name: card.dataset.name || repo, order: cards.size });
      // A second run, as after a page of Material's instant loading, starts anew.
      for (const added of card.querySelectorAll("[data-live]")) {
        added.remove();
      }
      const entry = data.repos.get(repo);
      const found = entry && REPO.test(repo) ? facts(repo, entry, labels, now) : [];
      if (found.length === 0) {
        continue;
      }
      // In front of the facts of the build, such as the level of the OpenSSF Best
      // Practices, in their list, or in a list of their own.
      let list = card.querySelector(".project-facts__list");
      if (!list) {
        list = element(document, "ul", undefined, {
          class: "project-facts__list",
          "aria-label": labels.label,
          "data-live": "",
        });
        card.prepend(list);
      }
      list.prepend(
        ...found.map((fact) => {
          const node = item(document, fact);
          node.setAttribute("data-live", "");
          return node;
        }),
      );
    }
    cells(document, data, labels.locale, now);
    const news = document.querySelector(".project-news");
    if (!news) {
      return;
    }
    news.replaceChildren();
    const releases = newest(data.entries, cards, Number.parseInt(news.dataset.count, 10) || 5);
    if (releases.length === 0) {
      return;
    }
    const list = element(document, "ul", undefined, { class: "project-news__list" });
    for (const entry of releases) {
      const released = day(entry.released);
      const node = item(document, {
        text: `${cards.get(entry.repo).name} ${entry.release}`,
        href: github(entry.release_url),
      });
      const time = element(document, "time", ago(released, now, labels.locale), {
        datetime: entry.released,
        title: longDate(released, labels.locale),
      });
      node.append(" ", time);
      list.append(node);
    }
    news.append(list);
  };

  // Fill the page in document with the data that fetch gets, as of now: a home page,
  // whose cards tell where the data is, or the Trust page, whose table does.
  const start = async (document, fetch, now) => {
    const place = document.querySelector("[data-facts]");
    if (!place) {
      return;
    }
    render(document, place, await load(fetch, place), now);
  };

  const api = { ago, duration, facts, newest, score, share, start };
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    // With Material's document$, which follows each page that its instant loading
    // brings, or once the document is ready.
    const run = () => start(document, (...args) => window.fetch(...args), new Date());
    if (window.document$) {
      window.document$.subscribe(run);
    } else if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", run);
    } else {
      run();
    }
  }
})();
