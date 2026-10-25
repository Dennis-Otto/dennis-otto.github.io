# Dennis Otto

[English](README.md) · **Deutsch**

[![Website](https://img.shields.io/badge/website-dennis--otto.github.io-526cfe?logo=materialformkdocs&logoColor=white)](https://dennis-otto.github.io/de/)
[![CI](https://github.com/Dennis-Otto/dennis-otto.github.io/actions/workflows/ci.yml/badge.svg)](https://github.com/Dennis-Otto/dennis-otto.github.io/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Dennis-Otto/dennis-otto.github.io/badge)](https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/dennis-otto.github.io)
[![REUSE](https://api.reuse.software/badge/github.com/Dennis-Otto/dennis-otto.github.io)](https://api.reuse.software/info/github.com/Dennis-Otto/dennis-otto.github.io)
[![Lizenz: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Sponsern](https://img.shields.io/badge/sponsor-%E2%99%A5-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Dennis-Otto)

<a href="https://dennis-otto.github.io/de/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/website-dark.de.webp">
    <img src="docs/images/website-light.de.webp" alt="Die deutsche Startseite von dennis-otto.github.io: ein dunkelblauer Kopfbereich mit dem Monogramm DO, dem Namen Dennis Otto, drei Sätzen über die Projekte, deren letzter sagt, dass die Suche oben die Seiten aller Projekte findet, und den Buttons Zu den Projekten und Unterstützen, darunter die erste Gruppe der Projekte, Für das smarte Zuhause und das Dokumentenarchiv, mit den Karten von HomeDarts for Autodarts, Player Switch for Autodarts und Paperless Sync, jede mit einem deutschen Bild des Projekts; die Karte von Paperless Unified Search folgt darunter, außerhalb des Bildes.">
  </picture>
</a>

Die Website aller Projekte von Dennis Otto, unter [dennis-otto.github.io/de](https://dennis-otto.github.io/de/): eine Seite mit jedem Projekt, seinem Button zum Installieren und seiner Dokumentation, auf Deutsch und auf Englisch.

<sub>💛 Wenn dir die Projekte nützen, kannst du [ihre Entwicklung unterstützen](https://github.com/sponsors/Dennis-Otto).</sub>

## Die Projekte

<!-- projects:start -->

| Projekt | Was es tut | Funktioniert mit | Start | Website |
| --- | --- | --- | --- | --- |
| [homedarts-for-autodarts](https://github.com/Dennis-Otto/homedarts-for-autodarts) | HomeDarts for Autodarts: Autodarts-Boards in Home Assistant, lokal und in Echtzeit | Home Assistant ([hacs.json](https://github.com/Dennis-Otto/homedarts-for-autodarts/blob/HEAD/hacs.json)) | [Mit HACS installieren](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=homedarts-for-autodarts&category=integration) | [dennis-otto.github.io/homedarts-for-autodarts/de](https://dennis-otto.github.io/homedarts-for-autodarts/de/) · [dennis-otto.github.io/homedarts-for-autodarts](https://dennis-otto.github.io/homedarts-for-autodarts/) |
| [player-switch-for-autodarts](https://github.com/Dennis-Otto/player-switch-for-autodarts) | Ein gemeinsames Autodarts-Display, jeder im eigenen Konto, ein Tipp zum Wechseln | Google Chrome auf dem Desktop | [Installieren](https://github.com/Dennis-Otto/player-switch-for-autodarts#quick-start) | [dennis-otto.github.io/player-switch-for-autodarts/de](https://dennis-otto.github.io/player-switch-for-autodarts/de/) · [dennis-otto.github.io/player-switch-for-autodarts](https://dennis-otto.github.io/player-switch-for-autodarts/) |
| [paperless-sync](https://github.com/Dennis-Otto/paperless-sync) | Dokumente aus Paperless-ngx als Archiv in Nextcloud | Nextcloud ([appinfo/info.xml](https://github.com/Dennis-Otto/paperless-sync/blob/HEAD/appinfo/info.xml)) | [Nextcloud App Store](https://apps.nextcloud.com/apps/paperless_sync) | [dennis-otto.github.io/paperless-sync/de](https://dennis-otto.github.io/paperless-sync/de/) · [dennis-otto.github.io/paperless-sync](https://dennis-otto.github.io/paperless-sync/) |
| [paperless-unified-search](https://github.com/Dennis-Otto/paperless-unified-search) | Die Suche von Paperless-ngx in der Suche von Nextcloud | Nextcloud ([appinfo/info.xml](https://github.com/Dennis-Otto/paperless-unified-search/blob/HEAD/appinfo/info.xml)) | [Nextcloud App Store](https://apps.nextcloud.com/apps/paperless_unified_search) | [dennis-otto.github.io/paperless-unified-search/de](https://dennis-otto.github.io/paperless-unified-search/de/) · [dennis-otto.github.io/paperless-unified-search](https://dennis-otto.github.io/paperless-unified-search/) |
| [issue-assistant](https://github.com/Dennis-Otto/issue-assistant) | Eine GitHub Action, die sich um Issues kümmert | GitHub Actions und Claude, Codex, Gemini oder Copilot | [Action einsetzen](https://github.com/Dennis-Otto/issue-assistant#set-up-a-repository) | [dennis-otto.github.io/issue-assistant](https://dennis-otto.github.io/issue-assistant/) |
| [repo-blueprint](https://github.com/Dennis-Otto/repo-blueprint) | Die Vorlage, aus der all diese Repositorys entstehen | Copier ([copier.yml](https://github.com/Dennis-Otto/repo-blueprint/blob/HEAD/copier.yml)) | [Repository anlegen](https://github.com/Dennis-Otto/repo-blueprint/blob/main/README.de.md#ein-repository-anlegen) · [Start a repository](https://github.com/Dennis-Otto/repo-blueprint#start-a-repository) | [dennis-otto.github.io/repo-blueprint/de](https://dennis-otto.github.io/repo-blueprint/de/) · [dennis-otto.github.io/repo-blueprint](https://dennis-otto.github.io/repo-blueprint/) |
| Repository-Dashboard | Der Zustand aller Repositorys auf einen Blick | — | [Dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) | — |

<!-- projects:end -->

[dennis-otto.github.io/dashboard](https://dennis-otto.github.io/dashboard/) ist die kurze Adresse des [Dashboards aller Repositorys](https://dennis-otto.github.io/repo-blueprint/dashboard/), das der Blueprint baut.

## Eine Liste der Projekte

Jedes Projekt steht einmal in [projects.toml](projects.toml): seine Gruppe, sein Name, seine Texte, sein Bild und seine Links, auf Englisch und auf Deutsch. Während MkDocs die Website baut, setzen die Hooks in [.github/mkdocs_project.py](.github/mkdocs_project.py) die Gruppen mit einer Karte für jedes Projekt in beide Startseiten, in der Sprache der Seite. Dieselbe Datei schreibt die Tabelle oben, zwischen ihren beiden Markierungen, und die englische in [README.md](README.md):

```sh
python3 -I .github/mkdocs_project.py --write
```

Die Tabelle dieser Datei zeigt die deutschen Texte und die deutschen Adressen zuerst, die englische die englischen; beide halten jede Adresse von projects.toml, damit der Link-Check, der die Markdown-Dateien liest, auch die Buttons der Karten prüft. `bash scripts/check.sh` schlägt fehl, wenn eine der beiden Tabellen von projects.toml abweicht, und in einem Pull Request [repariert sich eine abweichende Tabelle selbst](README.md#the-checks-of-this-website).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/diagrams/one-list-of-the-projects.de.dark.svg">
  <img src="docs/images/diagrams/one-list-of-the-projects.de.svg" alt="Eine Liste der Projekte: projects.toml nennt jedes Projekt einmal. Während MkDocs die Website baut, machen die Hooks der Website daraus die Gruppen und Karten der englischen und der deutschen Startseite, die strukturierten Daten der Startseite, die 404-Seite der ganzen Adresse sowie robots.txt, security.txt und llms.txt. Mit --write machen sie daraus die Tabellen von README.md auf Englisch und README.de.md auf Deutsch, und scripts/check.sh prüft mit --check, dass beide aktuell sind. Mit --pictures listen sie die Bilder der Karten, die scripts/project-pictures.sh aus der Social Preview jedes Repositorys macht.">
</picture>

Wie die Website sonst funktioniert, von der Suche über alle Projekte bis zur Trust-Seite, beschreibt [README.md](README.md#how-the-website-works) auf Englisch.

## Die Website ansehen

Die Seiten liegen in [docs/](docs/), jede deutsche als `NAME.de.md` neben ihrer englischen, wie `index.de.md` neben `index.md`. MkDocs mit dem Material-Theme baut sie, und der Docs-Workflow veröffentlicht die Website mit jeder Änderung von `main` auf GitHub Pages. Beim Schreiben zeigt sie dir eine Vorschau unter <http://127.0.0.1:8000>, mit den Werkzeugen des Docs-Workflows in einer eigenen virtuellen Umgebung, `.venv-docs`, die git ignoriert:

```sh
python3 -m venv .venv-docs
.venv-docs/bin/pip install --require-hashes -r .github/docs-requirements.txt
.venv-docs/bin/mkdocs serve
```

Unter Windows, in PowerShell:

```powershell
py -3 -m venv .venv-docs
.venv-docs\Scripts\pip install --require-hashes -r .github/docs-requirements.txt
.venv-docs\Scripts\mkdocs serve
```

## Mitmachen

Jede Änderung kommt über einen Pull Request, dessen Titel [Conventional Commits](https://www.conventionalcommits.org/) folgt, mit abgezeichneten Commits (`git commit -s`). Die Prüfungen der CI laufen lokal mit

```sh
bash scripts/check.sh
```

[CONTRIBUTING.md](CONTRIBUTING.md) erklärt auf Englisch die Einrichtung und die Regeln, und [README.md](README.md#development) die Prüfungen dieser Website.

## Hilfe und Sicherheit

Eine Frage, ein Problem oder eine Idee zu einem Projekt gehört in die Issues seines eigenen Repositorys, das die Tabelle oben verlinkt; die Issues dieses Repositorys sind für die Website selbst. Sicherheitslücken meldest du vertraulich, wie es [SECURITY.md](SECURITY.md) beschreibt; die [Sicherheitsseite](https://dennis-otto.github.io/de/security.html) verlinkt das Formular für vertrauliche Meldungen jeder Website der Adresse.

## Lizenz

MIT; siehe [LICENSE](LICENSE). Jede Datei nennt ihre Lizenz in der maschinenlesbaren Form von [REUSE](https://reuse.software).
