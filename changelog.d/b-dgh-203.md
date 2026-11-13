### Bug fixes

- A build that GitHub's API refuses no longer leaves the Releases page, What's new and "Works with" thin without a word: the summary of the build lists the releases it read for every project and why one has none, the check of the built website warns of each project without its releases, and the downloads of the build wait between their tries, as long as GitHub asks when its limit of requests resets within half a minute.
- The daily watch of the live websites now reports data of the dashboard that is more than a day old, or that doesn't say when it was written, so that old releases and scores on the cards and the Trust page no longer go unnoticed for days.
