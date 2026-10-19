---
# The title of the browser tab and of search results; the menu says Dennis Otto, in
# the section About.
title: About
description: "Who builds the open-source projects at dennis-otto.github.io and why, and how one blueprint and its bots carry every change to a signed release in every repository."
---

# About

<!-- This page belongs to the project. Keep every sentence true to the repositories, and change docs/about.de.md with it. The page shows the DO monogram and no photo, as Dennis decided; a photo or an avatar replaces the picture below once he gives one. -->

![The DO monogram of Dennis Otto](assets/logo.svg){ width="96" height="96" .off-glb }

## Who builds them { #who }

[Dennis Otto](https://github.com/Dennis-Otto) builds and maintains every project on this website, in the open and under open-source licenses. He reads every issue, reviews the pull requests of others, decides what comes next and answers the reports of vulnerabilities; bots do the routine work, each with the least permissions it needs.

## Why they exist { #why }

The projects connect tools that people already use at home and at work: an Autodarts board with Home Assistant, the document archive of Paperless-ngx with Nextcloud, and the issues and releases of a repository with bots that look after them. Each of them is meant to be as dependable as the work of a team, with one person behind it: tests for every change, signed releases that anyone can check, security checks, a website of its own and a first answer to every issue. The [Trust](trust.md) page shows what each project guarantees.

## How they are built { #how }

Every repository is made from one template, [Repo Blueprint](https://dennis-otto.github.io/repo-blueprint/): the same checks, workflows, settings and policies in each, for every kind of project. What one repository learns, the blueprint brings to every other.

- **One blueprint.** A change of the blueprint, such as a faster check or a new security control, becomes a release of the blueprint, and its bot brings that release to every repository as a pull request, which passes the checks of that repository like any other change.
- **Releases.** The release bot turns the titles of the merged pull requests into the next version and its changelog, then builds, signs and publishes the release, and a workflow checks it the way its users can.
- **Updates.** Renovate keeps the dependencies, the actions and the images current, a week after their release, or at once when an update fixes a vulnerability.
- **Triage.** The [issue assistant](https://dennis-otto.github.io/issue-assistant/) gives a new issue a first analysis by an AI that only reads, adds its labels, finds duplicates, reminds of open questions and closes an issue once a release ships its fix.
- **Settings.** The settings bot applies the settings of every repository, such as the rules of its `main`, from a file of the repository after every change and every week, so that a setting changes only in a reviewed pull request.
- **Help in pull requests.** Every check explains itself when it fails: what it found, why that matters and how to fix it, and a bot makes every fix that a command can make.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/diagrams/from-a-change-to-a-release.dark.svg">
  <img src="images/diagrams/from-a-change-to-a-release.svg" alt="From a change to a release in every repository: A change to the blueprint, a pull request of a person, of Renovate or of a bot, reaches main only through every required check. The release bot of the blueprint turns it into a release with a signed tag, provenance and SBOMs, which can't change once published. The blueprint bot of every project verifies that release and opens a pull request with it, which passes every required check of the project, as the own pull requests of the project do. The release bot of the project then publishes a signed, immutable release of its own. A workflow checks each release as its users can, after every release and every week, the issue assistant closes the issues that the release fixes, and the users get the release, which this website shows.">
</picture>

[Automation](automation.md) lists every workflow of this repository with what it does, and the [dashboard](https://dennis-otto.github.io/repo-blueprint/dashboard/) shows the state of every repository at a glance.

## Decisions { #decisions }

The decisions that shape a project are written down with their reasons, so that a later change can see why things are as they are. The [decision records of this website](decisions/README.md) explain how it serves the whole address and where its live facts come from, and those of [the blueprint](https://github.com/Dennis-Otto/repo-blueprint/blob/main/docs/decisions/README.md) shape every repository.

## Support { #support }

The projects are free and open source. If they are useful to you, you can support their development on GitHub Sponsors.

[:octicons-heart-16: Sponsor](https://github.com/sponsors/Dennis-Otto){ .md-button .md-button--primary }

## Contact { #contact }

Questions, problems and ideas about a project go to the issues of its repository: the [issue chooser of this website](https://github.com/Dennis-Otto/dennis-otto.github.io/issues/new/choose) leads to those of every project, and has the forms for the website itself. Please report a vulnerability privately, as [Trust](trust.md#report-a-vulnerability) says. Everything else reaches Dennis through [his profile on GitHub](https://github.com/Dennis-Otto).
