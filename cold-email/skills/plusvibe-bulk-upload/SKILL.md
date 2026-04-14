---
name: plusvibe-bulk-upload
description: |
  Bulk-upload leads (typically 50+, up to several thousand) to a PlusVibe campaign via the
  direct REST API using a local Python script with parallel batched requests. Use this skill
  whenever the user needs to push a large lead list into PlusVibe and the MCP tool would be
  too slow or would hit payload-size limits — even if the user doesn't explicitly say "bulk"
  or "script". Typical triggers: "upload all these leads to plusvibe", "push this CSV into
  the campaign", "add 300 contacts to [campaign name]", "sync my account ladder to plusvibe",
  "load this list into plusvibe", or any time a CSV/JSON of ~50+ leads needs to land in a
  PlusVibe campaign. For small batches (<25 leads, ad-hoc), prefer the `plusvibe-leads`
  skill which uses the MCP tool directly. This skill is specifically for the high-volume
  workflow where a local script is the right tool.
---

# PlusVibe Bulk Lead Upload

Push large lead lists into a PlusVibe campaign via the `/lead/add` REST endpoint, running
the script on the user's local machine (not the sandbox). The sandbox lacks outbound
internet, so this workflow intentionally hands execution to the user's terminal.

## When to use this vs. `plusvibe-leads`

- **`plusvibe-leads` (MCP)** — 1-25 leads, ad-hoc adds, exploratory work. The MCP tool is
  faster for small counts and requires no install.
- **This skill** — 50+ leads, or any time MCP batches are rejected because the payload is
  too large. The direct REST API has no such limit and parallelism makes it fast.

If the user is uploading a whole CSV of an account ladder / campaign prep output, this is
almost always the right skill.

## Prerequisites

Before running, confirm you have (or collect from the user):

1. **PlusVibe API key** — format like `xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx`. If not
   provided, ask the user; they can find it in PlusVibe → Settings → API.
2. **workspace_id** — from `get_workspaces` MCP call, or previously known.
3. **campaign_id** — from `list_campaigns` for the workspace, or previously known.
4. **The lead data** — usually a CSV at a known path in the user's workspace folder.

## Workflow

### Step 1: Prepare a `leads.json` file

The script expects a JSON file: a list of lead objects, each with PlusVibe-native root
fields plus a `custom_variables` dict. See `references/lead_schema.md` for the full schema
and the standard CSV→JSON mapping used across FundLevel campaigns.

Build this file from the user's CSV. Write a short Python snippet inline (don't make a
separate helper script — it's one-shot). Save the result somewhere in the user's workspace
folder (e.g. alongside the script, or in `/tmp/` on the user's Mac — but prefer the
workspace folder so the path is stable).

### Step 2: Copy the upload script into the user's workspace

The script at `scripts/upload_leads.py` is a template with three values to fill in:
`API_KEY`, `WORKSPACE_ID`, `CAMPAIGN_ID`. Everything else is generic.

Copy it to the user's workspace folder and edit those three constants. Also confirm:

- `BATCH_SIZE = 25` is a good default (PlusVibe handles it fine; smaller only if payloads
  are unusually large).
- `START_INDEX = 0` unless you're resuming a partial upload.
- The `open(...)` call at the top of `main()` points at the right JSON path.

### Step 3: Condense `custom_variables` if the payload is large

PlusVibe accepts arbitrary custom variables, but large lead lists with ~70+ custom fields
each can make individual batch payloads heavy. The script includes a `KEY_CV` allowlist of
the ~28 fields FundLevel actually uses in sequences. The `condense_lead` function filters
each lead down to just those fields before sending.

If the user's custom fields are different, update `KEY_CV` to match what their email
templates reference. If the user has no custom_variables to worry about, you can drop the
condense step entirely — just send `leads[i:i+BATCH_SIZE]` directly.

### Step 4: Give the user a one-line terminal command

The sandbox can't reach `api.plusvibe.ai` directly. The user runs the script themselves.

For macOS with Homebrew Python (the common case — system Python refuses `pip install`
without `--break-system-packages`):

```
cd ~/Desktop/"Campaign prep" && pip3 install aiohttp --break-system-packages --user --quiet && python3 upload_leads.py
```

If the user prefers to avoid `--break-system-packages`, offer the venv alternative:

```
cd ~/Desktop/"Campaign prep" && python3 -m venv .venv && source .venv/bin/activate && pip install aiohttp --quiet && python3 upload_leads.py
```

**Common gotcha:** if you scripted the JSON path as `/tmp/leads.json` but saved the JSON
into the workspace folder, the user will hit `FileNotFoundError`. Either patch the path
with a `sed` step in the command, or use a workspace-relative path from the start:

```
sed -i '' "s|/tmp/leads.json|leads.json|" upload_leads.py
```

### Step 5: Verify the upload

Once the user pastes back the script output, confirm all batches returned
`status=success` and the totals add up. Then verify via MCP:

```
get_lead_count(workspace_id, campaign_id)
```

The sum across all statuses should increase by the number of leads just uploaded (or less,
if any were already in the campaign and got overwritten).

## Example output

A successful run looks like this:

```
Total leads in file: 389
Uploading indices 0–388 (389 leads)
Batch size: 25  Total batches: 16

Batch 0 (a@x.com … p@y.com): status=success uploaded=25 overwritten=0 total_sent=25 (1.1s)
Batch 25 (q@x.com … b@y.com): status=success uploaded=25 overwritten=0 total_sent=25 (1.0s)
... [parallel, so order is non-sequential]

============================================================
DONE: 389 sent | 388 new | 1 overwritten | 0 errors
============================================================
```

The 1 "overwritten" in this example means one lead was already in the campaign and got
updated in place — that's fine and expected when `is_overwrite: True`.

## Troubleshooting

**`externally-managed-environment` on pip install** — macOS + Homebrew Python enforces
PEP 668. Use `--break-system-packages --user` or a venv. See Step 4.

**`FileNotFoundError: /tmp/pv_only_primary.json`** — the script was written with a
sandbox-local path that doesn't exist on the user's Mac. Patch with `sed` (see Step 4) or
rewrite the path before handing the command to the user.

**`Temporary failure in name resolution` / `Cannot connect to host api.plusvibe.ai`** —
you're running the script in the sandbox, not on the user's machine. The sandbox has no
outbound DNS. Give the user the terminal command instead of trying to run it here.

**Batch returns `status=error` with a 4xx** — most often a missing required field (email)
or a malformed `custom_variables` value. Log the full `data` dict from the failed batch
and fix the lead row; the rest of the batches will have already succeeded, so just
re-upload the fixed slice with `START_INDEX` set appropriately.

**Batch times out** — lower `BATCH_SIZE` to 10 or reduce semaphore concurrency from 6 to
3. PlusVibe occasionally throttles under heavy parallel load.

## Why this workflow

The sandbox's lack of outbound internet forced us into a split-responsibility pattern: the
sandbox prepares the data + script, the user's terminal does the network I/O. This is
actually a nice property — the user can audit the exact payload going out, re-run without
re-prompting the model, and the script becomes a durable artifact they can reuse for
future campaigns by just swapping `CAMPAIGN_ID` and the input JSON.

## Reference files

- `scripts/upload_leads.py` — the parameterized upload script. Copy, edit the three
  constants, give to the user to run.
- `references/lead_schema.md` — PlusVibe's `/lead/add` payload schema (root fields vs.
  `custom_variables`) and the standard FundLevel CSV→JSON mapping.
- `references/api.md` — raw REST endpoint details (URL, headers, response shape).
