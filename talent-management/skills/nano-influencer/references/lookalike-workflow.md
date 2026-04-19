# NanoInfluencer Lookalike Workflow

Step-by-step mechanics for running a similar-search end to end. Pair this with the main SKILL.md for when-to-use guidance.

## Tool inventory

| Tool | Purpose | Free or quota? |
|---|---|---|
| `nanoinfluencer-get-profile` | Fetch one creator's profile + pre-extracted topic terms | Free |
| `nanoinfluencer-submit-similar-search` | Kick off a lookalike search, returns a jobId | **Burns daily quota** (~10/day) |
| `nanoinfluencer-poll-similar-search` | Poll a jobId, returns running or the full channel list | Free (poll finished jobs as many times as you want) |
| `nanoinfluencer-list-projects` | List projects. Each project id is the `groupId` for flag scoping | Free |
| `nanoinfluencer-create-project` | Create a new project folder | Free |
| `nanoinfluencer-get-flags` | Read fav/hide/label state for channels | Free |
| `nanoinfluencer-set-flags` | Set fav/hide/del on channels | Free |

## Platform IDs — how to resolve them from a URL

NanoInfluencer's creator id is platform-specific:

- **YouTube** — the UC-prefixed channel id (e.g. `UCDUdeFslCNoM29MAlZOfdWQ`). Handle URLs like `youtube.com/@mkbhd` need to be resolved first. The easiest path: call `nanoinfluencer-get-profile({ platform: "ytb", id: "@mkbhd" })` — nano's profile endpoint resolves handles internally and the response comes back with the canonical `id`.
- **X / Twitter** — the handle (e.g. `theo` from `x.com/theo`). Drop any leading `@`.
- **Instagram** — the username (e.g. `jayvolp` from `instagram.com/jayvolp/`). Drop the trailing slash.

If the user pastes a URL, strip the protocol and path, then map the remaining identifier.

## Full example: "find creators similar to @theo on X"

```
# 1. Optional: confirm the profile and check topic terms
nanoinfluencer-get-profile({ platform: "twt", id: "theo" })
# → { id: "theo", name: "Theo - t3.gg", topic_terms: [...] }

# 2. Submit the search
nanoinfluencer-submit-similar-search({
  platform: "twt",
  id: "theo"
})
# → { jobId: "1b840119-...", baseChannel: {...}, searchTopics: [...] }

# 3. Poll until finished
nanoinfluencer-poll-similar-search({
  jobId: "1b840119-...",
  trailingWindow: 10
})
# First call may return { status: "running" } — call again with same jobId.
# Finished: { status: "finished", channels: [...] }
```

## Full example: YouTube with a handle URL

```
# User pastes: https://youtube.com/@hdeleon

# 1. Resolve handle to UC id
nanoinfluencer-get-profile({ platform: "ytb", id: "@hdeleon" })
# → { id: "UCDUdeFslCNoM29MAlZOfdWQ", name: "hdeleon.net", ... }

# 2. Submit with the canonical id
nanoinfluencer-submit-similar-search({
  platform: "ytb",
  id: "UCDUdeFslCNoM29MAlZOfdWQ"
})

# 3. Poll. YouTube responses include shortsTrailing in addition to longTrailing.
nanoinfluencer-poll-similar-search({ jobId, trailingWindow: 10 })
```

## Full example: scoped to a curated project

If the user has been curating a list (e.g. "AI dev creators"), pass the project's id as `groupId`. Previously `hide`'d channels in that project will be filtered server-side.

```
# 1. Find the project
nanoinfluencer-list-projects()
# → { projects: [{ id: 42, title: "AI dev creators" }, ...] }

# 2. Submit scoped to it
nanoinfluencer-submit-similar-search({
  platform: "twt",
  id: "theo",
  groupId: "42"
})

# 3. Same poll as before. Past hides from project 42 won't reappear.
```

## Server-side filters

`nanoinfluencer-submit-similar-search` accepts a `filters` object that nano applies **before** lookalike matching. Every field is optional — pass only what you need.

| Filter | Type | Example | What it does |
|---|---|---|---|
| `lastPostDays` | int | `60` | Drop channels whose most recent post is older than N days. Almost always want this — default to `60`. |
| `hasEmail` | bool | `true` | Only channels nano has an email for. Use when the user plans to cold-email the results. |
| `gender` | `("male"\|"female"\|"neutral"\|"org")[]` | `["male","female"]` | Inferred creator gender. `org` = brand/company channel — exclude for influencer outreach. |
| `includeCountries` | int[] | `[76]` | ISO 3166-1 numeric country codes to restrict to. Mutex with `excludeCountries`. |
| `excludeCountries` | int[] | `[840, 826]` | ISO 3166-1 numeric codes to exclude (840=US, 826=UK, 392=JP, 76=BR). Mutex with `includeCountries`. |
| `subs` | `[min, max]` | `[4000, 4000000]` | Subscriber count range. |
| `views` | `[min, max]` | `[12000, 120000]` | Median views range. |
| `posts` | `[min, max]` | `[10, 500]` | Total post count. Low `posts` = new channel. |
| `er` | `[min, max]` | `[10, 90]` | Engagement rate as percent. |
| `vr` | `[min, max]` | `[1, 100]` | View rate (views/subs) as percent. Filters over/under-performers. |

