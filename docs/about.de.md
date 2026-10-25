---
# The title of the browser tab and of search results; the menu says Dennis Otto, in
# the section Über.
title: Über
description: "Wer die Open-Source-Projekte unter dennis-otto.github.io baut und warum, und wie ein Blueprint und seine Bots jede Änderung zu einem signierten Release in jedem Repository bringen."
---

# Über

<!-- This page is the German translation of docs/about.md: change both together, and keep every sentence true to the repositories. The page shows the DO monogram and no photo, the default until Dennis chooses; a photo or an avatar replaces the picture below once he gives one. -->

![Das DO-Monogramm von Dennis Otto](assets/logo.svg){ width="96" height="96" .off-glb }

## Wer sie baut { #who }

[Dennis Otto](https://github.com/Dennis-Otto) baut und pflegt jedes Projekt auf dieser Website, öffentlich und unter Open-Source-Lizenzen. Er liest jedes Issue, prüft die Pull Requests anderer, entscheidet, was als Nächstes kommt, und beantwortet die Meldungen von Sicherheitslücken; Bots erledigen die Routinearbeit, jeder mit den geringsten Rechten, die er braucht.

## Warum es sie gibt { #why }

Die Projekte verbinden Werkzeuge, die Menschen zu Hause und bei der Arbeit schon nutzen: ein Autodarts-Board oder jede andere Dartscheibe mit Home Assistant, das Dokumentenarchiv von Paperless-ngx mit Nextcloud, und die Issues und Releases eines Repositorys mit Bots, die sich darum kümmern. Jedes soll so verlässlich sein wie die Arbeit eines Teams, mit einem Menschen dahinter: Tests für jede Änderung, signierte Releases, die jeder prüfen kann, Sicherheitsprüfungen, eine eigene Website und eine erste Antwort auf jedes Issue. Die Seite [Vertrauen](trust.md) zeigt, was jedes Projekt garantiert.

## Eine Suche für jedes Projekt { #search }

Die Suche oben auf jeder Seite findet auch die Seiten der Website jedes Projekts: *token* findet das API-Token von Paperless Unified Search, die versiegelten Tokens von Player Switch und das Token des Superusers in Paperless Sync, jedes unter dem kurzen Namen seines Projekts, und ein Ergebnis öffnet die Seite auf der Website seines Projekts. Bei reduzierter Bewegung zeigt das Bild nur die Ergebnisse.

<!-- The website shows the picture of its color scheme, by #only-light and #only-dark, and the still of the last frame to a reader who prefers reduced motion. scripts/screenshots.sh takes them; this page gets the pictures of the German home page, search-*.de.webp, at the addresses of the English ones. -->

<picture>
  <source media="(prefers-reduced-motion: reduce)" srcset="images/search-still-light.webp">
  <img src="images/search-light.webp#only-light" class="off-glb" width="1280" height="800" alt="Animation: die Suche von dennis-otto.github.io. Auf der deutschen Startseite klickt jemand in das Suchfeld oben und tippt token, Buchstabe für Buchstabe. Mit jedem Buchstaben ändert sich die Liste der Ergebnisse unter dem Feld, und für token zeigt sie die passenden Seiten der Websites mehrerer Projekte, jeder Titel beginnt mit dem kurzen Namen seines Projekts, und das Wort Token ist in jedem hervorgehoben. Dann wählt die Pfeiltaste das erste Ergebnis.">
</picture>
<picture>
  <source media="(prefers-reduced-motion: reduce)" srcset="images/search-still-dark.webp">
  <img src="images/search-dark.webp#only-dark" class="off-glb" width="1280" height="800" alt="Animation: die Suche von dennis-otto.github.io. Auf der deutschen Startseite klickt jemand in das Suchfeld oben und tippt token, Buchstabe für Buchstabe. Mit jedem Buchstaben ändert sich die Liste der Ergebnisse unter dem Feld, und für token zeigt sie die passenden Seiten der Websites mehrerer Projekte, jeder Titel beginnt mit dem kurzen Namen seines Projekts, und das Wort Token ist in jedem hervorgehoben. Dann wählt die Pfeiltaste das erste Ergebnis.">
</picture>

## Wie sie entstehen { #how }

Jedes Repository entsteht aus einer Vorlage, [Repo Blueprint](https://dennis-otto.github.io/repo-blueprint/de/): dieselben Prüfungen, Workflows, Einstellungen und Richtlinien in jedem, für jede Art von Projekt. Was ein Repository lernt, bringt der Blueprint zu allen.

- **Ein Blueprint.** Eine Änderung am Blueprint, etwa eine schnellere Prüfung oder eine neue Sicherheitskontrolle, wird zu einem Release des Blueprints, und sein Bot bringt dieses Release als Pull Request in jedes Repository, der die Prüfungen dieses Repositorys besteht wie jede andere Änderung.
- **Releases.** Der Release-Bot macht aus den Titeln der gemergten Pull Requests die nächste Version und ihr Changelog, baut, signiert und veröffentlicht dann das Release, und ein Workflow prüft es so, wie seine Nutzer es können.
- **Updates.** Renovate hält die Abhängigkeiten, die Actions und die Images aktuell, eine Woche nach ihrem Release, oder sofort, wenn ein Update eine Sicherheitslücke behebt.
- **Triage.** Der [Issue assistant](https://dennis-otto.github.io/issue-assistant/) gibt einem neuen Issue eine erste Analyse durch eine KI, die nur liest, vergibt seine Labels, findet Duplikate, erinnert an offene Fragen und schließt ein Issue, sobald ein Release seinen Fix ausliefert.
- **Einstellungen.** Der Settings-Bot wendet die Einstellungen jedes Repositorys, etwa die Regeln seines `main`, nach jeder Änderung und jede Woche aus einer Datei des Repositorys an, sodass sich eine Einstellung nur in einem geprüften Pull Request ändert.
- **Hilfe in Pull Requests.** Jede Prüfung erklärt sich, wenn sie fehlschlägt: was sie gefunden hat, warum das wichtig ist und wie es sich beheben lässt, und ein Bot macht jeden Fix, den ein Befehl machen kann.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/from-a-change-to-a-release.de.dark.svg">
  <img src="images/diagrams/from-a-change-to-a-release.de.svg" alt="Von einer Änderung zum Release in jedem Repository: Eine Änderung am Blueprint, ein Pull Request eines Menschen, von Renovate oder eines Bots, erreicht main nur über jede Pflichtprüfung. Der Release-Bot des Blueprints macht daraus ein Release mit einem signierten Tag, Provenienz und SBOMs, das sich nach der Veröffentlichung nicht mehr ändern kann. Der Blueprint-Bot jedes Projekts prüft dieses Release und öffnet einen Pull Request damit, der jede Pflichtprüfung des Projekts besteht, wie die eigenen Pull Requests des Projekts. Der Release-Bot des Projekts veröffentlicht dann ein eigenes signiertes, unveränderliches Release. Ein Workflow prüft jedes Release so, wie seine Nutzer es können, nach jedem Release und jede Woche, der Issue assistant schließt die Issues, die das Release behebt, und die Nutzer bekommen das Release, das diese Website zeigt.">
</picture>

[Automatisierung](automation.md) listet jeden Workflow dieses Repositorys mit dem, was er tut, und das [Dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) zeigt den Zustand jedes Repositorys auf einen Blick.

## Entscheidungen { #decisions }

Die Entscheidungen, die ein Projekt prägen, sind mit ihren Gründen aufgeschrieben, damit eine spätere Änderung sieht, warum die Dinge so sind, wie sie sind. Die [Entscheidungen dieser Website](decisions/README.md) erklären auf Englisch, wie sie die ganze Adresse bedient und woher ihre Live-Fakten kommen, und die [des Blueprints](https://github.com/Dennis-Otto/repo-blueprint/blob/main/docs/decisions/README.md) prägen jedes Repository.

## Unterstützen { #support }

Die Projekte sind kostenlos und Open Source. Wenn sie dir nützen, kannst du ihre Entwicklung über GitHub Sponsors unterstützen.

[:octicons-heart-16: Unterstützen](https://github.com/sponsors/Dennis-Otto){ .md-button .md-button--primary }

## Kontakt { #contact }

Fragen, Probleme und Ideen zu einem Projekt gehören in die Issues seines Repositorys: Die [Issue-Auswahl dieser Website](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/new/choose) führt zu denen jedes Projekts und hat die Formulare für die Website selbst. Melde eine Sicherheitslücke bitte vertraulich, wie [Vertrauen](trust.md#report-a-vulnerability) beschreibt. Alles andere erreicht Dennis über [sein Profil auf GitHub](https://github.com/Dennis-Otto).
