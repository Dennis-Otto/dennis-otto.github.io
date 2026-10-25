// The live facts of the home pages, of the Trust page and of the Releases page: the
// latest release and the quality numbers on the card of every project with a
// repository, a release newer than the build under What's new and on the Releases
// page, and the same release and numbers in the table of the projects of the Trust
// page. The dashboard of the blueprint publishes its data at the same address every
// few hours, and this script reads it from there as the page loads: no token, no
// request to another origin and no limit of an API, and the numbers stay current
// without a new build of the website. It also tells the day of every release as the
// time since, such as "3 days ago". Without the data, as in a preview of the website,
// or without the script, every card and every cell keeps what the build put into it.
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
//   <div class="project-news" data-count="6"><ul class="project-news__list">
//     <li data-repo="Dennis-Otto/homedarts-for-autodarts" data-release="v2.0.1"
//         data-released="2026-10-23"><a href="releases.html#…">HomeDarts for
//       Autodarts v2.0.1</a> <time datetime="2026-10-23" data-ago>2026-10-23</time>
//       <span class="project-news__headline">the headline of its notes</span></li> …
//   </ul></div>
//
// on the Trust page, with a row for every project in the table of the numbers and a
// cell for each value of release, coverage, mutation and scorecard, which takes the
// value alone and keeps its data-label, the label that a phone shows beside it:
//
//   <div class="trust" data-facts="…" data-history="…" data-locale="en">
//     … <td data-label="Test coverage" data-repo="Dennis-Otto/homedarts-for-autodarts"
//           data-fact="coverage">—</td> …
//   </div>
//
// and on the Releases page, with the place of a newer release below the heading of
// every project, which names the releases of the build and the day of the newest:
//
//   <nav class="release-filter" data-facts="…" data-locale="en"
//        data-github="Release on GitHub" …>the links to every project</nav>
//   … <div class="release-newer" data-repo="Dennis-Otto/homedarts-for-autodarts"
//          data-releases="v2.0.1 v2.0.0" data-released="2026-10-23"></div> …
//
// overrides/facts.html loads it on the pages with live facts alone.
// tests/projects.test.mjs runs it with Node, on a document of its own:
//   node --test tests/*.test.mjs
(() => {
  "use strict";

  const DAY = 86_400_000;
  // The shape of repos.json that the script knows. The dashboard counts it up when
  // it takes a field away or changes one, and the script then takes the numbers of
  // history.json alone, until it learns the new shape. .github/dashboard-fields.json
  // names it with every field that the script reads, for the watch of the catalog
  // bot, which checks the live data against both every day; tests/projects.test.mjs
  // keeps that file equal to what the script reads, so change both together.
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

  // The latest release of each project for What's new, the newest first, and of a
  // day in the order of the cards: the one of the build in built, by its repository,
  // or the latest of the data in its place for a project on the cards, when it is
  // another one, no older and none of the releases that the build read; count of
  // them at most.
  const newest = (entries, cards, count, built = new Map()) => {
    const latest = new Map(built);
    for (const entry of entries) {
      if (
        !cards.has(entry.repo) ||
        typeof entry.release !== "string" ||
        !entry.release ||
        Number.isNaN(day(entry.released))
      ) {
        continue;
      }
      const known = latest.get(entry.repo);
      if (
        !known ||
        (known.release !== entry.release &&
          !(known.releases ?? []).includes(entry.release) &&
          !(day(entry.released) < day(known.released)))
      ) {
        latest.set(entry.repo, entry);
      }
    }
    const order = (repo) => cards.get(repo)?.order ?? cards.size;
    return [...latest.values()]
      .sort((a, b) => day(b.released) - day(a.released) || order(a.repo) - order(b.repo))
      .slice(0, count);
  };

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

  // A day of the page, such as that of a release, with the day as its datetime and
  // as its text until the script tells it as the time since.
  const time = (document, date) => element(document, "time", date, { datetime: date, "data-ago": "" });

  // What's new: the release of every project that the build wrote, each with the
  // headline of its notes, or the newer one of the data in its place, linked to its
  // notes on GitHub, the newest first. A release of the build that a newer one
  // replaces stays hidden in the list, so that a second run starts from the build.
  const whatsNew = (document, data, cards) => {
    const news = document.querySelector(".project-news");
    if (!news) {
      return;
    }
    for (const added of news.querySelectorAll("[data-live]")) {
      added.remove();
    }
    let list = news.querySelector(".project-news__list");
    const built = new Map();
    for (const node of list ? list.querySelectorAll("li[data-repo]") : []) {
      node.removeAttribute("hidden");
      const { repo, release, released, releases = "" } = node.dataset;
      built.set(repo, { repo, release, released, releases: releases.split(" "), node });
    }
    const count = Number.parseInt(news.dataset.count, 10) || cards.size;
    const shown = newest(data.entries, cards, count, built);
    if (shown.length === 0) {
      return;
    }
    if (!list) {
      list = element(document, "ul", undefined, { class: "project-news__list", "data-live": "" });
      news.append(list);
    }
    const nodes = shown.map((entry) => {
      // A release of the build keeps its item. The script tells it from one of the
      // data by itself, never by a field, which the data could have too.
      if (built.get(entry.repo) === entry) {
        return entry.node;
      }
      const node = item(document, {
        text: `${cards.get(entry.repo).name} ${entry.release}`,
        href: github(entry.release_url),
      });
      node.setAttribute("data-live", "");
      node.append(" ", time(document, entry.released));
      return node;
    });
    for (const { node } of built.values()) {
      if (!nodes.includes(node)) {
        node.setAttribute("hidden", "");
        nodes.push(node);
      }
    }
    list.replaceChildren(...nodes);
  };

  // The Releases page: below the heading of each project, its latest release of the
  // data when the build didn't list it and it is no older than the newest that the
  // build did, with its day and a link to its notes on GitHub.
  const newer = (document, data, labels) => {
    for (const place of document.querySelectorAll(".release-newer[data-repo]")) {
      place.replaceChildren();
      const { repo, releases = "", released } = place.dataset;
      const entry = REPO.test(repo) ? data.repos.get(repo) : null;
      const href = entry ? github(entry.release_url) : null;
      if (
        !href ||
        typeof entry.release !== "string" ||
        !entry.release ||
        releases.split(" ").includes(entry.release) ||
        Number.isNaN(day(entry.released)) ||
        day(entry.released) < day(released)
      ) {
        continue;
      }
      const meta = element(document, "p", undefined, { class: "release-meta" });
      meta.append(
        element(document, "strong", entry.release),
        " ",
        time(document, entry.released),
        " · ",
        element(document, "a", labels.github || entry.release, { href }),
      );
      place.append(meta);
    }
  };

  // Every day of a release on the page as the time since, such as "3 days ago", in
  // the language of the page, with the day itself as its title.
  const times = (document, locale, now) => {
    for (const node of document.querySelectorAll("time[data-ago]")) {
      const start = day(node.getAttribute("datetime"));
      if (!Number.isNaN(start)) {
        node.textContent = ago(start, now, locale);
        node.setAttribute("title", longDate(start, locale));
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

  // Fill the cards, the cells of the Trust page, What's new and the newer releases of
  // the Releases page of document from the data, and tell every day of a release as
  // the time since, as of now.
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
    whatsNew(document, data, cards);
    newer(document, data, labels);
    times(document, labels.locale, now);
  };

  // Fill the page in document with the data that fetch gets, as of now: a home page,
  // whose cards tell where the data is, the Trust page, whose table does, or the
  // Releases page, whose list of the projects does.
  const start = async (document, fetch, now) => {
    const place = document.querySelector("[data-facts]");
    if (!place) {
      return;
    }
    render(document, place, await load(fetch, place), now);
  };

  const api = { SCHEMA, ago, duration, facts, newest, score, share, start };
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
