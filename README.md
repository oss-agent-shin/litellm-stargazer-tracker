# litellm-agent-platform stargazer tracker

Daily-syncs stargazers of [BerriAI/litellm-agent-platform](https://github.com/BerriAI/litellm-agent-platform) and records those who have a LinkedIn URL on their GitHub profile.

## Files

- [`stargazers.csv`](./stargazers.csv) — current snapshot, sorted by `starred_at` desc. GitHub renders this as a sortable table.
- [`seen.json`](./seen.json) — dedup state of every login already evaluated, so each run only profile-fetches *new* stargazers.
- [`scripts/sync.py`](./scripts/sync.py) — the sync script.
- [`.github/workflows/sync.yml`](./.github/workflows/sync.yml) — runs daily at 13:00 UTC, also triggerable manually via the Actions tab.

## LinkedIn detection

For each stargazer, LinkedIn is sourced from (in order, first match wins):

1. `GET /users/{login}/social_accounts` — the structured field GitHub exposes when a user explicitly links their LinkedIn.
2. A `linkedin.com/(in|pub|company)/...` URL found in the user's `blog` field.
3. Same regex applied to the user's `bio` field.

If none match, the user is recorded in `seen.json` as `has_linkedin: false` and not re-checked on subsequent runs.

## Triggering a run manually

Go to **Actions → Sync stargazers → Run workflow**.

## Caveats

- LinkedIn discovery is best-effort. There is no reliable way to find a LinkedIn for someone who didn't publish it on their GitHub profile.
- Scheduled workflows on GitHub auto-disable after 60 days of repo inactivity. Push any commit (or run the workflow manually) to reset the timer.
