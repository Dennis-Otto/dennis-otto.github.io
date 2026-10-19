# Notes of this project for coding agents

Dennis Otto: The projects of Dennis Otto in one place: Home Assistant, Nextcloud and Paperless, GitHub automation and the blueprint they all share.

This file belongs to the project: the blueprint wrote it once, and its updates leave it alone. It adds to `AGENTS.md` what a coding agent needs to know about this project alone, such as its architecture, the commands of its own checks and what to watch for in its tests.

## Where things are

- `README.md` documents installation, configuration and use, `docs/` holds the pages of the website, and `CHANGELOG.md` lists the changes of every release.
- `projects.toml` lists every project once; `.github/mkdocs_project.py`, the hooks of the website, turns it into the cards of both home pages, the table of `README.md`, the files at the root of the address, and on the Trust pages the table of guarantees and the tabs of verify commands in place of `<!-- trust -->` and `<!-- verify -->`, from the `[trust]` texts and the optional `asset` key of each project. Its tests are in `tests/test_mkdocs_project.py`, with every line and branch covered.
- `docs/javascripts/projects.js` writes the live facts of the dashboard into the cards of the home pages and the `td[data-fact]` cells of the Trust pages as they load; `overrides/facts.html` loads it on those pages. Its tests, `tests/projects.test.mjs`, run with Node 20 or newer and no packages, `node --test tests/*.test.mjs`, on a document of their own; `scripts/check-project.sh` runs them with the tests of the hooks.
