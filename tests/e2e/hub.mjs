// The browser tests of the hub, which scripts/check-site.sh runs after its checks of the
// files of the built website: they open the website that MkDocs built into a folder,
// such as site/, in Chrome, as a reader does, in the light scheme at the width of a
// phone and of a desktop, and use what only works together with the JavaScript of
// Material for MkDocs in a browser:
//
//   search         A word that only a project website has, typed into the search of
//                  the home page, shows a result that leads to that website: the
//                  index that the hooks merged, Material's search and the hold of
//                  overrides/partials/search-hold.js, which lets Material ask for the
//                  index only after the page has loaded.
//   old addresses  An old folder of a renamed project, a page of former/<folder>.txt
//                  and an address that the old website never had lead to the same
//                  path in the new folder, with the query and the fragment: the pages
//                  that the hooks write there, and the moves of the 404 page.
//   suggestions    An address that leads nowhere, such as /homedarts/, shows the
//                  project that it resembles on the 404 page, in English and German.
//   live facts     The cards of the home page and the table of the Trust page show
//                  the release of each project from the data of the dashboard,
//                  which docs/javascripts/projects.js writes into them.
//   language       The language switch of the home page leads to the German one.
//
// The folder answers every request to the address of the website as GitHub Pages
// does: with a file of it, or with its 404.html and the status 404 for one that it
// lacks. The data of the dashboard comes from tests/fixtures/repos.json, a page of a
// project website is a stand-in, and a request to another server is refused and
// named, so the tests read nothing from the network. A scenario that fails names
// itself, the width and what broke, in the CI as an annotation and in the summary of
// the job too, and leaves a screenshot and a trace of Playwright in .e2e/ of the folder,
// which the artifact website of a pull request keeps; https://trace.playwright.dev
// opens a trace in the browser, without sending it anywhere. After a build, on your
// machine:
//
//   npm ci --prefix tests/e2e --ignore-scripts
//   node tests/e2e/hub.mjs site
//
// It drives Google Chrome, which GitHub's runners have; CHROME names another Chrome or
// Chromium by the path of its program. Without either, it says so and passes on your
// machine, and fails in the CI. Renovate keeps playwright-core current.

import { existsSync } from "node:fs";
import { appendFile, mkdir, readdir, readFile, rm, stat } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
// The data of the dashboard that the live facts show, the same as the tests of
// docs/javascripts/projects.js read.
const FIXTURE = path.join(ROOT, "tests/fixtures/repos.json");
// The pages of the old website of each renamed project.
const FORMER = path.join(ROOT, "former");
// The folder of the website that keeps the screenshot and the trace of each failure.
const RESULTS = ".e2e";
// The widths of a reader: a phone and a desktop.
const WIDTHS = {
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  desktop: { viewport: { width: 1280, height: 900 } },
};
// How long a step may take; the search of a phone builds its index in the browser.
const WAIT = 20_000;
// The request of Material for the search index, of the page's language too.
const INDEX = /\/search\/search_index(?:\.[\w-]+)?\.json$/;
const TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".webm": "video/webm",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".xml": "application/xml",
};

/** A step that failed, with what it means for the reader in place of the error of
 * Playwright, whose first line it keeps as the cause. */
async function must(action, message) {
  try {
    return await action;
  } catch (error) {
    const cause = String(error?.message ?? error).split("\n")[0];
    throw new Error(`${message} (${cause})`, { cause: error });
  }
}

