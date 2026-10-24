---
# The title of the browser tab and of search results; the menu says Projekte, in the
# section Vertrauen.
title: Vertrauen
description: "Die Garantien jedes Projekts von Dennis Otto, von signierten Tags, SLSA-Provenienz und SBOMs bis zur Testabdeckung und vertraulichen Meldungen von Sicherheitslücken, mit den Befehlen, die sie prüfen."
# The template of the pages with live facts, whose script fills the table.
template: facts.html
---

# Vertrauen

<!-- This page is the German translation of docs/trust.md: change both together, keep every claim true to the SECURITY.md of every project, and check every command against the latest release of every project. -->

Jedes Projekt hier entsteht aus einem [Blueprint](https://github.com/Dennis-Otto/repo-blueprint), der seine Releases baut, signiert und prüft, und so geben alle dieselben Garantien. Du musst ihnen nicht einfach glauben: Jede Garantie unten bringt einen Weg mit, sie selbst zu prüfen. Diese Seite handelt von den Projekten; [Diese Website](security.md) beschreibt die Sicherheit und den Datenschutz der Website selbst.

## Was jedes Projekt garantiert {#every-project}

<!-- trust-shared -->

## Die Zahlen jedes Projekts {#numbers}

<!-- trust -->

## Was die Garantien bedeuten { #guarantees }

- **Signierte Tags.** Der Release-Workflow jedes Projekts signiert den Tag jedes Releases mit [gitsign](https://github.com/sigstore/gitsign): mit einem Zertifikat von [Sigstore](https://www.sigstore.dev/) für diesen Workflow, das zehn Minuten gilt, statt mit einem Schlüssel. Es gibt keinen Signaturschlüssel, der verloren gehen könnte, und der Workflow baut kein Release auf einem Tag, den er nicht selbst signiert hat. GitHub zeigt diese Tags als *Unverified*, weil es Zertifikate von Sigstore nicht prüft; gitsign prüft sie, wie [Einen signierten Tag prüfen](#check-a-signed-tag) zeigt.
- **Build-Provenienz.** Jede Datei eines Releases entsteht in einem isolierten Build, dessen Workflow mit Sigstore signiert, wo und wie er die Datei gebaut hat, aus welchem Commit: ihre Provenienz, nach [SLSA Build Level 3](https://slsa.dev/spec/v1.0/levels#build-l3).
- **Unveränderliche Releases.** Ist ein Release veröffentlicht, können sich weder seine Dateien noch sein Tag ändern. GitHub signiert eine Attestierung, die den Tag an seinen Commit und an jede Datei des Releases bindet.
- **SBOM.** Jedes Release listet, was es ausliefert, mit jeder Komponente darin, unter seinem Namen und seiner Version, als SPDX und als CycloneDX, damit ein Scanner wie [Grype](https://github.com/anchore/grype) es gegen die Advisories prüft, die er kennt. `THIRD_PARTY_NOTICES.md` daneben enthält die Lizenzen der Komponenten von Dritten.
- **OpenVEX.** Akzeptiert ein Projekt ein Advisory, mit dem Grund, warum es das Projekt nicht betrifft, trägt sein Release ein OpenVEX-Dokument, das das einem Scanner sagt. Ein Release ohne akzeptiertes Advisory trägt keines.
- **So geprüft, wie du prüfen kannst.** Nach jedem Release und jede Woche prüft ein Workflow jedes Projekts sein neuestes Release so, wie die Befehle unten es tun.
- **Testabdeckung und Mutations-Score.** Der Anteil des Codes, den die Tests eines Projekts ausführen, und der Anteil der Mutanten, kleiner Änderungen am Code, die seine Tests erkennen.
- **OpenSSF Scorecard.** Die [OpenSSF Scorecard](https://scorecard.dev/) bewertet jede Woche die Sicherheitspraktiken jedes Repositorys, mit bis zu 10 Punkten, etwa signierte Releases, fest gepinnte Abhängigkeiten, den Schutz seines Hauptzweigs und die Berechtigungen seiner Workflows.
- **OpenSSF Best Practices.** Das [OpenSSF-Best-Practices-Badge](https://www.bestpractices.dev/) jedes Projekts, auf der Stufe bestanden, Silber oder Gold, von denen jede mehr Kriterien verlangt als die vorige.
- **Sicherheitsrichtlinie und vertrauliche Meldungen.** Die SECURITY.md jedes Projekts beschreibt auf Englisch, was mit der Meldung einer Sicherheitslücke geschieht: eine Antwort innerhalb von 7 Tagen, eine erste Einschätzung innerhalb von 14 und ein Release mit dem Fix spätestens nach 90 Tagen. Meldungen gehen vertraulich an das Projekt, über das Formular von GitHub unter [Was jedes Projekt garantiert](#every-project), nie in ein öffentliches Issue. Meldungen auf Deutsch sind willkommen.

## Ein Release selbst prüfen { #check-a-release }

Die [GitHub CLI](https://cli.github.com/), `gh`, prüft die Signaturen mit den öffentlichen Schlüsseln von GitHub und Sigstore, die sie selbst abruft. Ohne Tag nimmt sie das neueste Release, das [die Tabelle der Zahlen](#numbers) zeigt; diese Befehle prüfen die Releases, seit der Release-Workflow eines Projekts unveränderliche, signierte Releases baut, und ältere Releases geben die Garantien, die die SECURITY.md ihres Projekts damals beschrieb. Der erste Befehl prüft die Attestierung des Releases und gibt die Dateien aus, die sie an seinen Tag bindet; der zweite lädt das Paket herunter, das du installierst, oder die SBOM eines Projekts ohne Paket; und der dritte prüft die Provenienz dieser Datei und gibt *Verification succeeded* aus: Der Release-Workflow des Projekts hat sie aus dem Commit des Tags gebaut.

<!-- verify -->

### Einen signierten Tag prüfen {#check-a-signed-tag}

[gitsign](https://github.com/sigstore/gitsign) prüft die Signatur eines Tags so, wie der Workflow es tut, der jedes Release prüft: dass der Release-Workflow des Projekts ihn auf seinem `main` signiert hat. In einer Shell wie Bash, mit dem Namen des Repositorys eines Projekts in `repo`:

```sh
repo=homedarts-for-autodarts
git clone --quiet --no-checkout --filter=blob:none "https://github.com/Dennis-Otto/$repo.git"
cd "$repo"
tag=$(gh release view --repo "Dennis-Otto/$repo" --json tagName --jq .tagName)
gitsign verify-tag "$tag" --certificate-identity "https://github.com/Dennis-Otto/$repo/.github/workflows/release.yml@refs/heads/main" --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Eine Sicherheitslücke melden { #report-a-vulnerability }

Bitte eröffne für eine vermutete Sicherheitslücke kein öffentliches Issue. Melde sie vertraulich an ihr Projekt, mit seinem Link unter [Was jedes Projekt garantiert](#every-project); [Diese Website](security.md#eine-sicherheitslücke-melden) sagt, wohin eine Sicherheitslücke der Website geht. Die Seite [Über](about.md) erzählt, wer die Projekte baut und wie.
