# Bright Data datasets

All three jobs go through `POST https://api.brightdata.com/datasets/v3/trigger?...`. The wrapper script handles auth, polling, and the `custom_output_fields` URL param — you only need to assemble the request body and pass it to `bd_fetch.sh`.

## LinkedIn person posts

- **dataset_id:** `gd_lyy3tktm25m4avu764`
- **discover_by:** `profile_url`
- **field list:** `fields-profile_url.txt`
- **input body:**

```json
{
  "input": [
    {
      "url": "https://www.linkedin.com/in/<handle>",
      "start_date": "2026-04-16T00:00:00.000Z",
      "end_date":   "2026-05-16T00:00:00.000Z"
    }
  ]
}
```

`start_date`/`end_date` are ISO 8601 with a `Z` suffix. The dataset returns posts authored by the profile within the window.

## LinkedIn company posts

- **dataset_id:** `gd_lyy3tktm25m4avu764` (same as person)
- **discover_by:** `company_url`
- **field list:** `fields-company_url.txt`
- **input body:**

```json
{
  "input": [
    { "url": "https://www.linkedin.com/company/<slug>" }
  ]
}
```

No date filter is supported on this discover mode. To cap response size, append `&limit_per_input=50` to the trigger URL — adjust if you need more depth. The wrapper script does **not** do this for you; if you need a limit, edit the trigger URL inline in `bd_fetch.sh` or add a fifth arg.

## X (Twitter) profile recent posts

- **dataset_id:** `gd_lwxkxvnf1cynvib9co`
- **discover_by:** `profile_url_most_recent_posts`
- **field list:** `fields-profile_url_most_recent_posts.txt`
- **input body:**

```json
{
  "input": [
    {
      "url": "https://x.com/<handle>",
      "start_date": "2026-04-16",
      "end_date":   "2026-05-16"
    }
  ]
}
```

Plain `YYYY-MM-DD` dates (no time component). Works for company X profiles too — Bright Data doesn't distinguish.

## Response shape

Every snapshot returns a JSON array. Field names match the `custom_output_fields` list.

### LinkedIn posts (person + company)

```json
{
  "url": "https://www.linkedin.com/posts/...",
  "date_posted": "2026-05-10T14:23:00Z",
  "post_text": "We just closed our Series B...",
  "post_type": "post",
  "num_likes": 412,
  "num_comments": 38,
  "hashtags": ["#funding"],
  "embedded_links": ["https://techcrunch.com/..."],
  "external_link_data": { "title": "...", "url": "..." },
  "repost": false,
  "user_posted": "Jane Smith",
  "headline": "VP Marketing at Acme",
  "tagged_companies": [],
  "tagged_people": [],
  "user_title": "VP Marketing",
  "user_id": "..."
}
```

A `null` or empty `post_text` with `repost: true` means the author shared someone else's post without commentary — usually low signal.

### X posts

```json
{
  "url": "https://x.com/jsmith/status/...",
  "date_posted": "2026-05-12T09:11:00Z",
  "description": "Excited to announce...",
  "user_posted": "jsmith",
  "name": "Jane Smith",
  "likes": 88,
  "replies": 4,
  "reposts": 21,
  "views": 9100,
  "hashtags": [],
  "external_url": "https://acme.com/blog/...",
  "quoted_post": null,
  "tagged_users": [],
  "photos": [],
  "videos": [],
  "bookmarks": 7,
  "quotes": 1
}
```

`description` is the tweet body for X (Bright Data's naming). `quoted_post` will be present when the tweet quote-retweets another tweet — useful for context.

## Error handling

The script exits non-zero on:
- Missing `BRIGHTDATA_API_KEY` (exit 2)
- Missing field list file (exit 2)
- No `snapshot_id` returned from trigger (exit 1)
- Snapshot status `failed` (exit 1)
- Snapshot still pending after 10 min (exit 1)

A successful snapshot with zero rows is *not* an error — it just means there's no qualifying activity in the window. Output file will be `[]`.
