// The script of every page, overrides/main.html, which includes it inline in front of
// the scripts of the theme, so that it runs before them and asks for no further file.
// The search index of the website, /search/search_index.json, holds the pages of
// every project website as well (.github/mkdocs_project.py), which makes it the
// largest file a page loads. Material for MkDocs asks for it with XMLHttpRequest as
// soon as its script runs, while the fonts and the pictures of the page still load,
// so on a slow connection the first paint waits for the index. This script holds that
// one request back until the reader goes to the search box, or until a second after
// the page has loaded, when the browser is idle, whichever comes first: Material's
// search shows its results once the index is there. It changes no other request.
// The script that .github/mkdocs_blueprint.py puts into the head of the page asks for
// the index of the page's language in its place, such as search_index.de.json, when
// this one lets the request go; the hooks of the blueprint fail the strict build when
// Material no longer asks with XMLHttpRequest, so the hold can't silently stop.
//
// Jinja reads this file as a template when it includes it, so it holds none of the
// three marks with which Jinja starts its own parts, and the end tag of a script would
// end the script of the page there. tests/search-hold.test.mjs checks both, and runs
// the script with Node, with a window and an XMLHttpRequest of its own:
//   node --test tests/*.test.mjs
(() => {
  "use strict";

  const index = /\/search\/search_index\.json$/;
  const held = new WeakSet();
  const waiting = [];
  let released = false;
  const open = XMLHttpRequest.prototype.open;
  const send = XMLHttpRequest.prototype.send;

  const release = () => {
    if (released) {
      return;
    }
    released = true;
    for (const go of waiting.splice(0)) {
      go();
    }
  };

  // Both stay functions, which the request calls as its methods, with itself as this.
  XMLHttpRequest.prototype.open = function (...options) {
    const [, url] = options;
    if (!released && index.test(String(url))) {
      held.add(this);
    }
    return open.apply(this, options);
  };
  XMLHttpRequest.prototype.send = function (...body) {
    if (released || !held.has(this)) {
      return send.apply(this, body);
    }
    waiting.push(() => {
      send.apply(this, body);
    });
  };

  window.addEventListener("load", () => {
    window.setTimeout(() => {
      if ("requestIdleCallback" in window) {
        window.requestIdleCallback(release, { timeout: 2000 });
      } else {
        release();
      }
    }, 1000);
  });
  document.addEventListener("focusin", (event) => {
    if (event.target.closest?.(".md-search")) {
      release();
    }
  });
})();
