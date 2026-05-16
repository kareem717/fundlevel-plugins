---
name: check-prospect-news
description: |
  Build a pre-call briefing for a prospect by pulling their and their company's recent LinkedIn + X posts via Bright Data, then summarizing what's news-worthy with cited URLs. Use when the user provides a prospect (email, name, LinkedIn URL, X handle, or company name) and asks to "check news", "what's new with X", "research before a call", "recent activity from", "prep for a meeting with", or wants a briefing on a prospect. Looks the prospect up in Attio first to resolve their LinkedIn/X handles and their company's handles, then fetches recent posts in parallel and produces a cited summary.
---

# Check Prospect News

End-to-end procedure for building a prospect briefing from public posts. Each step has a clear handoff; do not skip steps.

## Step 1 — Resolve the prospect in Attio

Take whatever the user gave (email, name, LinkedIn URL, X handle, company). Run `mcp__claude_ai_Attio__search-records` on the `people` object with that string as the query.

- One strong match → continue with that record.
- Multiple plausible matches → list candidates with `{name, title, company.name}` and ask the user to pick.
- No people match → search the `companies` object. If found, ask the user whether they want company-only research or to identify a specific person.

If the workspace's attribute slugs aren't obvious from the search response, call `mcp__claude_ai_Attio__list-attribute-definitions` on `people` and `companies` once to discover them.

## Step 2 — Extract URLs

From the person record, pull (these slug names are typical, but the workspace may differ — adapt):
- `linkedin` → person LinkedIn URL
- `twitter` or `x` → person X URL
- linked `company` record reference → fetch with `mcp__claude_ai_Attio__get-records-by-ids` and read its `linkedin` and `twitter`/`x` attributes

Normalize each URL: lowercase host, `https://` scheme, strip query string and trailing slash. Drop any URL that's not a valid `linkedin.com/in/…`, `linkedin.com/company/…`, or `x.com/…` / `twitter.com/…` form. Convert `twitter.com` to `x.com`.

You'll have up to four URLs: person-LI, person-X, company-LI, company-X. Skip the ones that don't exist.

## Step 3 — Pick a date window

Default to the last 30 days from today. If the user said "past week", "since the demo", "this quarter", use that instead.

Format for the Bright Data input JSON:
- LinkedIn person input expects `start_date` and `end_date` in ISO with time: `2026-04-16T00:00:00.000Z`
- X input expects plain dates: `2026-04-16`
- LinkedIn company input expects no dates (use `limit_per_input=100` on the URL to bound the response)

## Step 4 — Fetch posts in parallel

For each URL, write the request body JSON to a temp file, then run the helper script in the **background** so all four fetches poll concurrently.

The helper:
```
${CLAUDE_PLUGIN_ROOT}/skills/check-prospect-news/scripts/bd_fetch.sh \
  <dataset_id> <discover_by> <input_json_path> <output_json_path>
```

The four invocations (skip any whose URL is missing):

| Target | dataset_id | discover_by | output path |
| --- | --- | --- | --- |
| Person LI | `gd_lyy3tktm25m4avu764` | `profile_url` | `/tmp/prospect-news/person-li.json` |
| Person X | `gd_lwxkxvnf1cynvib9co` | `profile_url_most_recent_posts` | `/tmp/prospect-news/person-x.json` |
| Company LI | `gd_lyy3tktm25m4avu764` | `company_url` | `/tmp/prospect-news/company-li.json` |
| Company X | `gd_lwxkxvnf1cynvib9co` | `profile_url_most_recent_posts` | `/tmp/prospect-news/company-x.json` |

Body shapes are in `references/datasets.md`. Use `mkdir -p /tmp/prospect-news` first. Start each fetch with `run_in_background=true` and wait for all of them to finish before continuing.

The script returns non-zero if `BRIGHTDATA_API_KEY` is missing — if that happens, tell the user to either (a) re-enable the plugin to set the key via `userConfig`, or (b) `export BRIGHTDATA_API_KEY=...` in their shell rc and restart Claude Code.

## Step 5 — Filter for news-worthy posts

Read each output JSON. Each file is an array of post objects. Treat a post as news-worthy if it indicates:

- Funding, acquisitions, partnerships, customer wins
- Product launches or major releases
- New senior hires, promotions, or departures
- Layoffs, restructuring, office moves
- Awards, press features, conference talks, podcast appearances
- Personal milestones worth congratulating (work anniversary, new role, book launch, baby)

Drop:
- Plain reshares with no commentary (`repost: true` and `post_text` is empty)
- Holiday/seasonal greetings
- Generic industry hot takes with no personal stake
- Pure marketing copy with no announcement underneath

## Step 6 — Output

For each person, render this exact structure:

```
## <Person Name> @ <Company Name>
LinkedIn: <person-li-url> • X: <person-x-url or "—">

### About <Person Name>
- <One-line finding>. — <Platform> · <YYYY-MM-DD> · [source](<post_url>)
- …

### About <Company Name>
LinkedIn: <company-li-url> • X: <company-x-url or "—">
- <One-line finding>. — <Platform> · <YYYY-MM-DD> · [source](<post_url>)
- …

### Briefing notes
2–3 sentences on what to bring up, congratulate, or ask about on the call. Cite the underlying finding in parentheses.
```

If a section is empty, write `Nothing notable in the last <N> days.` Don't pad with low-signal posts to look thorough.

Cite *every* claim. If you summarize across multiple posts, list each source URL.
