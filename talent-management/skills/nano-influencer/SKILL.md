---
name: nano-influencer
description: |
  Source creators via NanoInfluencer lookalike search. Use whenever the user wants to find creators similar to a known source (YouTube channel, X handle, or Instagram username), prospect new talent in a niche, expand an existing list of creators, or triage lookalikes by trailing performance. Typical triggers: "find creators like @mkbhd", "who are the lookalikes for theo", "find YouTubers similar to this channel", "prospect creators similar to [X]", "expand this list with lookalikes", "nanoinfluencer search", "run a similar search for [handle/URL]", anything that starts from one creator and asks for more.
  MANDATORY TRIGGERS: nanoinfluencer, nano influencer, nano-influencer, lookalike search, similar creators, find creators like, find similar channels, expand creator list, source creators, prospect creators, creators similar to, lookalikes for
---

# NanoInfluencer Sourcing

Find and triage lookalike creators using the NanoInfluencer MCP tools. This skill covers the full lookalike workflow: picking a source creator, running a similar-search, triaging results by trailing performance, and curating via favorite/hide flags so future searches sharpen over time.

For writing outreach copy to creators you've sourced, use `campaign-copywriting`. For handling pushback from creators you've already contacted, use `influencer-objection-handling`. This skill is specifically about finding them in the first place.

## When to use

- You have one creator (URL, handle, or channel ID) and want a list of similar creators
- You need to expand a niche list — add 20–30 new names in the same vibe as an existing shortlist
- You're vetting whether a creator has a deep bench of peers worth prospecting
- You want to shape future searches by marking winners/losers so nano learns the pattern

For keyword-based niche discovery (e.g. "all software-engineering creators over 50k"), reach for MightyScout's `mightyscout-search` instead — nano is source-based, not keyword-based.

## Search quota — treat it as scarce

NanoInfluencer caps at roughly **10 similar-searches per day**. Every `nanoinfluencer-submit-similar-search` call burns quota. Before submitting:

1. **Re-poll, don't resubmit.** A finished jobId can be polled forever for free. If you already have a jobId from earlier today, poll it again with the new `trailingWindow` instead of running a fresh search.
2. **Check projects first.** If the user has favorited creators in a project, `nanoinfluencer-list-projects` + `nanoinfluencer-get-flags` can surface prior work before you submit anything.
3. **Don't submit on every platform "just in case."** If the user names a YouTuber, search YouTube. Only fan out across platforms when explicitly asked or when the creator is known to be cross-platform.

## The workflow

### 1. Resolve the source creator

The user usually gives a URL or handle. Map it to `{platform, id}`:

| Platform | Code | ID format | From URL |
|---|---|---|---|
| YouTube | `ytb` | Channel ID starting with `UC...` | May require `nanoinfluencer-get-profile` with the handle first to resolve the UC id, or lift it from the channel page |
| X / Twitter | `twt` | Handle or numeric user id | `x.com/theo` → `theo` |
| Instagram | `ins` | Username | `instagram.com/jayvolp/` → `jayvolp` |

If the user hands over a YouTube vanity URL like `youtube.com/@mkbhd` or a display name, call `nanoinfluencer-get-profile` first to confirm the creator exists and lift the canonical `id` off the response.

### 2. Optionally scope to a project

`groupId` scopes server-side filtering so previously `hide`'d channels from that project won't reappear. Run `nanoinfluencer-list-projects` if the user mentions a list they've curated before ("the AI creator list", "the DevTools project"). Pass that project's `id` as `groupId` on submit.

If the user is starting cold, skip `groupId` — it defaults to the root project.

### 3. Submit the search

```
nanoinfluencer-submit-similar-search({
  platform: "ytb" | "twt" | "ins",
  id: "<creator id>",
  groupId: "<project id>",   // optional
  filters: { ... },          // optional — server-side pre-filter
  useShortsSearch: false,    // YouTube only
  pagination: { ... }        // optional — for page 2+
})
```

Returns `{ jobId, baseChannel, searchTopics }`. **Save the jobId** — you'll re-poll it if the user wants a different `trailingWindow` later.

**Filters — pass these when they match user intent:**
- `lastPostDays: 60` almost always. Drops stale channels.
- `hasEmail: true` when outreach is the downstream goal.
- `subs: [min, max]` when the user specified a size range (e.g. "mid-tier, 10k–500k").
- `includeCountries: [76]` / `excludeCountries: [840]` — ISO 3166-1 numeric codes, mutually exclusive.
- `gender: ["male","female"]` to exclude `"org"` / brand channels.
- `er` / `vr` ranges to filter over- or under-performers.