Example — dev creators in Brazil with email and subs 4k–4M:

```
nanoinfluencer-submit-similar-search({
  platform: "ytb",
  id: "UCDoFiMhpOnLFq1uG4RL4xag",
  filters: {
    lastPostDays: 60,
    hasEmail: true,
    includeCountries: [76],
    subs: [4000, 4000000],
    er: [1, 90]
  }
})
```

## YouTube shorts-only matching

Pass `useShortsSearch: true` to make nano match on the shorts feed instead of long-form. Rejected for X and Instagram.

Use when the source creator's audience is primarily on shorts — the base embedding shifts to shorts signals so lookalikes skew toward shorts creators.

```
nanoinfluencer-submit-similar-search({
  platform: "ytb",
  id: "UCxxxxxx",
  useShortsSearch: true
})
```

## Pagination — fetching more results

A finished poll returns a `pagination` block when more results exist:

```json
{
  "status": "finished",
  "channels": [...52 channels],
  "pagination": {
    "nextToken": "ytb:cbf0e0c1-...",
    "nextIds": [...44 ids],
    "returnedIds": [...52 ids],
    "hint": "Pass { nextToken, nextIds, excludeIds: [...prior excludeIds, ...returnedIds] } ..."
  }
}
```

To get the next page: submit again with the same params plus `pagination`.

**Important:** each page submit **burns daily quota** like any other search. Only paginate if the first page didn't surface enough candidates.

Accumulate `excludeIds` across pages so duplicates don't reappear:

```
# page 2
nanoinfluencer-submit-similar-search({
  platform: "ytb",
  id: "UCxxxxxx",
  filters: { lastPostDays: 60, hasEmail: true },
  pagination: {
    nextToken: page1.pagination.nextToken,
    nextIds:   page1.pagination.nextIds,
    excludeIds: page1.pagination.returnedIds
  }
})

# page 3 — accumulate excludeIds across both prior pages
nanoinfluencer-submit-similar-search({
  ...
  pagination: {
    nextToken: page2.pagination.nextToken,
    nextIds:   page2.pagination.nextIds,
    excludeIds: [...page1.pagination.returnedIds, ...page2.pagination.returnedIds]
  }
})
```

If `pagination: null` on a finished poll, you've exhausted the result set.

## Polling gotchas

- The tool loops internally for ~24s. If you get `status: "running"`, that means nano is still crunching — call the tool again with the same jobId. A search typically finishes within 30–90s.
- Once a job is `finished`, you can re-poll it with a different `trailingWindow` without burning quota. The trailing computation is client-side.
- If a poll returns `channels: []` but `status: "finished"`, the source creator probably has too little content for nano to find lookalikes. Rare but happens on very new accounts.

## `searchTopics` override — when (not) to use

The default behavior uses the source creator's auto-extracted `topic_terms`. This is almost always correct.

Override with a flat `string[]` only if:
- The source creator covers multiple niches and you want to bias toward one
- You're explicitly hunting for a specific angle the base creator isn't known for

Even then: the baseChannel embedding dominates ranking. Custom topics are a weak secondary filter. If you need strong topic control, consider whether `mightyscout-search` (keyword-based) is actually the right tool instead.

```
# Biasing Theo's search toward infra angle specifically
nanoinfluencer-submit-similar-search({
  platform: "twt",
  id: "theo",
  searchTopics: ["infrastructure", "devops", "kubernetes", "cloud"]
})
```

## Output shape after poll

Each channel in the finished response looks like:

```json
{
  "id": "UCDUdeFslCNoM29MAlZOfdWQ",
  "name": "hdeleon.net",
  "platform": "ytb",
  "username": "hdeleonnet",
  "url": "https://youtube.com/channel/UCDUdeFslCNoM29MAlZOfdWQ",
  "countryCode": "484",
  "lang": "",
  "similarity": 86,
  "match_topic": "_base_channel_",
  "subsCount": "222000",
  "postCount": "1365",
  "postPerMonth": 8,
  "erMedian": 0.004,
  "vrMedian": 0.048,
  "likesMedian": 890,
  "viewsMedian": 10690,
  "lastPostDate": "2026-04-14T18:38:53+00:00",
  "lastPostDays": 0,
  "email": [{ "type": "MATCHED", "value": "******@gmail.com" }],
  "topics": ["Programming", "Technology", "Software Development"],
  "topic_terms": [{ "topic": "...", "terms": [...] }],
  "longTrailing": {
    "window": 10,
    "videosUsed": 8,
    "reliable": true,
    "avgViews": 15908,
    "viewRate": 7.17,
    "engagementRate": 8.49
  },
  "shortsTrailing": { ... } | null
}
```

`longTrailing` and `shortsTrailing` only appear when `trailingWindow` was passed. `shortsTrailing` is always `null` on X/Twitter and Instagram — those platforms don't split shorts from long-form the way YouTube does.

## Presenting results to the user

Don't dump the raw JSON. Build a ranked table with:

| Handle | Subs | Trailing avgViews | ViewRate | ER | Top topic | Email |

Sort by whichever signal matches the user's goal. Call out `reliable: false` rows explicitly or exclude them. Note `lastPostDays > 30` as "may be inactive".

Ask the user which creators they want to favorite or hide before moving on to outreach — this sets up the next search in the same project to be sharper.
