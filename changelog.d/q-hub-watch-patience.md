### Bug fixes

- The daily watch of the live websites and the weekly catalog bot no longer fail on a short outage of GitHub Pages: an address that answers 429 or an error of the server, such as 503, or can't be reached, is asked up to three times, 2 and then 10 seconds apart, within 3 minutes of the start of the run. Any other answer, such as 403, still fails at its first try, and an outage that lasts fails the run with the same message as before.