See `references/lookalike-workflow.md` for the full filter table and examples.

**`useShortsSearch: true`** (YouTube only) matches on the shorts feed instead of long-form. Use when the source creator's audience lives mainly in shorts.

**Pagination:** a finished poll returns a `pagination` block when more results exist — pass it back as `pagination` on a fresh submit to fetch the next page. Each page burns one quota slot.

You can override `searchTopics` with a flat `string[]` if you want to bias the search toward specific terms. **Usually don't.** The baseChannel embedding dominates ranking; custom topics are a weak secondary filter. The default (nano's auto-extracted `topic_terms`) is almost always the right call.

### 4. Poll with trailing metrics

```
nanoinfluencer-poll-similar-search({
  jobId: "<from step 3>",
  trailingWindow: 10  // almost always 10
})
```

The tool loops internally for ~24s. If `status: "running"` comes back, call it again with the same jobId. When finished, you get `channels[]` with per-channel `longTrailing` and `shortsTrailing` blocks.

**`trailingWindow` picking guide:**
- `10` is the default — matches how trailing is computed elsewhere in the pipeline. Use this unless the user asks otherwise.
- Smaller windows (3–5) show very recent momentum — useful for catching channels whose newest posts are blowing up but whose medians haven't caught up yet.
- Larger windows (20–30) smooth over recent spikes. Mostly useful for channels with high post cadence.

See `references/trailing-metrics.md` for how to read the numbers.

### 5. Triage

Hand the user a ranked table, not a dump. Default columns:

| Handle | Subs | Trailing avgViews | Trailing ViewRate | Trailing ER | Top topic |

Sort by whatever the user cares about — usually `longTrailing.avgViews` (absolute reach) or `longTrailing.viewRate` (over-performance vs follower count). Call out anomalies explicitly:

- Very high viewRate (>50% on YouTube, >100% on IG) — creator is overperforming relative to subs, often because reels/shorts hit. Still useful but expect lower email-list value.
- `reliable: false` — fewer than 3 posts in the window. Flag it; don't rank these.
- `lastPostDays > 30` — likely inactive, deprioritize.
- `email: []` — no contact info, harder to reach out.

### 6. Curate via flags

After triage, use `nanoinfluencer-set-flags` to:
- **`fav`** — mark winners so future searches (scoped to this project) know what "good" looks like
- **`hide`** — exclude obvious misses so they stop reappearing in this project's future searches
- **`del`** — clear a previously set flag

Per-project cap is 100 favorited or hidden channels. See `references/flag-management.md`.

## Triage principles

- **Filter by `reliable: true` first.** A trailing number over <3 posts is noise.
- **ViewRate beats raw Subs for prospecting.** A 20k-sub channel with 90% viewRate is often a better partner than a 500k-sub channel with 3% viewRate — they're punching above their weight and their audience is actually watching.
- **Cross-check `similarity` against `match_topic`.** Nano reports how it matched (e.g. `"_base_channel_"` means the embedding matched directly; a specific topic name means the match came through that topic). Base-channel matches are usually the strongest signal.
- **Topics are flavoring, not ground truth.** Two channels can share topics but one covers them from a consumer angle and the other from a B2B angle. Glance at the `topic_terms` to sanity-check before adding to a campaign.
- **`email` array has types.** `MATCHED` > `PUBLIC` > `IN PUBLIC` > `TWT DM` > `REVEAL BUTTON` in reliability. Empty means you'll need another route (manager, DM, site contact form).

## References

- `references/lookalike-workflow.md` — full submit/poll mechanics with concrete examples across platforms
- `references/trailing-metrics.md` — how trimmed-mean trailing numbers are computed and how to read them vs nano's own medians
- `references/flag-management.md` — favoriting, hiding, and project scoping to make future searches sharper

## Do not

- Submit a fresh search just to retry with a different `trailingWindow` — re-poll the existing jobId
- Pass a flat `searchTopics` override unless the user explicitly asked to bias the search
- Burn quota fanning out across platforms — stay on the source creator's platform unless told otherwise
- Recommend creators with `reliable: false` trailing — caveat the numbers or exclude them
- Treat nano's `erMedian` and your trailing `engagementRate` as the same thing; they use different denominators (see `references/trailing-metrics.md`)
