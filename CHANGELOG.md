# Changelog

All notable changes, by release. Each pull request that changes something for
users describes it under Unreleased. The release bot makes that text the section of
the next release, or lists the pull requests when there is none.

## Unreleased

## [1.1.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.0.0...v1.1.0) (2026-10-19)


### Features

* a Trust page with every project's guarantees and an About page ([#55](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/55)) ([3b94e17](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/3b94e179cb63f026a66698b410b0ffcd24b8c9c2))
* show each project's version, release date and quality numbers on the home page, and what's new ([#50](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/50)) ([7bf74a0](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/7bf74a0fc2c7c38f4e262a8350bc18463f02b560))

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
