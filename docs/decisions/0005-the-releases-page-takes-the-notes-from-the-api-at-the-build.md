# The Releases page takes the notes of the releases from the API of GitHub at the build

- Status: accepted
- Date: 2026-10-24

## Context

*What's new* on the home pages listed only the name, the version and the age of the newest releases, five of them, linked to GitHub. A visitor couldn't see what changed without leaving the website, although every project writes its changelog in the words of its users, and since the sixth project came, the one with the oldest release was always missing: on 2026-10-24, Player Switch for Autodarts v0.2.0. The website had no page with the notes of the releases, and the search didn't find them.

[Decision 0003](0003-the-home-pages-take-their-live-facts-from-the-dashboard.md) takes the release and the numbers of every project from the data of the dashboard, `repos.json`, as the page loads, so that they stay current without a token and without a request to another server. That data has the latest release of each repository, but not its notes, and `releases.atom` holds only the start of each.

## Options

1. **The dashboard publishes the notes too.** The page would read them as it reads the numbers, but the blueprint would carry the notes of every release of every repository in its data, which every home page loads, and the Releases page would need JavaScript to show anything.
2. **The browser asks the API of GitHub.** The notes would be current, but every reader would ask another server, which the privacy of the website rules out, and the API allows a reader without a token 60 requests an hour.
3. **The build reads the notes from the API of GitHub,** once for every project, as the HTML that GitHub makes of their Markdown, and writes what it keeps of them into the page. The page is complete without JavaScript and in the search; the notes are at most a day old, since the Catalog workflow builds the website every day, and the script adds a release that came out since from `repos.json`, as in option 3 of decision 0003. The build needs the API, and the notes are written by others than this repository.

## Decision

Option 3. The hooks in `.github/mkdocs_project.py` read the latest releases of every project with a repository from `api.github.com`, leave out drafts and prereleases, and keep of their notes only text, paragraphs, lists, headings, tables, code, quotes and links to `https://`, without an attribute but the address of a link. The notes take the place of their placeholders in the HTML of the page, after Markdown, so that no extension of Markdown reads them. A token in `GITHUB_TOKEN` or `GH_TOKEN`, where one is set, goes to the API alone. The build reads the releases once, for the Releases page and *What's new* of every language, and passes without them: the page then links the releases of every project on GitHub.

*What's new* now comes from the same releases: the latest release of every project with a repository, the newest first, each with the headline of its notes and linked to them on the Releases page. The script puts a newer release of `repos.json` in the place of one that came out after the build, so decision 0003 still holds for the numbers and for what changes between two builds.

## Consequences

- A visitor reads what changed in every project on the website, in English and on the German page too, and the search finds it.
- The build depends on the API of GitHub for the notes, but never fails for it. Without a token, the build asks the API once for every project, well below its limit of 60 requests an hour; the Docs workflow of the blueprint could pass the token of the workflow to the build, for a limit of 5,000.
- The notes reach the page only as the hooks keep them. A new kind of content in the notes, such as a picture, shows on the website only once the hooks keep it, and its tests show that it can't carry a script.
- The search index of each language grows by the text of the notes, once: each language has an index of its own, and every page loads only that of its language, so the German index holds the English notes of the German page.
