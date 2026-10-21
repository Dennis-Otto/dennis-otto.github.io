# The root website keeps the old addresses of a renamed project

- Status: accepted
- Date: 2026-10-21

## Context

Autodarts asked the project *Autodarts for Home Assistant* to stop using its name and logo. The project became *HomeDarts for Autodarts*, and its repository `Dennis-Otto/ha-autodarts` became `Dennis-Otto/homedarts-for-autodarts`. GitHub sends the old address of a renamed repository to the new one, but not its website: GitHub Pages publishes it in the folder of the new name, `/homedarts-for-autodarts/`, and nothing answers in the old folder, `/ha-autodarts/`, any more. Links in forums, chats, bookmarks, search results and the README of other projects lead there, many to a section of a page, such as `/ha-autodarts/de/games.html#cricket`.

GitHub Pages answers every address that no project serves from this website, as [decision 0002](0002-the-root-website-owns-the-address.md) describes, so the old folder reaches this website after the rename. GitHub Pages sends no redirect of its own: a website made of files can only lead on with a page at the old address.

## Options

1. **Leave the old addresses to the 404 page,** which suggests the project like the address. Every old link stops at a page that says it leads nowhere, and loses its section.
2. **Keep a repository under the old name** whose website leads to the new one. It takes the name back from the renamed repository, so GitHub stops sending the old address of the repository to the new one: clones, links to issues and the install link of HACS with the old name would break instead.
3. **Let this website lead the old addresses on:** a page at every address of the old website, which the build writes from a list in this repository, and the 404 page for every other address in the old folder.

## Decision

Option 3. A project names the folders where its website lived before in `former` of [projects.toml](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/projects.toml), and the pages of the old website, as its sitemap listed them before the rename, in `former/<folder>.txt`. While MkDocs builds the website, the hooks in `.github/mkdocs_project.py` write a page at each of those addresses. Its script leads to the same page in the new folder at once and keeps the query and the section of the address; without JavaScript, its refresh and its link lead there. It names the new address as its canonical one and asks search engines not to list it, so they move to the new address. The 404 page leads every other address in the old folder, such as that of a picture, to the same path in the new one, with its query and section. The card of the project on the home page keeps the anchor of the old folder, such as `/#ha-autodarts`, so no address of this website moves.

## Consequences

- Every page of the old website leads to its page on the new one, with its section. A page that the new website removes or renames lands on the 404 page of the new website.
- The pages at the old addresses wait behind the website of the project until its repository is renamed, since GitHub Pages serves the folder of a project before this website, so the change can come first.
- An old name stays taken: no new repository at the address may use it, or its website would hide the pages and GitHub would stop sending the old address of the repository to the renamed one. The check of projects.toml fails for a folder of `former` that the address or the home page uses already, and the strict build for a file of this website in such a folder.
- Search engines follow a canonical address more slowly than a redirect of the server, so the old addresses may show in search results for some weeks.
