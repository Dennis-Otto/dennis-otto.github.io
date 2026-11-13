# Changelog

All notable changes, by release. Each pull request that changes something for
users describes it under Unreleased. The release bot makes that text the section of
the next release, or lists the pull requests when there is none.

## Unreleased

## [1.9.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.8.0...v1.9.0) (2026-11-13)


### Features

* a feed of each project on the Releases page and a map of the projects ([#225](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/225)) ([c6b121e](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/c6b121e1d7843a87141e4402de681bf7d98bcb68))


### Bug fixes

* **hub:** tell of a build without releases and of old dashboard data ([#219](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/219)) ([bc348ef](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/bc348ef3b73496dcf0e8f93dddef46d031ecb1e6))
* lead the buttons of Player Switch and the issue assistant to their real targets ([#226](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/226)) ([ffed6c5](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/ffed6c5fed18f3a4f99c0402b15f22000f119d81))
* **releases:** show the notes for users once and date the pages by their releases ([#222](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/222)) ([3251f4a](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/3251f4a118cf53edbe7a615a82c07d53213c3ab2))
* **releases:** What's new drops the scope of a commit and names a maintenance release ([#217](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/217)) ([b671e16](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/b671e1664e0d9ed948f75a28bd053f8c43e6a408))
* **search:** keep the help and the setup pages of the projects in the search ([#215](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/215)) ([cc714c3](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/cc714c3c2244e0c05f18a0294a981e033ad3657c))
* small faults of the catalog bot, the card pictures and the German texts ([#228](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/228)) ([fa8b5b5](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/fa8b5b585cf1db41d2217bd7abeb82d8313fe0a6))
* the path above a page starts with the name of the website, and Material's end of life is May 5, 2027 ([#218](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/218)) ([10adad9](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/10adad931860864b487445de6a73625a84d00032))
* **trust:** verify the zip of Player Switch and check provenance as SECURITY.md does ([#212](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/212)) ([a2909c4](https://github.com/Dennis-Otto/dennis-otto.github.io/commit/a2909c4afaa8394e44ce8e60f105bbd235cac138))

## [1.8.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.7.0...v1.8.0) (2026-11-09)

### Features

- **The catalog bot gives a card back the light of its social preview by itself:** when the German picture of a card glows in a color that the social preview of its project lacks, the weekly catalog bot used to report it in its issue, and a person had to change `drawing.accent` in `projects.toml`. Now, where the preview names its `--accent`, the bot sets that color in its pull request, with every comment of the file in its place, and marks the difference in the issue; once a person merges it, the screenshot bot draws the picture anew. A preview without an accent of its own, or with two different ones, still leaves the choice to a person.

### Bug fixes

- **The German card of Player Switch shows its popup as large as the English one:** the popup of the extension grew taller with its button to join the lobby again, so inside the frame of the German picture it came out smaller than before and a good deal smaller than on the English card. It now hangs from the toolbar of the browser at the top of the picture and runs off its bottom edge, as in the social preview of the extension. A project in `projects.toml` asks for this with `drawing.hangs = true`; every other German card keeps its frame.

## [1.7.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.6.0...v1.7.0) (2026-11-09)

### Features

- **Dennis Otto Pager joins the home pages:** the Telegram bot on a Cloudflare Worker, which tells its maintainer only what needs them on GitHub and acts on it with a button, now has its card in English and German, with its live facts, its OpenSSF Best Practices level and a button to set it up. The search of this website finds the pages of its website, such as those about Telegram, and `robots.txt`, `llms.txt`, the Trust page, the 404 page, the issue chooser and the Security page name it as well.
- **Player Switch names every browser it works with:** its card said *Google Chrome on the desktop*; it now reads *Chrome or Edge 140 or newer and Firefox 140 or newer, on the desktop* from the manifest of its latest release, and its card and the Trust page show its OpenSSF Best Practices level.
- **The social preview shows every project:** the picture that GitHub shows for links to this repository now has the cards of Player Switch and the pager too, a column for each group of the home page.
- **Repo Pager is the new name of Dennis Otto Pager:** the pager became a product that every maintainer runs as an instance of their own, so its card, the search of this website, `llms.txt`, `robots.txt`, the Trust page, the Security page and the issue chooser name it Repo Pager, with its repository [Dennis-Otto/repo-pager](https://github.com/Dennis-Otto/repo-pager) and its website at `/repo-pager/`. Every address of its old website, such as `/dennis-otto-pager/de/setup.html`, leads to the same page of the new one, and the home page keeps the anchor `/#dennis-otto-pager`.
- **The card of Player Switch shows its popup:** its picture comes from the new social preview of the extension, the popup that its icon in the toolbar of the browser opens, large; the social preview of this website shows both new cards.

### Bug fixes

- **Repo Blueprint makes nine kinds of projects,** not seven as its card said.
- **The card of Player Switch glows in its own blue:** the German picture of its card lit the popup in the green of the Paperless apps, while its social preview, the English picture, is blue. Both pictures now show the popup in the blue of the extension, with its latest look, and the weekly catalog bot names every card whose light is a color that the social preview of its project lacks.

## [1.6.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.5.0...v1.6.0) (2026-11-01)

### Features

- **The catalog bot fixes what has one correct fix:** when a project gains a German website or loses one, or its website moved to another folder of the address, the bot used to report it in its issue, and a person had to change `projects.toml` and write the table of the README by hand. Now the bot asks the web for each address, makes the edit, with every comment of the file in its place, and keeps one pull request with it, whose checks run and which a person merges. The issue marks these differences and names the pull request; a repository that was renamed, archived, made private or is new stays in the issue for a person, as before. `python3 -I .github/mkdocs_project.py --network repositories.json --fix pull-request.md` makes the same edits on your machine.

## [1.5.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.4.0...v1.5.0) (2026-10-25)

### Features

- **German pictures on the German home page, and the first cards load first:** every card on the German home page showed the English social preview of its project, such as *Your board live in Home Assistant, locally*, and the pictures of the first row, which you see as the page opens, loaded last, after everything else, with an empty white box in their place until then. Now the German home page shows a German picture on every card: the logo, the name and the German tagline of the project beside a screenshot of it, in German where the project has one, in the look of its social preview, with a German description for screen readers; the English home page keeps the social previews. The pictures of the first group load at once, the first one before any other picture of the page, and those further down as you scroll to them. Until a picture is there, its place already has its size and the navy of the pictures, so no white box flashes in the light or the dark colors. The German pictures renew themselves like the English ones when a project changes its screenshot.
- **AI assistants find the guides of every project:** more and more people ask an AI assistant, such as *how do I bring my Autodarts board into Home Assistant?*, instead of a search engine, and `https://dennis-otto.github.io/llms.txt`, where assistants look for a map of a website, led nowhere. Now it is there, in Markdown as [llmstxt.org](https://llmstxt.org/) describes it: every project by the groups of the home page, each with its tagline, its website, its installation or first step, and the pages of its website that readers look for first, getting started, installation, guide, FAQ and troubleshooting, each with its German page, such as *Installation and setup* of HomeDarts for Autodarts with *Installation und Einrichtung*. It follows the projects with every build and never leads to a page for maintainers, such as a decision record.
- **A daily watch over what the live website depends on:** the website takes the live facts of its cards from the data of the dashboard of the blueprint, and the pages of every project from its search index, and when either changed or went away, the cards quietly kept old facts and a project quietly dropped out of the search, and nobody learned of it. Likewise, nothing noticed when the daily build stopped and `security.txt` drew near its expiry, or when an old address of a renamed project stopped leading to its page. Now the catalog bot asks the live websites every day after the daily build, and keeps one issue, *The live websites need attention*, open while something does, with what readers lose and the fix on every line, such as `release` missing from the data of the dashboard or the search index of a project website that answers 404; it closes the issue once everything is back. The summary of every build of the website shows how many pages and sections of each project website its search keeps, or why it left one out.

## [1.4.0](https://github.com/Dennis-Otto/dennis-otto.github.io/compare/v1.3.0...v1.4.0) (2026-10-25)

### Features

- **The cards follow the projects:** the picture of every card on the home page now renews itself from the social preview of its project. The screenshot bot makes the pictures anew every week, after every release and when started by hand, and one pull request brings every picture that looks different, together with the pictures at the top of the README, which a change of the projects or of the home page now renews too. The texts that describe the pictures for those who can't see them say what every preview keeps, so they stay true when a picture changes.
- **A Releases page with the notes of every project, and What's new names all of them:** *What's new* on the home page showed only the version of the newest releases, five of them, so one project was always missing, such as Player Switch for Autodarts v0.2.0, and a visitor had to go to GitHub to see what changed. Now *What's new* lists the latest release of every project, the newest first, each with the headline of its notes, such as *Ask Assist about your darts sounds more natural in German, Spanish, French and Dutch*, and leads to the new [Releases page](https://dennis-otto.github.io/releases.html), *Neuigkeiten* in German, with the notes of the latest five releases of every project, the newest first, a link to each project at the top, and the feed of all releases. The search finds the notes. A release that came out after the website was built shows up on both pages as they load, with a link to its notes on GitHub, and the day of every release reads as the time since, such as *3 days ago*. The notes keep their text, lists, code and links, but never a script or a picture of a release.
- **Every card says what its project works with:** the first question before an install is whether a project runs on your system, and the home page made you open each repository to find out. Now every card says it right above its buttons, as an app store does beside its install button, such as *Works with Home Assistant 2026.8.0 or newer*, *Works with Nextcloud 33 to 35 and Paperless-ngx* or *Works with Copier 9.8 or newer*, and *Funktioniert mit …* on the German page. The versions come from the latest release of each project, such as the `hacs.json` of HomeDarts for Autodarts or the `info.xml` of the Nextcloud apps, so the card follows the next release on its own. The table of the projects in the README has a column *Works with* that links the file of each, and search engines learn it from the structured data of the home page.

### Bug fixes

- **The search finds every page of every project:** the search at the top of dennis-otto.github.io held only 10 of the 76 pages of HomeDarts for Autodarts and no German page of a project, but hundreds of sections of decision records. Now it holds every page of every project website in English and German, and *installation* lists the installation of HomeDarts first, in the language of the page. The installation, the guide, the FAQ and the troubleshooting pages rank higher, the changelogs, the pages for maintainers and the decision records lower, and when the index runs out of room the changelogs and the pages for maintainers give up their sections first, while a decision record keeps only its title.
- **The Trust page on a phone:** the table of the guarantees was 766 pixels wide on a phone, so a reader saw two projects at a time, scrolled sideways and lost the names of the projects when scrolling down, and seven of its rows repeated the same value for every project, such as *gitsign, without a key* six times. The page now reads on a phone without scrolling sideways: *What every project guarantees* lists each guarantee that every project gives alike once, with the links to the security policy and the form for private reports of each project, and *The numbers of each project* has a row for each project with its latest release, test coverage, mutation score, OpenSSF Scorecard and OpenSSF Best Practices, which a phone shows as a card for each project, every number beside its label. The German page *Vertrauen* does the same.

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
