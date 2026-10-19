---
# The title of the browser tab and of search results; the hero of the page has the
# name of the website as its heading.
title: Open-Source-Apps für Home Assistant, Nextcloud und Paperless-ngx
description: "Open-Source-Apps von Dennis Otto: Autodarts für Home Assistant, Paperless-ngx in Nextcloud und Werkzeuge für Repositorys auf GitHub."
# The preview card of shared links, which has room for three lines of title.
social:
  cards_layout_options:
    title: Home Assistant, Nextcloud und Paperless-ngx
# A landing page: the hero of overrides/home.html instead of the heading and the
# pencil of a page of documentation, and neither menu nor footer with a next page.
template: home.html
hide:
  - navigation
  - toc
  - footer
hero:
  lead: "Open-Source-Projekte für das smarte Zuhause, das Dokumentenarchiv und die Arbeit auf GitHub. Jedes bringt Tests, signierte Releases, Sicherheitsprüfungen und Bots mit, die sich darum kümmern, und jedes hat eine eigene Website. Die Suche oben findet die Seiten aller Projekte."
  projects: Zu den Projekten
  sponsor: Unterstützen
---

<!-- The groups of the projects with their cards come from projects.toml: .github/mkdocs_project.py puts them in place of the marker below while MkDocs builds the website. -->

<!-- projects -->

## Neuigkeiten { #whats-new }

<!-- The hooks put the place of the newest release of each project in place of the marker below, and docs/javascripts/projects.js fills it from the data of the dashboard as the page loads. -->

<!-- releases -->

Das [Dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) zeigt das neueste Release jedes Projekts mit dem Stand seiner Prüfungen und den Zahlen seiner Tests, und der [Feed aller Releases](https://dennis-otto.github.io/repo-blueprint/dashboard/releases.atom) bringt jedes neue in einen Feedreader.

## Unterstützung

Fragen und Ideen gehören ins Repository des jeweiligen Projekts; Sicherheitslücken werden vertraulich gemeldet, wie es dessen Sicherheitsrichtlinie beschreibt. Wenn dir die Projekte nützen, kannst du [ihre Entwicklung unterstützen](https://github.com/sponsors/Dennis-Otto).
