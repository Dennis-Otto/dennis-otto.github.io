// The script of the page of every address at dennis-otto.github.io that leads
// nowhere, overrides/404.html, which includes it inline, so that the page asks for no
// further file. It leads an address in a folder where the website of a project lived
// before, such as /ha-autodarts/images/hero.webp, to the same path in its folder now,
// with its query and its fragment. It suggests the projects whose slug, or a folder
// where their website lived before, is like the first part of every other path, such
// as homedarts-for-autodarts for /autodarts/: the slug or a word of it starts with
// that part, the part starts with the slug, or at most 3 letters differ (Levenshtein).
//
// Its data is the JSON in the element #not-found-data of the page, a script of the
// type application/json, which the template writes from projects.toml with
// catalog.moves() and catalog.directory() of .github/mkdocs_project.py:
//
//   {"moves": {"ha-autodarts": "https://dennis-otto.github.io/homedarts-for-autodarts/"},
//    "projects": [{"slug": "homedarts-for-autodarts", "former": ["ha-autodarts"],
//                  "name": {"en": "…", "de": "…"}, "url": {"en": "…", "de": "…"}}, …]}
//
// Jinja reads this file as a template when it includes it, so it holds none of the
// three marks with which Jinja starts its own parts, and the end tag of a script would
// end the script of the page there. tests/not-found.test.mjs checks both, and runs the
// script with Node on a page and an address of its own:
//   node --test tests/*.test.mjs
(() => {
  "use strict";

  let projects;
  let moves;
  let wanted;
  try {
    ({ projects, moves } = JSON.parse(document.getElementById("not-found-data").textContent));
    wanted = decodeURIComponent(location.pathname.split("/")[1]).toLowerCase();
  } catch {
    // A page without its data, or an address that is no valid URI, such as /%E0%A4%A/:
    // the page stays as it is.
    return;
  }
  if (Object.prototype.hasOwnProperty.call(moves, wanted)) {
    const rest = location.pathname.split("/").slice(2).join("/");
    location.replace(moves[wanted] + rest + location.search + location.hash);
    return;
  }
  const distance = (a, b) => {
    let row = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const next = [i];
      for (let j = 1; j <= b.length; j++) {
        next[j] = Math.min(row[j] + 1, next[j - 1] + 1, row[j - 1] + (a[i - 1] !== b[j - 1]));
      }
      row = next;
    }
    return row[b.length];
  };
  const like = (name) =>
    [name, ...name.split("-")].some((word) => word.startsWith(wanted)) || wanted.startsWith(name)
      ? 0
      : distance(wanted, name);
  const score = ({ slug, former }) => Math.min(...[slug, ...former].map(like));
  const found = projects
    .filter((project) => wanted.length > 1 && score(project) <= 3)
    .sort((a, b) => score(a) - score(b));
  if (found.length === 0) {
    return;
  }
  // "Did you mean A, B or C?" in a language, with a link to each website in it.
  const question = (language, start, or) => {
    const line = document.createElement("p");
    line.lang = language;
    line.append(start);
    found.forEach((project, index) => {
      if (index > 0) {
        line.append(index < found.length - 1 ? ", " : or);
      }
      const link = document.createElement("a");
      link.href = project.url[language];
      link.textContent = project.name[language];
      line.append(link);
    });
    line.append("?");
    return line;
  };
  const title = question("en", "Did you mean ", " or ");
  title.className = "admonition-title";
  const box = document.getElementById("did-you-mean");
  box.className = "admonition question";
  box.append(title, question("de", "Meintest du ", " oder "));
})();
