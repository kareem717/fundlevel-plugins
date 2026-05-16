---
name: check-prospect-news
description: |
  Build a pre-call briefing for a prospect by pulling their and their company's recent LinkedIn + X posts via Bright Data, then summarizing what's news-worthy with cited URLs. Use when the user provides a prospect (email, name, LinkedIn URL, X handle, or company name) and asks to "check news", "what's new with X", "research before a call", "recent activity from", "prep for a meeting with", or wants a briefing on a prospect. Looks the prospect up in Attio first to resolve their LinkedIn/X handles and their company's handles, then delegates the fetch + filter + summary to the `account-exec:prospect-news-researcher` subagent.
---

# Check Prospect News

You do the Attio lookup; the subagent does the heavy fetching and summarization. Keep your part light.

## Step 1 — Resolve the prospect in Attio

Take whatever the user gave (email, name, LinkedIn URL, X handle, company). Run `mcp__claude_ai_Attio__search-records` on the `people` object.

- One strong match → continue with that record.
- Multiple plausible matches → list candidates as `{name, title, company.name}` and ask the user to pick.
- No people match → search the `companies` object. If found, confirm with the user whether they want a company-only briefing or want to identify a specific person.

If attribute slugs aren't obvious from the result, call `mcp__claude_ai_Attio__list-attribute-definitions` on `people` and `companies` once to discover them.

## Step 2 — Extract URLs

From the person record, read:
- `linkedin` → person LinkedIn URL
- `twitter` / `x` → person X URL
- linked `company` reference → fetch with `mcp__claude_ai_Attio__get-records-by-ids`, then read its `linkedin` and `twitter`/`x`

Normalize: `https://` scheme, lowercase host, strip query/trailing slash, convert `twitter.com` → `x.com`. Drop anything that doesn't match `linkedin.com/in/...`, `linkedin.com/company/...`, or `x.com/...`.

You'll have up to four URLs (person-LI, person-X, company-LI, company-X). Any missing one → pass as `none` to the subagent.

## Step 3 — Pick a date window

Default to the last 30 days from today. If the user specified a window ("past week", "since Q1"), use that.

## Step 4 — Delegate to the subagent

Invoke the Agent tool with `subagent_type: "account-exec:prospect-news-researcher"` and a prompt in this exact shape:

```
Person: <name> — <title>
Company: <company name>
Person LinkedIn: <url or "none">
Person X:        <url or "none">
Company LinkedIn: <url or "none">
Company X:        <url or "none">
Date window: <YYYY-MM-DD> to <YYYY-MM-DD>
```

If the user asks about multiple prospects at once, send all subagent invocations in **one message** with parallel Agent tool calls — the fetches will run concurrently.

## Step 5 — Pass the result through

Print the subagent's output verbatim. Don't reformat, don't add a preamble. If the user follows up with questions ("dig deeper on the Series B"), you can either answer from the cited URLs (read them via Bash + curl) or send a fresh subagent invocation with the narrower scope.
