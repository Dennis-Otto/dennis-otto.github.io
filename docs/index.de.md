---
# The title of the browser tab and of search results; the hero of the page has the
# name of the website as its heading.
title: Open-Source-Apps für Home Assistant, Nextcloud und Paperless-ngx
description: "Open-Source-Apps von Dennis Otto: HomeDarts for Autodarts in Home Assistant, Paperless-ngx in Nextcloud und Werkzeuge für Repositorys auf GitHub."
# The preview card of shared links, which has room for three lines of title.
social:
  cards_layout_options:
    title: Home Assistant, Nextcloud und Paperless-ngx
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
  lead: "Open-Source-Projekte für das smarte Zuhause, das Dokumentenarchiv und die Arbeit auf GitHub. Jedes bringt Tests, signierte Releases, Sicherheitsprüfungen und Bots mit, die sich darum kümmern, und jedes hat eine eigene Website. Die Suche oben findet die Seiten aller Projekte."
  projects: Zu den Projekten
  sponsor: Unterstützen
---

<!-- The groups of the projects with their cards come from projects.toml: .github/mkdocs_project.py puts them in place of the marker below while MkDocs builds the website. -->

<!-- projects -->

## Wie sie zusammengehören { #together }

<!-- The source of the picture is docs/diagrams/how-the-projects-belong-together.de.mmd, which the About page shows as well. -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/how-the-projects-belong-together.de.dark.svg">
  <img src="images/diagrams/how-the-projects-belong-together.de.svg" alt="Wie die Projekte zusammengehören: Oben stehen die Werkzeuge für Maintainer. Repo Blueprint macht jedes Repository, auch die des Issue assistant und von Repo Pager, und bringt jedes seiner Releases zu allen; der Issue assistant sichtet die Issues jedes Repositorys, Repo Pager meldet, was seinen Maintainer braucht, etwa einen fehlgeschlagenen Lauf, und das Repository-Dashboard zeigt den Stand jedes einzelnen. Darunter stehen die Apps, jede mit dem, womit sie sich verbindet. HomeDarts for Autodarts bringt ein Autodarts-Board in Home Assistant, und Player Switch for Autodarts wechselt die Spieler eines gemeinsamen Boards im Browser. Paperless Sync bringt die Dokumente von Paperless-ngx als Archiv in Nextcloud, und Paperless Unified Search bringt die Suche von Paperless-ngx in die von Nextcloud, wo ein Treffer die Datei öffnet, die Paperless Sync gebracht hat.">
</picture>

## Neuigkeiten { #whats-new }

<!-- The hooks put the latest release of every project, with the headline of its notes, in place of the marker below, and docs/javascripts/projects.js brings it up to date from the data of the dashboard as the page loads. -->

<!-- releases -->

[Alle Releases](releases.md) hat die Notizen der letzten Releases jedes Projekts. Das [Dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) zeigt das neueste Release jedes Projekts mit dem Stand seiner Prüfungen und den Zahlen seiner Tests, und der [Feed aller Releases](https://dennis-otto.github.io/repo-blueprint/dashboard/releases.atom) bringt jedes neue in einen Feedreader.

## Unterstützung

Fragen und Ideen gehören ins Repository des jeweiligen Projekts; Sicherheitslücken werden vertraulich gemeldet, wie es dessen Sicherheitsrichtlinie beschreibt. Wenn dir die Projekte nützen, kannst du [ihre Entwicklung unterstützen](https://github.com/sponsors/Dennis-Otto).
