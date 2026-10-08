# Security design

<!-- The blueprint wrote this page once; from now on it belongs to the project. Keep it true to the software: what it protects, what it trusts, the threats and how the code counters them, and what remains. -->

What Dennis Otto protects, what it trusts and which risks remain. [SECURITY.md](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/SECURITY.md) says how to report a vulnerability and how to verify a release, and argues why the repository and its releases are safe.

## What you can expect

- The repository holds documents and scripts; nothing of it runs on its own.
- The scripts run with the permissions of whoever starts them, check their arguments and change nothing outside the folder they are given.

## Trust boundaries

1. **Repository → user.** Documents and scripts reach the user through a release, whose signatures [SECURITY.md](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/SECURITY.md#verify-a-release) explains.

## Threats and countermeasures

| Threat | Countermeasure |
| --- | --- |
| A script changes more than it should | Scripts check their arguments and stay in the folder they are given |
| A tampered release | Releases are signed, as [SECURITY.md](https://github.com/Dennis-Otto/dennis-otto.github.io/blob/main/SECURITY.md#verify-a-release) shows |

## Residual risks

- Whoever runs a script trusts it with their permissions; read it before running it.
