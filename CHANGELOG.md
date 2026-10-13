# Changelog

All notable changes, by release. Each pull request that changes something for
users describes it under Unreleased. The release bot makes that text the section of
the next release, or lists the pull requests when there is none.

## Unreleased

### Features

- **A problem with a project reaches its own repository:** the issue chooser of the website's repository offered only its own forms, so a problem with Autodarts for Home Assistant or Paperless Sync could land here, where none of their code is. The chooser now also links the issues of each of the five projects, above the link to the website and the security report. Its own forms are for the hub pages of the website alone, not for the documentation of a project, which its own repository builds: *Problem with the website* asks for the address of the page, the browser and the device and, if it helps, a screenshot, instead of a release version and logs, and both forms point to the projects' issues as well. Their Area field names the parts of the website (the home page, the security page and the decision records, the German pages, the design) and gives the issue the label of its area; a pull request gets the same labels by the files it changes.
