# The home pages take their live facts from the data of the dashboard

- Status: accepted
- Date: 2026-10-19

## Context

The projects come with what sets them apart from most others of their kind: tests that run every line of their code, mutation tests, signed releases, a high score in the OpenSSF Scorecard, the silver level of the OpenSSF Best Practices and quick answers to new issues. With few stars, numbers that a reader can check are the strongest sign of trust that the home page can give, and a list of the newest releases shows that the projects are alive. The home page said so in one sentence, without a number.

The numbers change every few hours: a release, a new coverage, a new score. The website is built once a day and with every change of `main`, so numbers written at the build would be up to a day old. The home page must stay fast, private and readable: [decision 0002](0002-the-root-website-owns-the-address.md) makes it the first page of every website at the address, the privacy plugin keeps it from asking other servers, and it must read well without JavaScript.

## Options

1. **The build writes the numbers into the page,** from the API of GitHub and other services. The page is complete without JavaScript, but its numbers are up to a day old, and the build needs a token for the API and fails or waits when a service does.
2. **The browser asks the API of GitHub and the Scorecard.** The numbers are current, but every reader asks other servers, which the privacy of the website rules out, and the API of GitHub allows 60 requests an hour to a reader without a token, fewer than a reader who opens the page a few times needs.
3. **The browser reads the data of the dashboard of the blueprint,** which collects the release, the coverage, the mutation score, the Scorecard and the time to the first answer of every repository every two hours anyway, and publishes them as `repos.json` and `history.json` at the same address. The page asks no other server and needs no token, and the numbers are at most two hours old. Without JavaScript or without the data, the cards keep what the build wrote.

## Decision

Option 3, for the numbers that change often, and the build for the one that doesn't: [docs/javascripts/projects.js](../javascripts/projects.js) reads `repos.json`, or `history.json` when it can't, and writes the release, its day and the numbers into the cards and the newest releases under *What's new*, in the language of the page. The level of the OpenSSF Best Practices changes seldom and the dashboard doesn't collect it, so the hooks read it from bestpractices.dev at the build and write it into the card as text; the website shows no badge, since the hooks of the blueprint take every badge out of a page that the build would freeze.

*What's new* lists the newest release of each project, the five newest first, and not the five newest releases of all projects that the issue asked for. `repos.json` holds only the latest release of each repository, and reading `releases.atom` as XML for more would double the work of the script for a list in which one busy project, such as the blueprint with a release every few days, would push out all the others. One release of each project shows that every one of them is alive.

The head of the home pages names no feed, although the issue asked for it: Material asks the folder of every `link rel="alternate"` in the head for its `sitemap.xml`, to switch between the languages, and the dashboard publishes none, so every reader would make a failed request. *What's new* links the feed instead; once the dashboard publishes a sitemap, the head can name it.

## Consequences

- The numbers on the home pages follow the dashboard within two hours, without a build of the website, a token or a request to another server.
- The home pages depend on the shape of `repos.json`. The script reads only the `schema` that it knows, 1, and takes the numbers of `history.json` when the shape changes, until it learns the new one; a change of the shape in the blueprint names its version, so this repository can follow.
- Without the data, as in a preview of the website, the cards show what the build wrote: the level of the OpenSSF Best Practices and the links of the project.
- The tests of the script run with Node on a document of their own, in `scripts/check-project.sh` and the CI.
