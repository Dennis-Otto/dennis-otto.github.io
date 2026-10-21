---
# The title of the browser tab and of search results; the menu says Projects, in the
# section Trust.
title: Trust
description: "The guarantees of every project by Dennis Otto, from signed tags, SLSA provenance and SBOMs to test coverage and private vulnerability reports, with the commands that check them."
# The template of the pages with live facts, whose script fills the table.
template: facts.html
---

# Trust

<!-- This page belongs to the project. Keep every claim true to the SECURITY.md of every project, which the blueprint writes, check every command against the latest release of every project, and change docs/trust.de.md with it. -->

Every project here is made from one [blueprint](https://github.com/Dennis-Otto/repo-blueprint), which builds, signs and checks its releases, so they all give the same guarantees. You don't have to take them on trust: each guarantee below comes with a way to check it yourself. This page is about the projects; [This website](security.md) is about the security and privacy of the website itself.

<!-- trust -->

## What the guarantees mean { #guarantees }

- **Signed tags.** The release workflow of each project signs the tag of every release with [gitsign](https://github.com/sigstore/gitsign): with a certificate of [Sigstore](https://www.sigstore.dev/) for that workflow, valid for ten minutes, instead of a key. No signing key exists that could leak, and the workflow builds no release on a tag that it didn't sign. GitHub shows these tags as *Unverified*, since it doesn't check certificates of Sigstore; gitsign does, as [Check a signed tag](#check-a-signed-tag) shows.
- **Build provenance.** Every file of a release comes from an isolated build, whose workflow signs with Sigstore where and how it built the file, from which commit: its provenance, at [SLSA Build Level 3](https://slsa.dev/spec/v1.0/levels#build-l3).
- **Immutable releases.** Once a release is published, neither its files nor its tag can change. GitHub signs an attestation that ties the tag to its commit and to every file of the release.
- **SBOM.** Every release lists what it ships, with every component inside it, under its name and version, as SPDX and as CycloneDX, so that a scanner such as [Grype](https://github.com/anchore/grype) checks it against the advisories that it knows. `THIRD_PARTY_NOTICES.md` beside it has the licenses of the third-party components.
- **OpenVEX.** When a project accepts an advisory, with the reason why it doesn't affect the project, its release carries an OpenVEX document that tells a scanner so. A release without an accepted advisory carries none.
- **Checked as you can.** After every release and every week, a workflow of each project verifies its latest release the way the commands below do.
- **Test coverage and mutation score.** The share of the code that the tests of a project run, and the share of mutants, small changes to the code, that its tests catch.
- **OpenSSF Scorecard.** The [OpenSSF Scorecard](https://scorecard.dev/) rates the security practices of each repository every week, out of 10, such as signed releases, pinned dependencies, the protection of its main branch and the permissions of its workflows.
- **OpenSSF Best Practices.** The [OpenSSF Best Practices badge](https://www.bestpractices.dev/) of each project, at the level of passing, silver or gold, each of which asks for more criteria than the one before.
- **Security policy and private reports.** The SECURITY.md of each project says what happens with a report of a vulnerability: an answer within 7 days, a first assessment within 14 and a fixed release within 90 days at the latest. Reports go privately to the project, through the form of GitHub in the table, never into a public issue.

## Check a release yourself { #check-a-release }

The [GitHub CLI](https://cli.github.com/), `gh`, checks the signatures with the public keys of GitHub and Sigstore, which it fetches itself. Without a tag, it takes the latest release, which the table shows; these commands check releases made since the release workflow of a project builds immutable, signed releases, and older releases give the guarantees that the SECURITY.md of their project described at the time. The first command checks the attestation of the release and prints the files that it ties to its tag; the second downloads the package that you install, or the SBOM of a project without one; and the third checks the provenance of that file and prints *Verification succeeded*: the release workflow of the project built it from the commit of the tag.

<!-- verify -->

### Check a signed tag {#check-a-signed-tag}

[gitsign](https://github.com/sigstore/gitsign) checks the signature of a tag as the workflow that verifies every release does: that the release workflow of the project signed it, on its `main`. In a shell such as Bash, with the name of the repository of a project in `repo`:

```sh
repo=homedarts-for-autodarts
git clone --quiet --no-checkout --filter=blob:none "https://github.com/Dennis-Otto/$repo.git"
cd "$repo"
tag=$(gh release view --repo "Dennis-Otto/$repo" --json tagName --jq .tagName)
gitsign verify-tag "$tag" --certificate-identity "https://github.com/Dennis-Otto/$repo/.github/workflows/release.yml@refs/heads/main" --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Report a vulnerability {#report-a-vulnerability}

Please don't open a public issue for a suspected vulnerability. Report it privately to its project, with the link in the table; [This website](security.md#report-a-vulnerability) says where a vulnerability of the website goes. The [About](about.md) page tells who builds the projects and how.
