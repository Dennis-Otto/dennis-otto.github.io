#!/usr/bin/env bash
# Opens, updates or closes the one pull request of the catalog bot, from the branch
# BRANCH of this repository, with the edits that the job catalog of
# .github/workflows/catalog.yml kept in "$RUNNER_TEMP/edits": files.txt, the paths
# that the edits touch, files/, the edited files at those paths, and pull-request.md,
# the text of the pull request. The step "Open, update or close the pull request of
# the catalog" of the job catalog-pull-request runs it with the token of the release
# app; tests/test_catalog_pull_request.py runs it against a fake gh on the PATH.
#
# The environment of the step:
#   GH_TOKEN, GH_REPO  the token of the release app and the repository, for gh
#   APP_SLUG           the slug of the release app, whose account makes the commit
#   BRANCH, HEADLINE   the branch of the pull request, and its title and first line
#   EDITS              true when the job catalog kept edits
#   ISSUE              the number of the issue of the catalog
#   SHA, URL           the commit of main that was compared, and the address of the run
#   RUNNER_TEMP, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY  those of the runner
# It writes number=<the pull request> to GITHUB_OUTPUT when one stays open.
set -euo pipefail

: "${GH_REPO:?}" "${APP_SLUG:?}" "${BRANCH:?}" "${HEADLINE:?}" "${SHA:?}" "${URL:?}"
: "${RUNNER_TEMP:?}" "${GITHUB_OUTPUT:?}" "${GITHUB_STEP_SUMMARY:?}"
EDITS="${EDITS:-}"
ISSUE="${ISSUE:-}"

# Only the app's own pull request from the branch of this repository: a fork may open
# one from a branch of the same name.
open="$(gh pr list --head "$BRANCH" --state open --json number,isCrossRepository,author \
  --jq "map(select(.isCrossRepository == false and .author.login == \"app/$APP_SLUG\"))[0].number // empty")"
# A person may finish the edits on the branch, such as a website that moved, which the
# bot would overwrite, or delete with the branch. The merge commit of the button
# "Update branch" names the person who clicked it, and finishes nothing.
others=0
if [[ -n "$open" ]]; then
  others="$(gh pr view "$open" --json commits \
    --jq "[.commits[] | select(.messageHeadline | startswith(\"Merge branch\") | not) | .authors[].login | select(. != \"${APP_SLUG}[bot]\")] | length")"
fi
if ((others > 0)); then
  echo "number=$open" >>"$GITHUB_OUTPUT"
  echo "#$open has a commit of a person, so the bot leaves it as it is." >>"$GITHUB_STEP_SUMMARY"
  exit 0
fi
if [[ "$EDITS" != true ]]; then
  if [[ -n "$open" ]]; then
    gh pr close "$open" --delete-branch \
      --comment "\`main\` needs none of these edits any more: $URL"
    echo "main needs no edit; closed #$open." >>"$GITHUB_STEP_SUMMARY"
  fi
  exit 0
fi

# Only the files that the edits touch, by plain paths, whatever the job catalog kept:
# never a workflow, and at least one.
kept="$RUNNER_TEMP/edits"
edited='projects\.toml|README(\.de)?\.md|docs/[^/]+\.md|tests/fixtures/not-found-data\.json'
if grep --invert-match --line-regexp --extended-regexp "$edited" "$kept/files.txt"; then
  echo "::error::The edits of the catalog bot hold the files above, which it never edits."
  exit 1
fi
if [[ ! -s "$kept/files.txt" ]]; then
  echo "::error::The catalog bot kept edits but names no file of them."
  exit 1
fi

# Points the branch of the pull request at a commit, new or moved.
point() {
  if gh api "repos/$GH_REPO/git/ref/heads/$1" >/dev/null 2>&1; then
    gh api --method PATCH "repos/$GH_REPO/git/refs/heads/$1" -f sha="$2" -F force=true >/dev/null
  else
    gh api --method POST "repos/$GH_REPO/git/refs" -f ref="refs/heads/$1" -f sha="$2" >/dev/null
  fi
}
# The commit starts from the commit that was compared, so that there is one pull
# request with one commit, however often main changed. It is made on a branch of its
# own, and the branch of the pull request moves to it in one step: a pull request
# whose head is a commit of main would be closed by GitHub. That branch starts anew,
# so that one which a failed run left behind can't stop the next run.
scratch="$BRANCH-next"
if gh api "repos/$GH_REPO/git/ref/heads/$scratch" >/dev/null 2>&1; then
  gh api --method DELETE "repos/$GH_REPO/git/refs/heads/$scratch" >/dev/null
fi
gh api --method POST "repos/$GH_REPO/git/refs" -f ref="refs/heads/$scratch" -f sha="$SHA" >/dev/null
# The commit goes through GitHub's API as the release app: GitHub signs it, as main
# requires, and it starts the checks. The sign-off names the app's account, which is
# the author of the commit.
user_id="$(gh api "users/${APP_SLUG}[bot]" --jq .id)"
body="Made by the catalog bot on $SHA: $URL

Signed-off-by: ${APP_SLUG}[bot] <${user_id}+${APP_SLUG}[bot]@users.noreply.github.com>"
while IFS= read -r path; do
  base64 --wrap=0 "$kept/files/$path" >"$RUNNER_TEMP/contents.txt"
  jq --null-input --arg path "$path" --rawfile contents "$RUNNER_TEMP/contents.txt" \
    '{path: $path, contents: $contents}'
done <"$kept/files.txt" >"$RUNNER_TEMP/additions.json"
jq --null-input --arg repository "$GH_REPO" --arg branch "$scratch" --arg head "$SHA" \
  --arg headline "$HEADLINE" --arg body "$body" --slurpfile additions "$RUNNER_TEMP/additions.json" \
  '{
    query: "mutation ($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) { commit { oid } } }",
    variables: {input: {
      branch: {repositoryNameWithOwner: $repository, branchName: $branch},
      expectedHeadOid: $head,
      message: {headline: $headline, body: $body},
      fileChanges: {additions: $additions}
    }}
  }' >"$RUNNER_TEMP/commit.json"
commit="$(gh api graphql --input "$RUNNER_TEMP/commit.json" --jq .data.createCommitOnBranch.commit.oid)"
point "$BRANCH" "$commit"
gh api --method DELETE "repos/$GH_REPO/git/refs/heads/$scratch" >/dev/null
{
  cat "$kept/pull-request.md"
  echo
  echo "The issue #$ISSUE lists every difference, those that need a person too. This run made the commit: $URL"
} >"$RUNNER_TEMP/body.md"
if [[ -n "$open" ]]; then
  gh pr edit "$open" --title "$HEADLINE" --body-file "$RUNNER_TEMP/body.md"
else
  created="$(gh pr create --base main --head "$BRANCH" --title "$HEADLINE" --body-file "$RUNNER_TEMP/body.md")"
  open="${created##*/}"
fi
echo "number=$open" >>"$GITHUB_OUTPUT"
echo "The pull request of the catalog, #$open from $BRANCH, has the commit $commit." >>"$GITHUB_STEP_SUMMARY"
