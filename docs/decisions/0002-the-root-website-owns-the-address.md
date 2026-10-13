# This repository serves the root of the address for every website there

- Status: accepted
- Date: 2026-10-13

## Context

GitHub Pages gives an account one address, `dennis-otto.github.io`. It serves the website of the repository named after the address at its root, and the website of every other repository in a folder named after it, such as `/ha-autodarts/`. This repository and those of the projects publish there, each with its own Docs workflow.

Some files count at the root of an address alone:

- Crawlers read `/robots.txt` and nothing in a folder ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309)).
- Security researchers look for `/.well-known/security.txt` ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)).
- Browsers and phones ask the root for `/favicon.ico` and `/apple-touch-icon.png` when what they show names no icon of its own, such as a picture or a PDF opened by itself.
- GitHub Pages answers an address that no website serves, such as a mistyped project, with the 404 page of the root.
- Search engines take the name of a website from the home page at the root, for every page below it.

The repository of a project can't publish a file outside its folder. And the projects were written by hand three times, on the cards of both home pages and in the table of the README, which had drifted apart already.

## Options

1. Let every project serve these files in its own folder. Nothing reads them there: crawlers and researchers find no file, browsers get a 404 page for the icon, and a mistyped address meets the bare 404 page of GitHub.
2. Let the blueprint give every repository the same files. They would still land in folders, as in option 1.
3. Let this repository serve every file of the root for every website at the address, built from one list of the projects, so that a new project reaches each of them without another edit.

## Decision

Option 3. This repository serves the root of the address for every website at `dennis-otto.github.io`: `robots.txt` with the sitemap of each of them, `security.txt` at both of its places, the icons, the 404 page with every project and the structured data of the home page. [projects.toml](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/projects.toml) is the one list of the projects. While MkDocs builds the website, the hooks in `.github/mkdocs_project.py` make the cards, the 404 page, `robots.txt`, `security.txt` and the structured data from it, and the table of the README is written from it and checked against it.

## Consequences

- A new project is an entry in projects.toml, the picture of its card and the table of the README. A few lists still name the projects by hand, and the tests check them against projects.toml: the websites and the private report forms on the security page in both languages, and the links of the issue chooser. No text says how many websites there are, which a test checks, so a new project changes neither the texts nor this record. The checklist [Add a project](https://github.com/Dennis-Otto/dennis-otto.github.io#add-a-project) of the README lists every place.
- A mistake here reaches every website of the address: a `robots.txt` that shut crawlers out would hide all of them, and a service worker registered at the root could control every page of them, so the website registers none, as its [security page](../security.md) says. The strict build of the website and the tests of the hooks, with every line and branch covered, guard the files.
- `security.txt` expires a year after the build that wrote it, so the website must be built anew at least once a year, by any change of `main` or by running the Docs workflow.
- The websites of the projects keep their own 404 pages and sitemaps, which serve their folders; the root names their sitemaps but never builds their pages.
