---
# The title of the browser tab and of search results; the hero of the page has the
# name of the website as its heading.
title: Open-source apps for Home Assistant, Nextcloud and Paperless-ngx
description: "Open-source apps by Dennis Otto: HomeDarts for Autodarts in Home Assistant, Paperless-ngx in Nextcloud, and tools that look after repositories on GitHub."
# The preview card of shared links, which has room for three lines of title.
social:
  cards_layout_options:
    title: Home Assistant, Nextcloud and Paperless-ngx
# A landing page: the hero of overrides/home.html instead of the heading and the
# pencil of a page of documentation, neither menu nor footer with a next page, and no
# path above the hero, which overrides/partials/path.html leaves out.
template: home.html
hide:
  - navigation
  - toc
  - footer
  - path
hero:
  lead: "Open-source projects for the smart home, the document archive and the work on GitHub. Each one comes with tests, signed releases, security checks and bots that look after it, and each has a website of its own. The search at the top finds the pages of all of them."
  projects: See the projects
  sponsor: Sponsor
---

<!-- The groups of the projects with their cards come from projects.toml: .github/mkdocs_project.py puts them in place of the marker below while MkDocs builds the website. -->

<!-- projects -->

## How they belong together { #together }

<!-- The source of the picture is docs/diagrams/how-the-projects-belong-together.mmd, which the About page shows as well. -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/how-the-projects-belong-together.dark.svg">
  <img src="images/diagrams/how-the-projects-belong-together.svg" alt="How the projects belong together: The tools for maintainers are on top. Repo Blueprint makes every repository, also those of the issue assistant and of Repo Pager, and brings each of its releases to all of them; the issue assistant triages the issues of every repository, Repo Pager reports what needs its maintainer, such as a failed run, and the repository dashboard shows the state of each. Below them are the apps, each with what it connects to. HomeDarts for Autodarts brings an Autodarts board into Home Assistant, and Player Switch for Autodarts switches the players of a shared board in the browser. Paperless Sync brings the documents of Paperless-ngx into Nextcloud as an archive, and Paperless Unified Search brings the search of Paperless-ngx into that of Nextcloud, where a result opens the file that Paperless Sync brought.">
</picture>

## What's new { #whats-new }

<!-- The hooks put the latest release of every project, with the headline of its notes, in place of the marker below, and docs/javascripts/projects.js brings it up to date from the data of the dashboard as the page loads. -->

<!-- releases -->

[All releases](releases.md) has the notes of the latest releases of every project. The [dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) shows the latest release of every project with the state of its checks and the numbers of its tests, and the [feed of all releases](https://dennis-otto.github.io/repo-blueprint/dashboard/releases.atom) brings each new one into a feed reader.

## Support

Questions and ideas belong in the repository of each project; vulnerabilities are reported privately, as its security policy describes. If the projects are useful to you, you can [support their development](https://github.com/sponsors/Dennis-Otto).
