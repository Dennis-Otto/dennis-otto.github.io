# Dennis Otto

[![Website](https://img.shields.io/badge/website-dennis--otto.github.io-526cfe?logo=materialformkdocs&logoColor=white)](https://dennis-otto.github.io/)
[![CI](https://github.com/Dennis-Otto/dennis-otto.github.io/actions/workflows/ci.yml/badge.svg)](https://github.com/Dennis-Otto/dennis-otto.github.io/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Dennis-Otto/dennis-otto.github.io/badge)](https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/dennis-otto.github.io)
[![REUSE](https://api.reuse.software/badge/github.com/Dennis-Otto/dennis-otto.github.io)](https://api.reuse.software/info/github.com/Dennis-Otto/dennis-otto.github.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-%E2%99%A5-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Dennis-Otto)

The website of all projects of Dennis Otto, at [dennis-otto.github.io](https://dennis-otto.github.io/): one page with every project, its install button and its documentation, in English and German.

<sub>💛 If the projects are useful to you, you can [support their development](https://github.com/sponsors/Dennis-Otto).</sub>

## The projects

<!-- projects:start -->

| Project | What it does | Start | Website |
| --- | --- | --- | --- |
| [ha-autodarts](https://github.com/Dennis-Otto/ha-autodarts) | Autodarts for Home Assistant, local and in realtime | [Install with HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=ha-autodarts&category=integration) | [dennis-otto.github.io/ha-autodarts](https://dennis-otto.github.io/ha-autodarts/) · [dennis-otto.github.io/ha-autodarts/de](https://dennis-otto.github.io/ha-autodarts/de/) |
| [paperless-sync](https://github.com/Dennis-Otto/paperless-sync) | Paperless-ngx documents as an archive in Nextcloud | [Nextcloud App Store](https://apps.nextcloud.com/apps/paperless_sync) | [dennis-otto.github.io/paperless-sync](https://dennis-otto.github.io/paperless-sync/) |
| [paperless-unified-search](https://github.com/Dennis-Otto/paperless-unified-search) | The search of Paperless-ngx in the search of Nextcloud | [Nextcloud App Store](https://apps.nextcloud.com/apps/paperless_unified_search) | [dennis-otto.github.io/paperless-unified-search](https://dennis-otto.github.io/paperless-unified-search/) |
| [issue-assistant](https://github.com/Dennis-Otto/issue-assistant) | A GitHub Action that looks after issues | [Use the action](https://github.com/Dennis-Otto/issue-assistant#set-up-a-repository) | [dennis-otto.github.io/issue-assistant](https://dennis-otto.github.io/issue-assistant/) |
| [repo-blueprint](https://github.com/Dennis-Otto/repo-blueprint) | The template all of these repositories are made from | [Start a repository](https://github.com/Dennis-Otto/repo-blueprint#start-a-repository) · [Repository anlegen](https://github.com/Dennis-Otto/repo-blueprint/blob/main/README.de.md#ein-repository-anlegen) | [dennis-otto.github.io/repo-blueprint](https://dennis-otto.github.io/repo-blueprint/) · [dennis-otto.github.io/repo-blueprint/de](https://dennis-otto.github.io/repo-blueprint/de/) |
| Repository dashboard | The state of every repository at a glance | [Dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) | — |

<!-- projects:end -->

[dennis-otto.github.io/dashboard](https://dennis-otto.github.io/dashboard/) is the short address of the [dashboard of every repository](https://dennis-otto.github.io/repo-blueprint/dashboard/), which the blueprint builds.

## How the website works

The pages are in [docs/](docs/): `index.md` in English, `index.de.md` in German, `security.md` with the decision records it links, and `dashboard/index.html`, which forwards to the dashboard. MkDocs with the Material theme builds them, and the Docs workflow publishes the website on GitHub Pages with every change of `main`. Preview it while you write with

```sh
pip install --require-hashes -r .github/docs-requirements.txt && mkdocs serve
```

The repository comes from the [blueprint](https://github.com/Dennis-Otto/repo-blueprint), whose bot keeps it current.

### The home page

Both home pages name [overrides/home.html](overrides/home.html) as their template. It shows the hero, on the navy of the social previews of the projects: the monogram, the name, a lead sentence and two buttons, *See the projects* and *Sponsor*. The texts of the hero come from the front matter of each page, under `hero:`, so that every language has its own. A landing page has no pencil that edits it, no date of its last change, no menu at its side and no footer that leads to the next page.

Below the hero, the projects stand in groups by their readers, each under a heading of its own: *For the smart home and the document archive* and *For maintainers on GitHub*. Each card has a picture of the project, its name, which links its website, a summary and two buttons, both on one line on a phone: where to start, such as *Install with HACS*, and its documentation. The card of the blueprint leads to the dashboard instead, since its name links the documentation already. A sentence under the Paperless cards explains how the two apps work together. The page loads no diagram: the script of Mermaid would weigh about 1 MB on the most visited page.

### One list of the projects

Every project is written once, in [projects.toml](projects.toml): its group, its name, its texts, its picture and its links, in English and German. While MkDocs builds the website, the hooks in [.github/mkdocs_project.py](.github/mkdocs_project.py) put the groups with a card for each project in place of the line `<!-- projects -->` of both home pages, in the language of the page. The same file writes the table of the projects above, between its two markers:

```sh
python3 -I .github/mkdocs_project.py --write
```

A new project is a new `[[project]]` in projects.toml with its group, then `bash scripts/project-pictures.sh` for its picture and this command; the comments at the top of the file describe every key, and [the catalog bot](#the-catalog-bot) opens an issue for a project with a website at the address that the file lacks. A project without a group, such as the dashboard, has no card of its own: another card names it as its `second` button, and the check fails for a project that no card shows. The same list makes the 404 page, the sitemaps of robots.txt and the structured data of the home page, which [the root of the address](#the-root-of-the-address) describes, so a new project appears there without another edit. The table holds every address of projects.toml, the German ones too, so that the link check, which reads the Markdown files, checks the buttons of the cards as well. `bash scripts/check.sh` fails when the table differs from projects.toml or a project lacks a German text, and the strict build of the website fails when a page or a title of the menu has no German translation.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 400
---
flowchart TB
    accTitle: One list of the projects
    accDescr: projects.toml lists every project once. While MkDocs builds the website, the hooks of the website turn it into the groups and cards of the English and the German home page, the structured data of the home page, the 404 page of the whole address, and robots.txt and security.txt. With --write they turn it into the table of README.md, and scripts/check.sh checks with --check that the table is current. With --pictures they list the pictures of the cards, which scripts/project-pictures.sh makes from the social preview of each repository.

    catalog[("projects.toml")]
    hooks[".github/mkdocs_project.py"]
    build(["mkdocs build"])
    cards["The groups and cards of the home page<br>English · German"]
    data["The structured data<br>of the home page"]
    notfound["The 404 page<br>of the whole address"]
    root["robots.txt and<br>security.txt"]
    table["The table of README.md"]
    check(["scripts/check.sh"])
    pictures(["scripts/project-pictures.sh"])
    previews[".github/social-preview.png<br>of every repository"]
    images["docs/images/projects/<br>a WebP of 640×320 per card"]

    catalog --> hooks
    hooks --> build
    build --> cards & data & notfound & root
    hooks -- "<code>--write</code>" --> table
    check -. "<code>--check</code>" .-> table
    hooks -- "<code>--pictures</code>" --> pictures
    previews --> pictures
    pictures --> images
    images --> cards

    classDef bot fill:#526cfe2e,stroke:#526cfe,stroke-width:2px
    classDef person fill:#f59e0b2e,stroke:#f59e0b,stroke-width:2px
    classDef done fill:#16a34a2e,stroke:#16a34a,stroke-width:2px
    class build,check bot
    class pictures person
    class cards,data,notfound,root,table,images done
```

### The catalog bot

The projects change without this repository: a new one gets its website at `dennis-otto.github.io`, another one translates its documentation, a third is renamed or archived. So every Monday the Catalog workflow, [.github/workflows/catalog.yml](.github/workflows/catalog.yml), compares projects.toml with GitHub and with the websites of the projects, and finds:

- a public repository of the owner with its website in a folder of `dennis-otto.github.io` that has no project in projects.toml;
- a project whose repository was renamed, archived, made private or deleted, or names another website on GitHub;
- a German website that appeared, such as `…/paperless-sync/de/`, while the German home page still leads to the English one, and a German website of projects.toml that answers 404.

It keeps one issue, *The project catalog is out of date*, with what it found and how to fix it, and closes the issue once a run finds projects.toml current. It needs no AI, commits nothing and may only read the repository and write issues; projects.toml stays a change that a person makes and reviews. The comparison needs the standard library alone, so it runs locally too, with the list of the repositories that gh writes:

```sh
gh repo list Dennis-Otto --limit 1000 --json nameWithOwner,homepageUrl,isArchived,isPrivate >repositories.json
python3 -I .github/mkdocs_project.py --network repositories.json
```

```mermaid
flowchart TB
    accTitle: The catalog bot
    accDescr: Every Monday, or when started by hand, the Catalog workflow lists the repositories of the owner with gh and asks every website of a project at dennis-otto.github.io for its German version. .github/mkdocs_project.py --network compares both with projects.toml. When something differs, the bot opens or updates the issue The project catalog is out of date, and a person changes projects.toml and writes the table of the README. When nothing differs, the bot closes the issue.

    week(["Every Monday<br>or by hand"])
    repos["gh repo list<br>the repositories of the owner"]
    sites["The website of every project<br>and its folder de/"]
    catalog[("projects.toml")]
    compare[".github/mkdocs_project.py<br><code>--network</code>"]
    issue["The issue<br><i>The project catalog is out of date</i>"]
    fix(["A person changes projects.toml<br>and runs <code>--write</code>"])
    closed["The issue closes"]

    week --> repos & sites
    repos & sites & catalog --> compare
    compare -- "something differs" --> issue
    issue --> fix
    fix -.-> catalog
    compare -- "nothing differs" --> closed

    classDef bot fill:#526cfe2e,stroke:#526cfe,stroke-width:2px
    classDef person fill:#f59e0b2e,stroke:#f59e0b,stroke-width:2px
    classDef done fill:#16a34a2e,stroke:#16a34a,stroke-width:2px
    class week,repos,sites,compare bot
    class issue,fix person
    class closed done
```

### Pictures and icons

The pictures of the website come from scripts, so that a new one is a command away and the same input makes the same file, byte for byte. The first two need Pillow from the tools of the website in `.venv-docs`, which [CONTRIBUTING.md](CONTRIBUTING.md#website) sets up, and the last two need Docker.

| Command | What it makes |
| --- | --- |
| `bash scripts/project-pictures.sh` | The picture of every card with a repository, from the social preview of that repository on `main`: a WebP of 640×320 pixels, about 15 KB, in `docs/images/projects/`, with a `.license` file beside it that names the license of the repository for REUSE. Run it when a project has a new social preview, and describe the new picture in its `alt` texts. |
| `bash scripts/icons.sh` | `docs/favicon.ico` with 16, 32 and 48 pixels and `docs/apple-touch-icon.png` with 180, from the monogram in [docs/assets/logo.svg](docs/assets/logo.svg), which is the logo of the header and the icon of the browser tab too. Browsers ask the root of the address for both, for every website at `dennis-otto.github.io`. It renders [.github/icons.html](.github/icons.html) with the Chromium of Playwright in Docker. |
| `bash scripts/social-preview.sh` | `.github/social-preview.png`, the picture of links to this repository, from [.github/social-preview.html](.github/social-preview.html): the monogram and a collage of the pictures of the projects. Upload it under *Settings → General → Social preview*. |

[REUSE.toml](REUSE.toml) gives every file the MIT license of this repository, and REUSE adds that license to the one of a `.license` file instead of replacing it. So `reuse spdx` names both licenses for each picture of a project, until the blueprint, which owns REUSE.toml, lets a `.license` file win.

### The root of the address

The websites of the projects live in folders of the same address, such as `dennis-otto.github.io/ha-autodarts/`, and each is built by the repository of its project. Crawlers, browsers and security researchers look for some files at the root of an address alone, and only this repository can serve them there. So while MkDocs builds the website, the hooks in [.github/mkdocs_project.py](.github/mkdocs_project.py) write them for all six websites:

| At the root | What it does |
| --- | --- |
| `/robots.txt` | Lets every crawler in and names the sitemap of every website of the address: this one, and that of each project of projects.toml whose documentation is at `dennis-otto.github.io`. |
| `/.well-known/security.txt` and `/security.txt` | Tell security researchers how to report a vulnerability of any of the websites privately, as [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116) describes, and link the [security page](https://dennis-otto.github.io/security.html). The file expires a year after the build, and every change of `main` builds it anew. GitHub Pages publishes the copy under `/.well-known/` once the Docs workflow of the blueprint uploads folders whose names start with a dot. |
| `/favicon.ico` and `/apple-touch-icon.png` | The icons that browsers and phones ask the root of an address for, which [Pictures and icons](#pictures-and-icons) describes. |
| The 404 page | Answers every address that leads nowhere outside the websites of the projects, which have 404 pages of their own: in English and German, with every project, the home page and, for a mistyped project such as `/autodarts/`, *Did you mean Autodarts for Home Assistant?* Its template is [overrides/404.html](overrides/404.html). |
| The structured data of the home page | Search engines take the name of a website from the home page at the root of an address alone, for every page below it. The English home page names the website, its owner and every project with its repository, license and platform, as JSON-LD. Its canonical address, the links between its languages and the sitemaps give the root of the address, `https://dennis-otto.github.io/`, as the website does, rather than `index.html` in it. |

## Development

Every change goes through a pull request whose title follows [Conventional Commits](https://www.conventionalcommits.org/), with signed-off commits (`git commit -s`). The checks of the CI run locally with

```sh
bash scripts/check.sh
```

[CONTRIBUTING.md](CONTRIBUTING.md) explains the set-up and the rules.

## Support and security

A question, a problem or an idea about a project belongs to the issues of its own repository, which the table above links. The [issue chooser](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/new/choose) of this repository links each project's issues too; its own two forms are for the website itself, a problem with a page or an idea for it. The documentation of a project, under `dennis-otto.github.io/<project>/`, is built by the project's repository, and its issues take reports about it. [SUPPORT.md](SUPPORT.md) says what happens with an issue. Report vulnerabilities privately, as [SECURITY.md](SECURITY.md) describes.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 400
---
flowchart TB
    accTitle: Where an issue goes
    accDescr: The issue chooser of this repository sends a question, a problem or an idea about a project to the issues of that project's own repository. A problem with the website or an idea for it stays here, and a vulnerability goes to a private security advisory. In both repositories, the issue assistant posts a first analysis and the Area field of the form chooses the area label.

    you(["You: a question,<br>a problem or an idea"])
    chooser{"New issue in<br>dennis-otto.github.io"}
    project["The issues of its repository:<br>ha-autodarts, paperless-sync,<br>paperless-unified-search,<br>issue-assistant or repo-blueprint"]
    website["Problem with the website<br>or Idea for the website"]
    advisory["A private<br>security advisory"]
    assistant(["Issue assistant:<br>first analysis and area label"])

    you --> chooser
    chooser -- "about a project" --> project
    chooser -- "about the website" --> website
    chooser -- "a vulnerability" --> advisory
    project & website --> assistant

    classDef bot fill:#526cfe2e,stroke:#526cfe,stroke-width:2px
    classDef person fill:#f59e0b2e,stroke:#f59e0b,stroke-width:2px
    classDef done fill:#16a34a2e,stroke:#16a34a,stroke-width:2px
    class assistant bot
    class you person
    class project,website,advisory done
```

## License

MIT; see [LICENSE](LICENSE). Every file names its license in the machine-readable form of [REUSE](https://reuse.software).
