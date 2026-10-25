# Changelog

All notable changes, by release. Each pull request that changes something for
users describes it under Unreleased. The release bot makes that text the section of
the next release, or lists the pull requests when there is none.

## Unreleased

## [1.4.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.3.0...v1.4.0) (2026-10-25)


### Features

* a Releases page with the notes of every project, and What's new names all of them ([#75](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/75)) ([ffc86e0](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/ffc86e02009d5c8a1cbf119ac524fd9c0be3d122))
* **pictures:** renew the card pictures from the projects' social previews automatically ([#87](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/87)) ([44a2dbe](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/44a2dbe87d67fa7c95835f48bb44de2f229a25e3))
* show on every card what a project works with, read from its latest release ([#77](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/77)) ([39858f4](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/39858f437bc499377b41bd089e2838ff887425bf))


### Bug fixes

* **search:** find the installation, guide and German pages of every project in the search of the hub ([#72](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/72)) ([53afb6f](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/53afb6f7d46903f0e4f41418d6f97430f65df765))
* **trust:** make the Trust page readable on a phone without sideways scrolling ([#79](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/79)) ([736642b](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/736642b56d97fd530c7eb9231c33fc4c9293e4cf))

## [1.3.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.2.0...v1.3.0) (2026-10-23)

### Features

- **Player Switch for Autodarts on the home page:** the Chrome extension that switches the players of a shared Autodarts display with one tap has its card in *For the smart home and the document archive*, next to HomeDarts for Autodarts, with its picture, its install button and its website in English and German. The Trust page shows its guarantees and the commands that check its latest release, the search finds the pages of its website, robots.txt names its sitemap, the 404 page suggests it for an address like its own, and the security page and the issue forms of this website lead to its repository.

### Bug fixes

- **The German websites of Paperless Sync and Paperless Unified Search:** the German home page and the German security page led to the English websites of both apps, which have German websites now; their cards, the table of the README and the security page lead to [dennis-otto.github.io/paperless-sync/de/](https://dennis-otto.github.io/paperless-sync/de/) and [dennis-otto.github.io/paperless-unified-search/de/](https://dennis-otto.github.io/paperless-unified-search/de/).

## [1.2.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.1.0...v1.2.0) (2026-10-21)

### Features

- **HomeDarts for Autodarts, the new name of Autodarts for Home Assistant:** at the request of Autodarts, the integration has a name and an icon of its own: HomeDarts for Autodarts, an unofficial community project for Autodarts boards and any other dartboard. Its card shows the new name, picture and install button, and the Trust page, the security page, the search and the issue forms name it and its new website, [dennis-otto.github.io/homedarts-for-autodarts](https://dennis-otto.github.io/homedarts-for-autodarts/). Every old address keeps working: a page under `dennis-otto.github.io/ha-autodarts/`, such as `/ha-autodarts/de/games.html#cricket`, leads to the same page and section of the new website, any other address there, such as that of a picture, to the same path, and `dennis-otto.github.io/#ha-autodarts` still to the card.

## [1.1.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.0.0...v1.1.0) (2026-10-19)

### Features

- **The numbers of every project on its card, and what's new:** the home page said in one sentence that the projects come with tests and checks, without a number. Every card of a project now shows its latest release and how long ago it came out, the share of its code that its tests run, its mutation score, its OpenSSF Scorecard, the median time to the first answer by a person to a new issue when there is one, and the level of its OpenSSF Best Practices, such as *v1.17.0 · released today · 100% test coverage · 90% mutation score · Scorecard 7.8 · OpenSSF Best Practices: silver*, in German on the German home page. *What's new* below the projects lists the newest release of each project, each linked to its notes. The numbers come from the dashboard at the same address and follow it within two hours; the page asks no other server. Without JavaScript, a card shows the level of its Best Practices and *What's new* links the dashboard. *What's new* links the feed of the releases of all projects for a feed reader.
- **A Trust page with the guarantees of every project, and an About page:** besides *Home*, the menu had only *Security*, about the website itself, so nothing showed what the projects promise or who builds them. The menu now has *Home*, *Trust* and *About*. *Trust* shows the guarantees of every project in one table, with a column for each: its latest release, signed tags, build provenance at SLSA Build Level 3, immutable releases, SBOMs as SPDX and CycloneDX, OpenVEX, its test coverage, mutation score and OpenSSF Scorecard, which follow the dashboard as the page loads, its level of the OpenSSF Best Practices, and links to its security policy and its form for private reports. Below the table, each guarantee is explained, and a tab for each project has the commands of the GitHub CLI that check its latest release, which work as they are copied, with those of gitsign for a signed tag. *About* tells who builds the projects and why, shows in a diagram how one blueprint and its bots carry a change to a signed release in every repository, and links the decision records, GitHub Sponsors and the ways to get in touch. The security page of the website is now under *Trust* as *This website*, and the automation under *About*. Both pages are in German too, as *Vertrauen* and *Über*.

## [1.0.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v0.1.0...v1.0.0) (2026-10-14)

### Changes

- **The first stable version, 1.0.0:** the rebuilt website, with a home page that shows every project, one search across the documentation of all of them and an issue form that leads to the right project, is complete. From now on, a release that moves or removes an address of the website, such as `dennis-otto.github.io/#ha-autodarts`, is a new major version.

## 0.1.0 (2026-10-14)

### Features

- **A home page that shows the projects:** the home page was a wall of six text cards with the pencil, the date and the footer of a page of documentation. It now opens with a hero: the DO monogram, one sentence about the projects and two buttons, *See the projects* and *Sponsor*. The projects follow in two groups, *For the smart home and the document archive* and *For maintainers on GitHub*, each card with a picture of the project, its name as a link to its website and its two buttons on one line, on a phone too. A sentence explains how Paperless Sync and Paperless Unified Search work together, and the card of Repo Blueprint leads to the dashboard. The header shows the monogram and leads to the profile with every repository instead of the repository of the website, the footer links GitHub and GitHub Sponsors, and the menu has *Home* and *Security*, which links the decision records. The page stays fast: about 220 KB, with each picture about 15 KB and loaded only as it comes into view.
- **One search for the documentation of every project:** the search box of the website found only its own three pages, so *Cricket* or *archive account* found nothing. It now finds the pages of every project website too, each under the short name of its project, such as *Autodarts › Games and rules*, and a result opens the page on the website of the project. The search follows the documentation of the projects within a day; a project website that can't be reached stays out of the search until the next day, and the rest of the website stays as it is. The search loads about 100 KB more, but only when you go to the search box or once the page has loaded, so the page appears as fast as before.
- **An icon for every website of the address:** `/favicon.ico` and `/apple-touch-icon.png` answered *404* for all six websites at dennis-otto.github.io, since browsers and phones ask the root of the address for them. Both now show the monogram, which is the icon of the browser tab too.
- **A problem with a project reaches its own repository:** the issue chooser of the website's repository offered only its own forms, so a problem with Autodarts for Home Assistant or Paperless Sync could land here, where none of their code is. The chooser now also links the issues of each of the five projects, above the link to the website and the security report. Its own forms are for the hub pages of the website alone, not for the documentation of a project, which its own repository builds: *Problem with the website* asks for the address of the page, the browser and the device and, if it helps, a screenshot, instead of a release version and logs, and both forms point to the projects' issues as well. Their Area field names the parts of the website (the home page, the security page and the decision records, the German pages, the design) and gives the issue the label of its area; a pull request gets the same labels by the files it changes.
- **Every project on the home page has a heading of its own:** screen readers list the cards as headings under the heading of their group and jump from one project to the next, and each card has an address that is the same in English and German, such as [dennis-otto.github.io/#ha-autodarts](https://dennis-otto.github.io/#ha-autodarts).
- **A wrong address leads somewhere:** an address of dennis-otto.github.io that leads nowhere, such as `/autodarts/`, showed a bare *404 - Not found*. It now lists every project with its website and a link to the home page, in English and German, and asks *Did you mean Autodarts for Home Assistant?* when the address looks like a project.
- **Search engines find every website of the address:** `/robots.txt` names the sitemap of this website and of the documentation of every project under dennis-otto.github.io. The home page tells search engines the name of the website, its owner and every project with its repository and license. Its title in browser tabs and search results reads *Open-source apps for Home Assistant, Nextcloud and Paperless-ngx*, or *Open-Source-Apps für Home Assistant, Nextcloud und Paperless-ngx* in German, instead of *Dennis Otto* and *Startseite - Dennis Otto*, and the preview card of a shared link names the three instead of *Home* or *Startseite*.
- **One place to report a vulnerability of any of the websites:** `/security.txt` (RFC 9116) names the private report form and the security page. `/.well-known/security.txt` follows once the Docs workflow of the blueprint publishes folders whose names start with a dot.

### Bug fixes

- **The German button of Repo Blueprint leads to its section:** *Repository anlegen* opened the German README at its top; it now opens the section *Ein Repository anlegen*.
