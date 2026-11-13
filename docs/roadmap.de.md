---
# The title of the browser tab and of search results; the menu says Fahrplan, in the
# section Über.
title: Fahrplan
description: "Was die Website unter dennis-otto.github.io im nächsten Jahr vorhat, von November 2026 bis November 2027, und was sie nicht tun wird."
---

# Fahrplan

<!-- This page belongs to the project. Keep every sentence true to the repository, its issues, its decisions and docs/security.de.md, and change docs/roadmap.md with it. A plan leaves the page in the pull request that ships it; the page looks a year ahead, so move its horizon with the plans. -->

Diese Seite sagt, was die Website unter dennis-otto.github.io im nächsten Jahr vorhat, von November 2026 bis November 2027, und was sie nicht tun wird. Jedes Projekt führt seine eigenen Pläne auf seiner eigenen Website, und der [Blueprint](https://dennis-otto.github.io/repo-blueprint/) die Pläne für das, was alle Websites der Adresse teilen, etwa das Theme. Ein Plan hier kommt aus dem, was das Repository schon enthält: seinen [Issues](https://github.com/Dennis-Otto/dennis-otto.github.io/issues), seinen [Entscheidungen](decisions/README.md), die auf Englisch sind, und den [verbleibenden Risiken](security.md#verbleibende-risiken) seiner Sicherheitsseite. Ideen sind als [Issue](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/new/choose) willkommen.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/the-roadmap.de.dark.svg">
  <img src="images/diagrams/the-roadmap.de.svg" alt="Der Fahrplan der Website: Die nächsten Monate bringen ein gepflegtes Theme anstelle von Material for MkDocs, das am 5. Mai 2027 sein Lebensende erreicht, eine Kopfzeile, die keinen anderen Server fragt, und die Silber-Stufe von OpenSSF Best Practices mit den Stufen der OpenSSF Baseline. Später im Jahr 2027 bekommen die Schriften und Mermaid, die der Build herunterlädt, festgelegte Hashes, oder Mermaid wird gar nicht mehr heruntergeladen. Die Website wird ihre Leser nicht verfolgen, keinen eigenen Server betreiben, aus Live-Daten nicht zweimal dieselben Bytes bauen und die Gold-Stufe nicht anstreben, solange eine Person sie pflegt.">
</picture>

## Als Nächstes, bis zum Frühjahr 2027

- **Ein gepflegtes Theme.** Material for MkDocs, das Theme aller Websites der Adresse, ist mit [Version 9.7.0](https://github.com/squidfunk/mkdocs-material/releases/tag/9.7.0) im November 2025 in den Wartungsmodus gegangen und erreicht am 5. Mai 2027 sein Lebensende, wie die [Notizen der Version 9.8.0](https://github.com/squidfunk/mkdocs-material/releases/tag/9.8.0) sagen, mit Korrekturen kritischer Fehler und Sicherheitsupdates bis zu diesem Tag. Die Website wechselt vorher zu einem gepflegten Nachfolger, etwa Zensical, das das Team von Material baut, sobald es diese Website mit ihren Hooks, ihren zwei Sprachen und ihrem Datenschutz baut, zusammen mit allen Websites des Blueprints, die sich eine Konfiguration von MkDocs teilen: Der Blueprint plant den Wechsel in [seinem Issue #872](https://github.com/Dennis-Otto/repo-blueprint/issues/872), und sein Update bringt ihn hierher. Bis dahin installiert der Docs-Workflow Material mit festgelegten Hashes, und Renovate bringt jede seiner Korrekturen.
- **Eine Kopfzeile, die keinen anderen Server fragt.** Die Kopfzeile fragt `api.github.com` nach der Zahl der öffentlichen Repositorys von [Dennis-Otto](https://github.com/Dennis-Otto), höchstens einmal je Browser-Tab, und GitHub sieht dabei die IP-Adresse jedes Lesers. Die Angaben der Kopfzeile sollen beim Bauen der Website geschrieben werden, wie es die Karten schon sind, damit das Lesen einer Seite keinen Server außer dieser Adresse fragt. Die Kopfzeile gehört zur Konfiguration, die sich alle Websites des Blueprints teilen, also ist die Änderung eine des Blueprints, der noch kein Issue dafür hat; bis dahin fragt die Kopfzeile wie bisher.
- **Die Silber-Stufe von OpenSSF Best Practices.** Die Website hat seit November 2026 die Stufe *passing* von [OpenSSF Best Practices](https://www.bestpractices.dev/projects/16446). Ihre README zeigt beide Badges, diese Seite ist ihr Fahrplan, und Ruff, mypy und Biome prüfen die Programmierstandards ihres Python und ihres JavaScript; das waren die offenen Kriterien von Silber. Die Stufen der OpenSSF Baseline folgen.

## Später im Jahr 2027

- **Festgelegte Downloads beim Bauen.** Das Privacy-Plugin lädt bei jedem Build die Schriften von Google Fonts und Mermaid von unpkg herunter, ohne festgelegten Hash, wie die [verbleibenden Risiken](security.md#verbleibende-risiken) sagen. Die Hooks des Blueprints legen die Version von Mermaid schon fest. Die Downloads sollen festgelegte Hashes bekommen, oder Mermaid soll gar nicht mehr heruntergeladen werden, da jedes Diagramm dieser Website ein Bild ist. Beides sind Änderungen der Hooks des Blueprints, der noch kein Issue dafür hat.

## Was die Website nicht tun wird

- **Kein Tracking.** Keine Cookies, keine Analyse, keine Werbung und kein Service Worker: Die Website speichert nichts über ihre Leser, wie [ihre Sicherheitsseite](security.md#was-du-erwarten-kannst) sagt.
- **Kein eigener Server.** Sie bleibt eine statische Website auf GitHub Pages, ohne Konten, Kommentare oder Code, der auf einem Server läuft. Fragen und Ideen gehören in die Issues des jeweiligen Projekts.
- **Kein Build, der zweimal dieselben Bytes liefert.** Der tägliche Build nimmt mit Absicht Live-Daten: die Notizen der neuesten Releases, die Suchindizes der Projekt-Websites, die Stufen von OpenSSF Best Practices und das, womit jedes Projekt läuft. Ein Build desselben Commits einen Tag später sieht anders aus, deshalb verspricht die Website keinen wiederholbaren Build.
- **Keine Gold-Stufe, solange eine Person sie pflegt.** Die Gold-Stufe von OpenSSF Best Practices verlangt, dass eine zweite Person die meisten Änderungen prüft, und das Repository hat einen Maintainer. Jede Änderung geht trotzdem durch einen Pull-Request mit jeder Pflichtprüfung.
- **Keine Dokumentation der Projekte.** Jedes Projekt führt seine Dokumentation, sein Changelog und seine Pläne auf seiner eigenen Website; diese hier führt dorthin.

## Wie sich dieser Fahrplan ändert

Ein Plan verlässt diese Seite mit dem Pull-Request, der ihn umsetzt, und ein neuer kommt mit dem Issue oder der Entscheidung dazu, aus der er stammt. Ein Kurswechsel, der die Website prägt, wird als [Entscheidung](decisions/README.md) aufgeschrieben, auf Englisch. Das [Changelog](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/CHANGELOG.md) zeigt, was schon umgesetzt ist.
