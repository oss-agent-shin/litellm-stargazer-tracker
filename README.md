# litellm-agent-platform stargazer tracker

Daily-syncs stargazers of [BerriAI/litellm-agent-platform](https://github.com/BerriAI/litellm-agent-platform) and records those who have a LinkedIn URL on their GitHub profile.

## ⚠️ One-time activation required

The agent that scaffolded this repo couldn't create files under `.github/workflows/` (its token lacks the `workflow` scope). To activate the daily cron:

1. Open [`workflow.yml.template`](./workflow.yml.template) in the GitHub UI.
2. Click **Edit (pencil)** → rename the path to `.github/workflows/sync.yml` → commit.
3. Go to **Actions → Sync stargazers → Run workflow** to do an immediate first run.

After that, the cron runs daily at 13:00 UTC on its own.

## Files

- [`stargazers.csv`](./stargazers.csv) — current snapshot, sorted by `starred_at` desc. GitHub renders this as a sortable table.
- [`seen.json`](./seen.json) — dedup state of every login already evaluated, so each run only profile-fetches *new* stargazers.
- [`scripts/sync.py`](./scripts/sync.py) — the sync script.
- `.github/workflows/sync.yml` — runs daily at 13:00 UTC, also triggerable manually via the Actions tab. (Created from `workflow.yml.template` per the activation step above.)

## LinkedIn detection

For each stargazer, LinkedIn is sourced from (in order, first match wins):

1. `GET /users/{login}/social_accounts` — the structured field GitHub exposes when a user explicitly links their LinkedIn.
2. A `linkedin.com/(in|pub|company)/...` URL found in the user's `blog` field.
3. Same regex applied to the user's `bio` field.

If none match, the user is recorded in `seen.json` as `has_linkedin: false` and not re-checked on subsequent runs.

## Caveats

- LinkedIn discovery is best-effort. There is no reliable way to find a LinkedIn for someone who didn't publish it on their GitHub profile.
- Scheduled workflows on GitHub auto-disable after 60 days of repo inactivity. Push any commit (or run the workflow manually) to reset the timer.
- The target repo currently has ~520 stars, so the first run profile-fetches all of them (~1040 API calls); subsequent runs only fetch *new* stargazers. Well within the 1000 req/hr Actions limit per hour, but the first run may take a few minutes.
