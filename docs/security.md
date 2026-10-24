---
# The title of the browser tab and of search results; the menu says This website,
# in the section Trust.
title: Security and privacy
description: "What the website at dennis-otto.github.io keeps in your browser, which servers a page asks, how a change reaches the website, and where to report a vulnerability of any website at the address."
---

# Security and privacy

<!-- This page belongs to the project. Keep every sentence true to the repository and to a measurement of the live website, and change docs/security.de.md with it. -->

This page is about the website at dennis-otto.github.io itself: what it does in your browser, how a change reaches it, where its trust boundaries lie and which risks remain. Each project describes its own software on its own website. [SECURITY.md](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/SECURITY.md) says what happens with a report and how the repository keeps itself secure.

## What you can expect

- **Static pages over HTTPS.** GitHub Pages serves the pages as files; no code of the website runs on a server. It answers an `http://` address with a redirect to `https://`, and tells your browser to use nothing but HTTPS for the address for a year (HSTS).
- **No cookies, analytics, advertising or sign-in,** and no form that sends what you type anywhere.
- **Fonts and scripts from this address.** While the website is built, the privacy plugin of Material for MkDocs downloads the Roboto fonts from Google Fonts and the Mermaid script for diagrams from unpkg, and the website serves them itself, under `/assets/external/`. Reading a page asks neither Google nor unpkg.
- **The search stays in your browser.** Its index is a file of the website, which holds the pages of every project website too, and what you type into the search box stays on the page.
- **Two small entries in your browser.** Its local storage keeps whether the pages are light or dark (`/.__palette`), and its session storage keeps the number of public repositories in the header until the tab closes (`/.__source`). Neither is sent anywhere. The language is part of the address, `/de/` for German, and isn't stored.
- **One request to another server.** The header asks `api.github.com` for the number of public repositories of [Dennis-Otto](https://github.com/Dennis-Otto), at most once per browser tab, so GitHub sees your IP address and that you visit a website at this address. An outdated browser without `ResizeObserver`, such as Safari before version 13.1, also loads a small script from unpkg that adds it. <!-- Once bp-site-chrome renders the facts of the header at build time, remove this bullet, the /.__source entry above, the edge 5 to api.github.com and their mentions in accDescr, boundary 5 and the threats table, in both languages. -->
- **Links that leave the website.** The buttons of the projects lead to HACS through my.home-assistant.io, to the Nextcloud App Store and to GitHub, where their own privacy rules apply.

GitHub, which hosts the website, logs the IP address of every visitor for security purposes, as [About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages#data-collection) says; the [GitHub General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) applies to it.

## Trust boundaries

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/the-trust-boundaries-of-the-website.dark.svg">
  <img src="images/diagrams/the-trust-boundaries-of-the-website.svg" alt="The trust boundaries of the website: Six boundaries. 1, a pull request reaches main only through the ruleset of main and every required check. 2, the Docs workflow builds the website from main with tools from PyPI that are pinned by their hashes, and downloads the fonts from Google Fonts, Mermaid from unpkg and the search indexes of the project websites while it builds. 3, its deploy job alone publishes the website, in the environment github-pages, which accepts main alone, with a short-lived OIDC token. 4, GitHub Pages serves this website at the root of dennis-otto.github.io, on the same origin as the project websites, which their own repositories build and publish. 5, your browser gets the pages over HTTPS and asks api.github.com for the number of public repositories. 6, the install links lead to HACS, the Nextcloud App Store and GitHub.">
</picture>

1. **A pull request → `main`.** A change reaches `main` only through a pull request that is up to date with `main` and passes every required check, squashed into one signed commit. The ruleset of `main` has no exceptions, not even for administrators. Among the checks, *docs* builds the website strictly, so that a link or an anchor that leads nowhere fails it; CodeQL and actionlint examine the workflows, Gitleaks the secrets and the dependency review new dependencies.
2. **Third-party code → the build.** The Docs workflow installs MkDocs, Material for MkDocs and their plugins from PyPI with `pip install --require-hashes -r .github/docs-requirements.txt`, so pip refuses every file whose SHA-256 hash differs from the lock file. The actions are pinned to commit hashes. While the website is built, the privacy plugin downloads the fonts from Google Fonts and Mermaid from unpkg, as `mermaid@11`, the newest release of version 11; these downloads have no pinned hash. The hooks of the website download the search index of each project website at the address too and add its titles and excerpts to the search of this website. Harden-Runner records the network traffic of every job.
3. **The build → GitHub Pages.** The jobs that build the website hold a token that can only read. The deploy job alone may publish: it runs in the environment `github-pages`, which accepts runs on `main` alone, and identifies its workflow with an OIDC token that GitHub issues for that one run, instead of a stored secret. No branch holds the published website.
4. **The websites of the projects → the same address.** [HomeDarts for Autodarts](https://dennis-otto.github.io/homedarts-for-autodarts/), [Player Switch for Autodarts](https://dennis-otto.github.io/player-switch-for-autodarts/), [Paperless Sync](https://dennis-otto.github.io/paperless-sync/), [Paperless Unified Search](https://dennis-otto.github.io/paperless-unified-search/), the [issue assistant](https://dennis-otto.github.io/issue-assistant/) and [Repo Blueprint](https://dennis-otto.github.io/repo-blueprint/) live in folders of the address, and each is built and published by its own repository, with its own checks. For your browser, they and this website are one origin, `https://dennis-otto.github.io`. This repository serves the root of the address: `robots.txt`, `security.txt` and the icons for all of them, and the 404 page for every address outside the folders of the projects, whose websites answer a missing page with their own.
5. **The website → your browser.** The pages travel over HTTPS, and the only other server that a page asks is `api.github.com`, for the header.
6. **The install links → other services.** HACS, the Nextcloud App Store and GitHub deliver the software of the projects. The SECURITY.md of each project says how to verify its releases.

## Threats and countermeasures

| Threat | Countermeasure | Evidence |
| --- | --- | --- |
| A tampered build tool on PyPI | pip installs only files with the hash of the lock file. A new version arrives with the update pull request of the blueprint and passes every check here; in repo-blueprint, Renovate proposes it a week after its release at the earliest, unless it fixes a vulnerability | `.github/docs-requirements.txt`, which the blueprint keeps current; `stacks/docs/requirements-docs.txt` and `.github/renovate-blueprint.json5` in repo-blueprint |
| A changed font or Mermaid release, downloaded while the website is built | The download runs over HTTPS on a runner of GitHub, never in your browser, and Harden-Runner records it. Mermaid has no pinned version yet, which [Residual risks](#residual-risks) describes | `/assets/external/` of the website, `.github/workflows/docs.yml` |
| A harmful change to a page, a hook or a workflow | The ruleset of `main` without exceptions, every required check and a squashed, signed commit | `.github/repository.toml` |
| An unauthorized deployment | The deploy job alone publishes, in the environment `github-pages`, which accepts `main` alone, with a short-lived OIDC token; no key or token for publishing is stored anywhere | `.github/workflows/docs.yml`, the branch policy of the environment |
| Someone on the network reads or changes a page | HTTPS, which GitHub Pages enforces, and HSTS for a year | the header `Strict-Transport-Security: max-age=31556952` |
| A link to another website breaks or changes hands | Every address of a project card starts with `https://`. The Links workflow checks the links of the pages and of the README, which lists every address of the cards, every week, and opens an issue for a broken one. It leaves out the redirect of my.home-assistant.io behind the HACS button, as `lychee.toml` says | `URL` in `.github/mkdocs_project.py`, `.github/workflows/links.yml`, `lychee.toml` |
| A text of `projects.toml` breaks a card or the structured data of the home page | Brackets in the texts of a card are escaped, and no text can end the script of the structured data | `test_a_card_escapes_brackets_in_its_texts` and `test_no_text_of_the_catalog_ends_the_script_of_the_structured_data` in `tests/test_mkdocs_project.py` |
| The search index of a project website carries markup or a script into the search of this website, or can't be downloaded | The search takes the plain text of every title and excerpt of a project, escaped, and leaves out an index that isn't one. A project whose index can't be downloaded stays out of the search until the next build, which passes | `test_an_excerpt_is_the_plain_text_of_a_section`, `test_a_broken_search_index_is_named` and `test_the_search_of_the_address_adds_every_project_website` in `tests/test_mkdocs_project.py` |
| The notes of a release carry markup or a script into the Releases page, or can't be read | The build keeps of the notes only text, paragraphs, lists, headings, tables, code, quotes and links to `https://`, without an attribute but the address of a link, and puts them into the page after Markdown. Without the API, the page links the releases on GitHub, and the build passes | `test_no_script_or_picture_of_a_release_reaches_the_page` and `test_the_notes_keep_text_lists_code_and_links_to_https_alone` in `tests/test_mkdocs_project.py` |
| A compromised project website on the shared origin | Nothing to steal: no website of the address sets a cookie or has a sign-in, and the browser's storage holds the color scheme and the number of repositories | the headers and pages of the live websites |

## Residual risks

- **The root of the address.** A service worker registered by this website could control every page of dennis-otto.github.io, the project websites included, while a project website can register one for its own folder only. This website registers none. That makes a change to this repository the most sensitive of them all.
- **One origin for every website.** A flaw in any of them, such as a script that a compromised build tool adds to its pages, reaches the others in your browser, because one origin shares the browser's storage and lets one page script another.
- **Downloads at build time.** The fonts and Mermaid are downloaded anew in every build, without a pinned hash, and Mermaid follows the newest release of version 11. A harmful release on unpkg would reach the website with the next change of `main`; only a page with a diagram, such as this one, loads Mermaid.
- **GitHub.** GitHub hosts the website, the repository and the request of the header, and logs the IP addresses of the visitors. Whoever controls the GitHub account Dennis-Otto can change every website of the address.
- **Material for MkDocs.** Material for MkDocs went into maintenance mode with [version 9.7.0](https://github.com/squidfunk/mkdocs-material/releases/tag/9.7.0) in November 2025, with critical bug fixes and security updates promised for at least 12 months, until about November 2026. After that, a vulnerability in its JavaScript may stay unfixed.

## Report a vulnerability

Please don't open a public issue for a suspected vulnerability. Report it privately to the repository that builds the affected website; [SECURITY.md](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/SECURITY.md#what-happens-next) says what happens next and how fast.

| Website | Report privately |
| --- | --- |
| [This website](index.md), the root of the address, and anything you can't place | [dennis-otto.github.io](https://github.com/Dennis-Otto/dennis-otto.github.io/security/advisories/new) |
| [HomeDarts for Autodarts](https://dennis-otto.github.io/homedarts-for-autodarts/) | [homedarts-for-autodarts](https://github.com/Dennis-Otto/homedarts-for-autodarts/security/advisories/new) |
| [Player Switch for Autodarts](https://dennis-otto.github.io/player-switch-for-autodarts/) | [player-switch-for-autodarts](https://github.com/Dennis-Otto/player-switch-for-autodarts/security/advisories/new) |
| [Paperless Sync](https://dennis-otto.github.io/paperless-sync/) | [paperless-sync](https://github.com/Dennis-Otto/paperless-sync/security/advisories/new) |
| [Paperless Unified Search](https://dennis-otto.github.io/paperless-unified-search/) | [paperless-unified-search](https://github.com/Dennis-Otto/paperless-unified-search/security/advisories/new) |
| [Issue assistant](https://dennis-otto.github.io/issue-assistant/) | [issue-assistant](https://github.com/Dennis-Otto/issue-assistant/security/advisories/new) |
| [Repo Blueprint](https://dennis-otto.github.io/repo-blueprint/) and the [dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) | [repo-blueprint](https://github.com/Dennis-Otto/repo-blueprint/security/advisories/new) |

[security.txt](https://dennis-otto.github.io/security.txt) names the first of these forms for the whole address, and this page as its policy.

## Decisions

The [decision records](decisions/README.md) explain the decisions that shape the website and its repository, each with its reasons.