/** Fails with message unless the condition holds. */
function expect(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

/** Whether a file is there. */
async function isFile(file) {
  try {
    return (await stat(file)).isFile();
  } catch {
    return false;
  }
}

/** The text of a file of the folder, or "" when it lacks the file. */
async function textOf(file) {
  try {
    return await readFile(file, "utf-8");
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------- what the website holds

/** What the scenarios need to know of the built website, read from its files. A part
 * that is missing stays empty, and the scenario that needs it names it. */
async function survey(site) {
  const home = await textOf(path.join(site, "index.html"));
  const canonical = home.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  const address = new URL(".", canonical ?? "https://website.test/").href;
  const data = home.match(/data-facts="([^"]+)"/)?.[1];
  const history = home.match(/data-history="([^"]+)"/)?.[1];
  const notFound = (await textOf(path.join(site, "404.html"))).match(
    /<script type="application\/json" id="not-found-data">([\s\S]*?)<\/script>/,
  );
  let moves = {};
  let projects = [];
  try {
    ({ moves = {}, projects = [] } = JSON.parse(notFound?.[1] ?? "{}"));
  } catch {
    // Data that isn't JSON is none: the scenarios that need it name what is missing.
  }
  // The folders of the project websites at the address, which another repository
  // publishes, such as /homedarts-for-autodarts/.
  const websites = new Map();
  for (const project of projects) {
    const url = project.url?.en;
    if (typeof url === "string" && url.startsWith(address)) {
      websites.set(url.slice(address.length).split("/")[0], project);
    }
  }
  return {
    site,
    address,
    origin: new URL(address).origin,
    prefix: new URL(address).pathname,
    data: data && new URL(data, address).pathname,
    history: history && new URL(history, address).pathname,
    moves,
    projects,
    websites,
    search: await searchWord(site, home, websites),
  };
}

/** A word that the search index of the home page has only in the pages of a project
 * website, such as a word of the title of one of its pages, and the folders of the
 * websites that have it; null when the index has no page of a project website. */
async function searchWord(site, home, websites) {
  // The script of the blueprint in the head of the page asks for the index of its
  // language in place of search_index.json, such as search_index.en.json.
  const language = home.match(/search\/search_index\.([\w-]+)\.json/)?.[1];
  const name = language ? `search_index.${language}.json` : "search_index.json";
  let docs = [];
  try {
    docs = JSON.parse(await textOf(path.join(site, "search", name))).docs ?? [];
  } catch {
    // No index, or one that isn't JSON, has no page of a project website.
  }
  const own = [];
  const theirs = [];
  for (const doc of docs) {
    const folder = String(doc.location).split(/[/#]/)[0];
    (websites.has(folder) && !existsSync(path.join(site, folder)) ? theirs : own).push(doc);
  }
  // Material matches the start of a word, so the word is in no text of the hub at all.
  const hub = own.map((doc) => `${doc.title} ${doc.text}`.toLowerCase()).join(" ");
  const counts = new Map();
  for (const doc of theirs) {
    for (const word of new Set(String(doc.title).toLowerCase().split(/[\s-]+/))) {
      if (/^[a-z]{7,16}$/.test(word) && !hub.includes(word)) {
        counts.set(word, (counts.get(word) ?? 0) + 1);
      }
    }
  }
  const [word] = [...counts].sort(([a, m], [b, n]) => n - m || a.localeCompare(b))[0] ?? [];
  if (!word) {
    return null;
  }
  const folders = new Set(
    theirs
      .filter((doc) => `${doc.title} ${doc.text}`.toLowerCase().includes(word))
      .map((doc) => String(doc.location).split(/[/#]/)[0]),
  );
  return { word, file: `search/${name}`, folders: [...folders].sort() };
}

// ---------------------------------------------------------------- the scenarios

/** The search finds a page of a project website. */
async function search(page, hub) {
  expect(
    hub.search,
    "The search index of the home page has no page of a project website, so the search can't find one: " +
      "the hooks of .github/mkdocs_project.py no longer merge the indexes of the project websites into it, " +
      "or GitHub Pages was away for every one of them during the build.",
  );
  const { word, file, folders } = hub.search;
  const names = folders.map((folder) => hub.websites.get(folder)?.name?.en ?? folder).join(" and ");
  let loaded = false;
  let early = false;
  page.on("load", () => {
    loaded = true;
  });
  page.on("request", (request) => {
    if (INDEX.test(new URL(request.url()).pathname) && !loaded) {
      early = true;
    }
  });
  await must(page.goto(hub.address, { waitUntil: "load" }), "The home page doesn't load");
  expect(
    !early,
    "The home page asked for the search index before it had loaded: the hold of " +
      "overrides/partials/search-hold.js, which overrides/main.html includes before the scripts of " +
      "the theme, no longer holds the request back.",
  );
  // The button of the search in the header on a phone, the box itself on a desktop.
  const toggle = page.locator('label.md-header__button[for="__search"]');
  if (await toggle.isVisible()) {
    await must(toggle.click(), "The button of the search in the header can't be pressed");
  }
  await must(page.locator("input.md-search__input").fill(word), "The search box of the home page takes no text");
  const wanted = folders.map((folder) => `${hub.address}${folder}/`);
  await must(
    page.waitForFunction(
      (starts) =>
        [...document.querySelectorAll(".md-search-result a")].some((link) =>
          starts.some((start) => link.href.startsWith(start)),
        ),
      wanted,
      { timeout: WAIT },
    ),
    `Searching for "${word}", a word of ${names} in ${file} alone, shows no result that leads to that ` +
      "website: the merged search index, Material's search or the hold of overrides/partials/search-hold.js " +
      "no longer work together",
  );
}

/** The old addresses of a renamed project lead to its new folder. */
async function oldAddresses(page, hub) {
  // Every old folder of former/ has its move; without a renamed project, there is
  // nothing to lead.
  const former = (await readdir(FORMER).catch(() => []))
    .filter((name) => name.endsWith(".txt"))
    .map((name) => name.slice(0, -".txt".length));
  const unmoved = former.filter((old) => !Object.hasOwn(hub.moves, old));
  expect(
    unmoved.length === 0,
    `The 404 page has no move for the old folder ${unmoved.join(", ")} of former/ in #not-found-data: ` +
      "overrides/404.html no longer gets the moves of the catalog.",
  );
  for (const [old, target] of Object.entries(hub.moves)) {
    const pages = (await textOf(path.join(FORMER, `${old}.txt`)))
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));
    // A page in a folder of the old website, other than the page of a folder, whose
    // address in the new folder is that of the folder.
    const deep = pages.find((line) => line.includes("/") && !line.endsWith("index.html"));
    const visits = [
      // The old folder, and a page of the old website, each a page that the hooks
      // write; then an address that the old website never had, which only the 404
      // page leads on.
      { path: "", status: 200, what: `the page that the hooks write at the old folder /${old}/` },
      ...(deep
        ? [
            {
              path: deep,
              status: 200,
              what: `the page that the hooks write at /${old}/${deep}, which former/${old}.txt lists`,
            },
          ]
        : []),
      { path: "images/e2e-picture.png", status: 404, what: "the 404 page, with the moves of #not-found-data" },
    ];
    for (const visit of visits) {
      const from = `${hub.address}${old}/${visit.path}?from=e2e#top`;
      const to = `${target}${visit.path}?from=e2e#top`;
      const response = await must(page.goto(from, { waitUntil: "commit" }), `The old address ${from} doesn't load`);
      expect(
        response?.status() === visit.status,
        `The old address ${from} answered ${response?.status()}, not ${visit.status}: ` +
          (visit.status === 200
            ? `${visit.what} is missing, so .github/mkdocs_project.py no longer writes it.`
            : "the folder of the website has a file there, where the test expects none."),
      );
      await must(
        page.waitForURL((url) => url.href === to, { timeout: WAIT }),
        () =>
          `The old address ${from} leads to ${page.url()}, not to ${to}: ${visit.what} no longer leads to the ` +
          "same path in the new folder, with its query and its fragment",
      );
    }
  }
}

/** The 404 page suggests the project that an address resembles. */
async function suggestions(page, hub) {
  const [project] = hub.projects;
  expect(
    project,
    "The 404 page has no projects in #not-found-data: overrides/404.html no longer gets the projects of the catalog.",
  );
  // The first word of the folder of the first project, such as /homedarts/.
  const wanted = project.slug.split("-")[0];
  const from = `${hub.address}${wanted}/`;
  const response = await must(page.goto(from), `The address ${from} doesn't load`);
  expect(response?.status() === 404, `The address ${from} answered ${response?.status()}, not 404 with the 404 page.`);
  for (const [language, name, start] of [
    ["en", "English", "Did you mean "],
    ["de", "German", "Meintest du "],
  ]) {
    const line = page.locator(`#did-you-mean p[lang="${language}"]`);
    await must(
      line.waitFor({ timeout: WAIT }),
      `The 404 page at ${from} suggests no project in ${name}: overrides/partials/not-found.js, which ` +
        "overrides/404.html includes, no longer writes the question into #did-you-mean",
    );
    const text = (await line.textContent()) ?? "";
    expect(
      text.startsWith(start),
      `The ${name} suggestion of the 404 page at ${from} reads "${text}", not "${start}…".`,
    );
    const links = await line.locator("a").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")));
    expect(
      links.includes(project.url[language]),
      `The ${name} suggestion of the 404 page at ${from} leads to ${links.join(", ") || "nothing"}, not to ` +
        `${project.name[language]} at ${project.url[language]}.`,
    );
  }
}

/** The cards of the home page and the table of the Trust page show the live facts. */
async function liveFacts(page, hub) {
  expect(
    hub.data,
    "The home page names no data of the dashboard in data-facts: .github/mkdocs_project.py no longer writes " +
      "the place of the live facts.",
  );
  const releases = new Map(
    JSON.parse(await readFile(FIXTURE, "utf-8"))
      .repos.filter((entry) => typeof entry.release === "string" && entry.release)
      .map((entry) => [entry.repo, entry.release]),
  );
  const places = [
    {
      page: "",
      name: "the card",
      selector: ".project-facts[data-repo]",
      shows: (repo, release) =>
        `.project-facts[data-repo="${repo}"] li[data-live] a:text-is("${release}")`,
      fills: "the cards of the home page, .project-facts[data-repo]",
    },
    {
      page: "trust.html",
      name: "the release cell of the table",
      selector: 'td[data-fact="release"][data-repo]',
      shows: (repo, release) => `td[data-fact="release"][data-repo="${repo}"] a:text-is("${release}")`,
      fills: 'the cells of the table of the Trust page, td[data-fact][data-repo]',
    },
  ];
  for (const place of places) {
    const address = `${hub.address}${place.page}`;
    await must(page.goto(address), `The page ${address} doesn't load`);
    const repos = await page
      .locator(place.selector)
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-repo")));
    const shown = repos.filter((repo) => releases.has(repo));
    expect(
      shown.length > 0,
      `The page ${address} has no ${place.name} of a project of tests/fixtures/repos.json: ` +
        `.github/mkdocs_project.py no longer writes ${place.fills}.`,
    );
    for (const repo of shown) {
      await must(
        page.locator(place.shows(repo, releases.get(repo))).first().waitFor({ timeout: WAIT }),
        `${place.name[0].toUpperCase()}${place.name.slice(1)} of ${repo} on ${address} doesn't show its release ` +
          `${releases.get(repo)} from the data of the dashboard: docs/javascripts/projects.js, which ` +
          `overrides/facts.html loads, no longer fills ${place.fills}`,
      );
    }
  }
}

/** The language switch of the home page leads to the German home page. */
async function language(page, hub) {
  await must(page.goto(hub.address), "The home page doesn't load");
  await must(
    page.locator(".md-header__option .md-select > button").click(),
    "The home page has no language switch in its header",
  );
  await must(
    page.locator('.md-select__link[hreflang="de"]').click(),
    "The language switch of the home page offers no German page",
  );
  const german = [`${hub.prefix}de/`, `${hub.prefix}de/index.html`];
  await must(
    page.waitForURL((url) => german.includes(url.pathname), { timeout: WAIT }),
    () => `The language switch of the home page leads to ${page.url()}, not to the German home page ${hub.prefix}de/`,
  );
  const lang = await page.locator("html").getAttribute("lang");
  expect(lang === "de", `The German home page has the language "${lang}", not "de".`);
}

export const SCENARIOS = [
  { id: "search", title: "The search finds a project website", run: search },
  { id: "old-addresses", title: "The old addresses lead to the new folder", run: oldAddresses },
  { id: "suggestions", title: "The 404 page suggests a project", run: suggestions },
  { id: "live-facts", title: "The live facts fill the cards and the Trust table", run: liveFacts },
  { id: "language", title: "The language switch leads to the German home page", run: language },
];

// ---------------------------------------------------------------- the browser

/** Answers every request to the address from the folder, as GitHub Pages does, the
 * data of the dashboard from the fixture and a page of a project website with a
 * stand-in, and refuses every other request, whose server it names. */
async function serve(context, hub, foreign) {
  const root = path.resolve(hub.site);
  const data = await readFile(FIXTURE);
  const missing = await readFile(path.join(root, "404.html")).catch(() => Buffer.from("Not found"));
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== hub.origin || !url.pathname.startsWith(hub.prefix)) {
      foreign.add(url.origin);
      await route.abort("blockedbyclient");
      return;
    }
    if (url.pathname === hub.data) {
      await route.fulfill({ status: 200, contentType: TYPES[".json"], body: data });
      return;
    }
    if (url.pathname === hub.history) {
      await route.fulfill({ status: 404, contentType: TYPES[".txt"], body: "Not found" });
      return;
    }
    const rest = decodeURIComponent(url.pathname.slice(hub.prefix.length));
    let file = path.resolve(root, rest);
    if (url.pathname.endsWith("/")) {
      file = path.join(file, "index.html");
    }
    if (file !== root && !file.startsWith(root + path.sep)) {
      await route.fulfill({ status: 403 });
      return;
    }
    if (await isFile(file)) {
      const type = TYPES[path.extname(file).toLowerCase()] ?? "application/octet-stream";
      await route.fulfill({ status: 200, contentType: type, body: await readFile(file) });
      return;
    }
    const website = hub.websites.get(rest.split("/")[0]);
    if (website && !existsSync(path.join(root, rest.split("/")[0]))) {
      await route.fulfill({
        status: 200,
        contentType: TYPES[".html"],
        body:
          `<!doctype html><html lang="en"><title>${website.name.en}</title>` +
          `<p>A page of the website of ${website.name.en}, which these tests don't open.</p></html>`,
      });
      return;
    }
    await route.fulfill({ status: 404, contentType: TYPES[".html"], body: missing });
  });
}

/** Starts the Chrome of the runner, or the one that CHROME names. */
function launch() {
  const executablePath = process.env.CHROME || undefined;
  return chromium.launch(executablePath ? { executablePath } : { channel: "chrome" });
}

/** Runs a scenario at a width in a browser of its own, and keeps the screenshot and
 * the trace of a failure. */
async function attempt(browser, hub, scenario, width, results) {
  const started = performance.now();
  const foreign = new Set();
  const thrown = [];
  const context = await browser.newContext({ ...WIDTHS[width], colorScheme: "light", locale: "en-US" });
  context.setDefaultTimeout(WAIT);
  await serve(context, hub, foreign);
  await context.tracing.start({ screenshots: true, snapshots: true, title: `${scenario.title} (${width})` });
  const page = await context.newPage();
  page.on("pageerror", (error) => thrown.push(error.message));
  let problem = null;
  try {
    await scenario.run(page, hub);
    expect(thrown.length === 0, `A script of the page failed: ${thrown.join("; ")}`);
  } catch (error) {
    problem = error.message;
  }
  const name = `${scenario.id}-${width}`;
  if (problem) {
    await mkdir(results, { recursive: true });
    await page.screenshot({ path: path.join(results, `${name}.png`) }).catch(() => {});
    await context.tracing.stop({ path: path.join(results, `${name}.zip`) }).catch(() => {});
  } else {
    await context.tracing.stop();
  }
  await context.close();
  return { scenario, width, name, problem, foreign: [...foreign], seconds: (performance.now() - started) / 1000 };
}

/** A value for a command of GitHub Actions, such as ::error. */
function escaped(text, property = false) {
  let value = String(text).replaceAll("%", "%25").replaceAll("\r", "%0D").replaceAll("\n", "%0A");
  if (property) {
    value = value.replaceAll(":", "%3A").replaceAll(",", "%2C");
  }
  return value;
}

async function main(argv) {
  if (argv.length !== 1) {
    console.error("Usage: node tests/e2e/hub.mjs SITE, the folder of the built website, such as site.");
    return 2;
  }
  const site = path.resolve(argv[0]);
  if (!(await isFile(path.join(site, "index.html")))) {
    console.error(`${argv[0]} has no index.html; build the website first: mkdocs build --strict`);
    return 2;
  }
  const actions = process.env.GITHUB_ACTIONS === "true";
  const results = path.join(site, RESULTS);
  await rm(results, { recursive: true, force: true });
  const hub = await survey(site);

  let browser;
  try {
    browser = await launch();
  } catch (error) {
    console.error(String(error?.message ?? error).split("\n")[0]);
    console.error("Install Google Chrome, or name another Chrome or Chromium with CHROME=/path/to/chrome.");
    if (process.env.CI) {
      return 1;
    }
    console.log("Chrome is not installed here; the CI runs the browser tests of the hub.");
    return 0;
  }
  let runs;
  try {
    console.log(`The hub at ${hub.address} in Chrome ${browser.version()}, from ${argv[0]}:`);
    if (hub.search) {
      console.log(`  the search looks for "${hub.search.word}", which ${hub.search.folders.join(", ")} alone have`);
    }
    runs = await Promise.all(
      SCENARIOS.flatMap((scenario) =>
        Object.keys(WIDTHS).map((width) => attempt(browser, hub, scenario, width, results)),
      ),
    );
  } finally {
    await browser.close();
  }

  const failed = runs.filter((run) => run.problem);
  for (const run of runs) {
    const mark = run.problem ? "FAILED" : "ok";
    console.log(`  ${mark.padEnd(6)} ${run.scenario.title} (${run.width}, ${run.seconds.toFixed(1)} s)`);
    if (run.problem) {
      console.log(`         ${run.problem}`);
      console.log(`         The screenshot and the trace: ${path.join(argv[0], RESULTS, run.name)}.png and .zip`);
    }
  }
  const foreign = [...new Set(runs.flatMap((run) => run.foreign))].sort();
  if (foreign.length > 0) {
    console.log(`The pages asked other servers, which the tests refused: ${foreign.join(", ")}`);
  }
  if (actions) {
    for (const run of failed) {
      const title = escaped(`Browser test: ${run.scenario.title} (${run.width})`, true);
      console.log(`::error title=${title}::${escaped(run.problem)}`);
    }
  }
  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = [
      "### The hub in a browser",
      "",
      "| Scenario | Phone | Desktop |",
      "| --- | --- | --- |",
      ...SCENARIOS.map((scenario) => {
        const cell = (width) =>
          runs.find((run) => run.scenario === scenario && run.width === width).problem ? "failed" : "passed";
        return `| ${scenario.title} | ${cell("phone")} | ${cell("desktop")} |`;
      }),
      "",
      ...failed.map((run) => `- **${run.scenario.title} (${run.width}):** ${run.problem.replaceAll("|", "\\|")}`),
      ...(failed.length > 0
        ? [
            "",
            `The screenshot and the trace of each failure are in \`${RESULTS}/\` of the artifact *website* ` +
              "of a pull request.",
          ]
        : []),
      "",
    ];
    await appendFile(process.env.GITHUB_STEP_SUMMARY, `${lines.join("\n")}\n`);
  }
  if (failed.length > 0) {
    console.log(`${failed.length} of ${runs.length} browser tests of the hub failed.`);
    return 1;
  }
  console.log(`All ${runs.length} browser tests of the hub passed.`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main(process.argv.slice(2));
}
