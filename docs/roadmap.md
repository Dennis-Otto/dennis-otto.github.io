---
# The title of the browser tab and of search results; the menu says Roadmap, in the
# section About.
title: Roadmap
description: "What the website at dennis-otto.github.io plans for the next year, from November 2026 to November 2027, and what it won't do."
---

# Roadmap

<!-- This page belongs to the project. Keep every sentence true to the repository, its issues, its decisions and docs/security.md, and change docs/roadmap.de.md with it. A plan leaves the page in the pull request that ships it; the page looks a year ahead, so move its horizon with the plans. -->

This page says what the website at dennis-otto.github.io plans for the next year, from November 2026 to November 2027, and what it won't do. Each project keeps its own plans on its own website, and the [blueprint](https://dennis-otto.github.io/repo-blueprint/) those of the parts that every website of the address shares, such as the theme. A plan here comes from what the repository already holds: its [issues](https://github.com/Dennis-Otto/dennis-otto.github.io/issues), its [decisions](decisions/README.md) and the [residual risks](security.md#residual-risks) of its security page. Ideas are welcome as [an issue](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/new/choose).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/the-roadmap.dark.svg">
  <img src="images/diagrams/the-roadmap.svg" alt="The roadmap of the website: The next months bring a maintained theme in place of Material for MkDocs, whose security fixes end about November 2026, a header that asks no other server, the silver level of OpenSSF Best Practices with the levels of the OpenSSF Baseline, and an accessibility check that accepts no violation. Later in 2027 the fonts and Mermaid, which the build downloads, get pinned hashes, or Mermaid is no longer downloaded. The website won't track its readers, run a server of its own, build the same bytes twice from live data, or seek the gold level while one person maintains it.">
</picture>

## Next, until the spring of 2027

- **A maintained theme.** Material for MkDocs, the theme of every website of the address, went into maintenance mode with [version 9.7.0](https://github.com/squidfunk/mkdocs-material/releases/tag/9.7.0) in November 2025, with security fixes promised until about November 2026. The website moves to a maintained successor, such as Zensical, which the team of Material builds, once it builds this website with its hooks, its two languages and its privacy, together with every website of the blueprint, which share one configuration of MkDocs. Until then, the Docs workflow installs Material pinned by its hashes, and Renovate brings each of its fixes.
- **A header that asks no other server.** The header asks `api.github.com` for the number of public repositories of [Dennis-Otto](https://github.com/Dennis-Otto), at most once per browser tab, which shows GitHub the IP address of each reader. The facts of the header are to be written while the website is built, as the cards already are, so that reading a page asks no server but this address. The blueprint makes this change for every website.
- **The silver level of OpenSSF Best Practices.** The website holds the passing level of [OpenSSF Best Practices](https://www.bestpractices.dev/projects/16446) since November 2026. Its README shows both badges, this page is its roadmap, and Ruff, mypy and Biome check the coding standards of its Python and its JavaScript, which were the open criteria of silver; the levels of the OpenSSF Baseline follow.
- **An accessibility check without exceptions.** The check of every page accepts 146 violations today, the title and the language of the old addresses of HomeDarts for Autodarts, which lead to its new folder, and of the dashboard. Each of them gets its title and its language, so that the check accepts none and a new violation can't hide among them.

## Later in 2027

- **Pinned downloads at the build.** The privacy plugin downloads the fonts from Google Fonts and Mermaid from unpkg in every build, without a pinned hash, as the [residual risks](security.md#residual-risks) say. The hooks of the blueprint pin the version of Mermaid already. The downloads get pinned hashes, or Mermaid is no longer downloaded at all, since every diagram of this website is a picture.

## What the website won't do

- **No tracking.** No cookies, no analytics, no advertising and no service worker: the website keeps nothing about its readers, as [its security page](security.md#what-you-can-expect) says.
- **No server of its own.** It stays a static website on GitHub Pages, without accounts, comments or code that runs on a server. Questions and ideas go to the issues of each project.
- **No build that gives the same bytes twice.** The daily build takes live data on purpose: the notes of the latest releases, the search indexes of the project websites, the levels of OpenSSF Best Practices and what each project works with. A build of the same commit a day later differs, so the website doesn't promise a repeatable build.
- **No gold level while one person maintains it.** The gold level of OpenSSF Best Practices asks a second person to review most changes, and the repository has one maintainer. Every change still goes through a pull request with every required check.
- **No documentation of the projects.** Each project keeps its documentation, its changelog and its plans on its own website; this one leads there.

## How this roadmap changes

A plan leaves this page with the pull request that ships it, and a new one joins it with the issue or the decision it comes from. A change of course that shapes the website gets a [decision record](decisions/README.md). The [changelog](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/CHANGELOG.md) shows what has shipped.
