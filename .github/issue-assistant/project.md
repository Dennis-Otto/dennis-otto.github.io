This repository is only the website dennis-otto.github.io, which presents the projects of Dennis Otto in one place, in English and German. Its readers are people who use or look for one of the projects. Each project has a repository of its own, with its own issues, code and documentation:

- Dennis-Otto/ha-autodarts: Autodarts for Home Assistant, the integration with its dashboard cards and blueprints.
- Dennis-Otto/paperless-sync: Paperless Sync, the Nextcloud app that mirrors the documents of Paperless-ngx into Nextcloud.
- Dennis-Otto/paperless-unified-search: Paperless Unified Search, the search of Paperless-ngx in the search of Nextcloud.
- Dennis-Otto/issue-assistant: the issue assistant, the GitHub Action that looks after the issues of a repository.
- Dennis-Otto/repo-blueprint: Repo Blueprint, the template of all these repositories, its bots and the repository dashboard, which the short address dennis-otto.github.io/dashboard/ opens.

This repository builds only the hub pages of the website: the home page (`https://dennis-otto.github.io/` and its German version under /de/), the Trust page with the guarantees of every project, the About page, the security page, the decision records and the forward /dashboard/. It also serves what belongs to the root of the whole address: `/robots.txt`, `/security.txt` and `/.well-known/security.txt`, and the 404 page that answers every address outside the documentation websites of the projects. A page under `https://dennis-otto.github.io/<repo>/`, such as `https://dennis-otto.github.io/ha-autodarts/de/`, is the documentation website of `Dennis-Otto/<repo>`, built from that repository.

An issue about a project or its documentation rather than the hub pages belongs to the issues of that project's repository; this one has none of its code. Such an issue is not spam: choose the kind that fits it, say that it belongs to the other repository and name that repository in plain text, such as Dennis-Otto/ha-autodarts, because your comment can't link to other repositories. The table under "The projects" in `README.md` links each repository, and the issue chooser of this repository ("New issue") lists them as well.

Where things are:

- `docs/index.md` is the home page and `docs/index.de.md` its German version; `docs/trust.md` is the Trust page, with a table of the guarantees of every project and the commands that check them, `docs/about.md` the About page, and `docs/security.md` the security and privacy page, each with its German version as `.de.md`; `docs/decisions/` holds the decision records, and `docs/dashboard/index.html` forwards to the repository dashboard.
- `projects.toml` holds the name, the texts and the buttons of every project in English and German, and the texts of the table of the Trust page. `.github/mkdocs_project.py` builds the cards of both home pages, the table and the commands of the Trust page and the table of the projects in `README.md` from it, so a wrong text or a dead button of a card is fixed in `projects.toml`, not in the pages. The release and the numbers on the cards and in the table of the Trust page come from the dashboard, which `docs/javascripts/projects.js` reads as a page loads.
- `.github/mkdocs_project.py` also writes `robots.txt` and `security.txt`, and the structured data (JSON-LD) of the English home page; `overrides/404.html` is the 404 page, whose script suggests a project for a mistyped address.
- `mkdocs.yml` sets up MkDocs with the Material theme, the languages and the menu; `.github/mkdocs-blueprint.yml` holds the settings that every website of the projects shares, and `docs/stylesheets/extra.css` the styles of this website.
- `README.md` explains how the website is built; the Docs workflow publishes it on GitHub Pages with every change of `main`.

What matters in a report about the website: the address of the page, the browser with its version and the device, whether dark mode was on, and a screenshot that shows the problem.

In German, address the reporter with "du", as the German pages do.
