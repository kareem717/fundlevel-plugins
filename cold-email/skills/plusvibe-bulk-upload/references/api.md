# PlusVibe `/lead/add` REST API

## Endpoint

```
POST https://api.plusvibe.ai/api/v1/lead/add
```

## Headers

```
x-api-key: <your-api-key>
Content-Type: application/json
```

The API key is workspace-scoped. Find it in PlusVibe → Settings → API. Format is four
8-char segments joined with dashes: `xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx`.

## Request body

```json
{
  "workspace_id": "685f76d3c06c039e5516c3f9",
  "campaign_id":  "69810e6cabce405388b1654a",
  "is_overwrite": true,
  "leads": [
    {
      "email": "jane@example.com",
      "first_name": "Jane",
      "last_name": "Doe",
      "job_title": "Director of Marketing",
      "company_name": "Example Corp",
      "company_website": "example.com",
      "linkedin_person_url": "https://linkedin.com/in/janedoe",
      "linkedin_company_url": "https://linkedin.com/company/example",
      "custom_variables": {
        "entry_id": "abc-123",
        "ladder_rank": "1",
        "buyer_type": "Economic Buyer"
      }
    }
  ]
}
```

Notes:

- `workspace_id` and `campaign_id` are both required. Get them from the `get_workspaces`
  and `list_campaigns` MCP tools, or from the PlusVibe UI URL.
- `leads` is an array; one request can carry many leads. 25 per request is a comfortable
  default. The upper limit is generous (hundreds work) but payload size grows linearly so
  very fat custom_variables dicts will push request times up.
- `is_overwrite: true` updates existing leads in-place; `false` skips them.

## Response

```json
{
  "status": "success",
  "leads_uploaded": 24,
  "overwritten": 1,
  "total_sent": 25
}
```

Where:

- `status` — `"success"` when the request was accepted. Errors come back with a `message`
  field and a 4xx/5xx HTTP code.
- `leads_uploaded` — number of newly created leads.
- `overwritten` — number of existing leads that got updated (only nonzero when
  `is_overwrite: true`).
- `total_sent` — should equal the length of `leads` in the request. If it's less, a row
  was rejected (usually bad email format).

## Parallelism

PlusVibe tolerates moderate parallelism well. The upload script uses an asyncio semaphore
with `CONCURRENCY=6`. Empirically this keeps per-batch round-trip under ~1.2s for
25-lead batches. Push higher only if you're uploading tens of thousands and need the
throughput — otherwise 6 is fine and friendlier to their infra.

## Error modes seen in the wild

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong `x-api-key` or key from a different workspace | Regenerate in Settings → API, make sure it matches `workspace_id` |
| `400` with "invalid email" | Email field malformed or empty | Clean the CSV; drop empties |
| `total_sent < len(leads)` | One or more leads silently dropped (usually email issue) | Log the batch, inspect the emails, fix and re-upload that slice |
| `Cannot connect to host` / DNS failure | Running from a sandbox with no outbound internet | Run the script on the user's local machine |
| Slow responses (>10s) | Large payloads + high concurrency | Drop `BATCH_SIZE` to 10-15 and/or `CONCURRENCY` to 3 |
