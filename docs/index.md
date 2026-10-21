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
# pencil of a page of documentation, and neither menu nor footer with a next page.
template: home.html
hide:
  - navigation
  - toc
  - footer
hero:
  lead: "Open-source projects for the smart home, the document archive and the work on GitHub. Each one comes with tests, signed releases, security checks and bots that look after it, and each has a website of its own. The search at the top finds the pages of all of them."
  projects: See the projects
  sponsor: Sponsor
---

<!-- The groups of the projects with their cards come from projects.toml: .github/mkdocs_project.py puts them in place of the marker below while MkDocs builds the website. -->

<!-- projects -->

## What's new { #whats-new }

<!-- The hooks put the place of the newest release of each project in place of the marker below, and docs/javascripts/projects.js fills it from the data of the dashboard as the page loads. -->

<!-- releases -->

The [dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) shows the latest release of every project with the state of its checks and the numbers of its tests, and the [feed of all releases](https://dennis-otto.github.io/repo-blueprint/dashboard/releases.atom) brings each new one into a feed reader.

## Support

Questions and ideas belong in the repository of each project; vulnerabilities are reported privately, as its security policy describes. If the projects are useful to you, you can [support their development](https://github.com/sponsors/Dennis-Otto).
