# Trailing Metrics — How to Read the Numbers

When you poll with `trailingWindow: N`, nano-poll attaches a `longTrailing` and `shortsTrailing` block to each channel. Both use the same formula, computed over the newest-N posts from that channel's feed.

## What's in the block

```json
{
  "window": 10,        // the N you passed in
  "videosUsed": 8,     // post count after trimming min/max
  "reliable": true,    // false when videosUsed < 3
  "avgViews": 15908,   // trimmed-mean views over videosUsed posts
  "viewRate": 7.17,    // avgViews / subsCount * 100, rounded to 2 dp
  "engagementRate": 8.49  // trimmed-mean of per-post (likes+comments)/views * 100
}
```

## How it's computed

Mirrors the trimmed-mean SOP from the jobs pipeline (`packages/jobs/src/lib/rapid-youtube.ts`):

1. Take the newest N posts from the feed (`recentPosts` for `longTrailing`, `shortsData.recentPosts` for `shortsTrailing`).
2. Depending on count:
   - **0 posts** → block is `null`
   - **1 post** → plain value, `reliable: false`, `videosUsed: 1`
   - **2 posts** → simple average, `reliable: false`, `videosUsed: 2`
   - **3 posts** → simple average, `reliable: true`, `videosUsed: 3`
   - **4+ posts** → drop the highest and lowest by view count, then average the rest, `reliable: true`, `videosUsed: N-2`
3. `viewRate = avgViews / subsCount * 100`. Returns `null` if `subsCount <= 0`.
4. `engagementRate` is computed per post as `(likes + comments) / views * 100`, then trimmed-mean aggregated across the window.

The min/max drop (step 2, 4+ case) is **by view count**, applied to the views series. The engagement-rate aggregation runs the same trimming on the per-post ER series.

## `longTrailing` vs `shortsTrailing`

| Platform | `longTrailing` source | `shortsTrailing` source |
|---|---|---|
| YouTube | Long-form feed (`recentPosts`) | Shorts feed (`shortsData.recentPosts`) |
| X / Twitter | Main post feed (`recentPosts`) | Always `null` |
| Instagram | Main feed (`recentPosts`) | Always `null` |

On YouTube, compare the two blocks side by side. A creator with strong `longTrailing` but weak `shortsTrailing` monetizes through long-form; the reverse signals a viral-shorts channel where long-form is an afterthought. For brand sponsorship placement, `longTrailing` usually matters more — integrations live in long-form.

## Reading the numbers

### `avgViews`
Absolute reach per post, smoothed. Best single signal for "how many eyeballs does this creator put on a sponsor".

### `viewRate` — over/underperformance vs follower count
Percentage of the creator's subscribers that watch a typical recent post.

- **YouTube**: healthy is 2–10%. Above 15% is strong. Above 30% is either a tiny channel (where every sub actually watches) or a viral window. Under 2% is a dormant audience.
- **Instagram**: numbers run much higher because reels reach far beyond followers. 50–200% is common. 500%+ means the creator is landing viral reels that dwarf their follower count — great reach, but note the audience-match may be looser than subs imply.
- **X / Twitter**: all over the map. Subscribers on X are a weak denominator; treat viewRate here as a soft signal, not a primary filter.

### `engagementRate`
`(likes + comments) / views * 100`, trimmed-mean. Measures how sticky the content is — are viewers reacting, or just scrolling past?

- **1–3%** is normal.
- **5%+** is strong — the audience is actively engaged.
- **Under 0.5%** usually means the creator is getting views from algo surfacing rather than a loyal audience.

### `reliable: false`
Skip these in ranking. `videosUsed < 3` means the trimmed mean is noise — either the creator has almost no content, or the feed sample is too small.

## `engagementRate` vs nano's `erMedian` — different denominators

Nano's top-level `erMedian` on each channel is **not** the same metric as our computed `engagementRate`. They use different denominators:

| Metric | Denominator | Example (hdeleon.net) |
|---|---|---|
| Nano's `erMedian` | Subscribers (`(likes + comments) / subsCount`) | 0.004 → 0.4% |
| Our `engagementRate` | Views (`(likes + comments) / views`) | 8.5% |

Both are valid; they answer different questions. Nano's is "how engaged is the subscriber base". Ours is "how sticky are individual videos". Don't compare the two numbers directly. Our `engagementRate` matches the pipeline's SOP and is what the brand team uses.

Nano's `vrMedian` and our `viewRate` do line up — both are `views / subs` scaled. You can use `vrMedian` as a sanity check on the trailing `viewRate`. They won't match exactly (nano uses medians, we use trimmed means) but magnitudes should agree.

## Picking `trailingWindow`

| Window | Use case |
|---|---|
| `10` | **Default.** Matches pipeline. Use this unless there's a reason not to. |
| `3`–`5` | Catch short-term momentum. Useful for spotting channels whose recent posts are trending up but whose medians haven't caught up. Expect more `reliable: false` on sparse feeds. |
| `15`–`20` | Smooth over spikes. Good for high-cadence channels (30+ posts/month) where 10 posts is a week of content. |
| `25`–`30` | Roughly a month for daily posters. Use when the user wants a stable baseline for negotiation leverage. |

Going above 30 isn't allowed (schema cap). Going below 1 isn't either. If the user asks for "last week" or "last month", translate to a post count based on the creator's `postPerMonth` — e.g. daily posters → window 7 for a week.

## When the trailing block is missing or weird

- **Block is `null`** — creator has zero posts of that type in nano's cache. Shorts often `null` for channels that don't post shorts.
- **`avgViews: 0`** — the creator posts but views are null/zero in the source data (private channel, fresh uploads not yet indexed).
- **`viewRate: null`** — `subsCount` is 0 or missing. Still useful to show `avgViews` and `engagementRate`, but note the viewRate can't be computed.
- **`engagementRate: 0`** — either genuinely no engagement, or nano's data for likes/comments is zero/missing. On very small creators both happen; trust the data but caveat it.
