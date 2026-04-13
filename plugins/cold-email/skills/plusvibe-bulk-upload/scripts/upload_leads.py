#!/usr/bin/env python3
"""
Bulk-upload leads to a PlusVibe campaign via the /lead/add REST endpoint.

Edit the three constants below (API_KEY, WORKSPACE_ID, CAMPAIGN_ID) and make sure
the path in main() points to your leads JSON file. Requires `aiohttp`.

Run locally (the sandbox can't reach api.plusvibe.ai):
    pip3 install aiohttp --break-system-packages --user --quiet && python3 upload_leads.py
"""

import json
import time
import asyncio
import aiohttp

# -----------------------------------------------------------------------------
# CONFIG — fill these in
# -----------------------------------------------------------------------------
API_KEY = "PLUSVIBE_API_KEY_HERE"
WORKSPACE_ID = "WORKSPACE_ID_HERE"
CAMPAIGN_ID = "CAMPAIGN_ID_HERE"

API_URL = "https://api.plusvibe.ai/api/v1/lead/add"
BATCH_SIZE = 25          # PlusVibe handles 25 comfortably. Lower if payloads are huge.
START_INDEX = 0          # Set to N to resume after a partial upload
CONCURRENCY = 6          # Parallel batches. Lower to 3 if you see throttling.
LEADS_JSON_PATH = "leads.json"  # Relative to wherever you run the script

# -----------------------------------------------------------------------------
# Custom-variable allowlist
# -----------------------------------------------------------------------------
# Filters each lead's custom_variables down to just the fields your email templates
# actually use. Reduces payload size substantially for large uploads. If you have no
# custom_variables (or want to send all of them), set KEY_CV = None.
KEY_CV = [
    'entry_id',
    'parent_record_name_first', 'parent_record_name_last',
    'parent_record_job_title', 'parent_record_company_name',
    'parent_record_company_domains', 'parent_record_company_linkedin',
    'parent_record_linkedin',
    'sponsorship_primary_youtube_video',
    'sponsorship_primary_youtube_video_youtube_url',
    'sponsorship_primary_youtube_video_published_at',
    'sponsorship_primary_youtube_video_influencer_name',
    'sponsorship_primary_type', 'sponsorship_primary_company',
    'sponsorship_primary_company_domains',
    'sponsorship_subsidiary_youtube_video',
    'sponsorship_subsidiary_youtube_video_youtube_url',
    'sponsorship_subsidiary_youtube_video_influencer_name',
    'influencer_primary_name', 'influencer_primary_normalized_profile_name',
    'influencer_primary_first_names', 'influencer_primary_casual_first_names',
    'influencer_primary_name_drop_phrase', 'influencer_subsidiary_name',
    'buyer_type', 'grade', 'ladder_rank',
    'parent_record_company_company_name_for_emails',
]


def condense_lead(lead):
    """Keep only allowlisted custom_variables on each lead. No-op if KEY_CV is None."""
    if KEY_CV is None:
        return lead
    cv = lead.get('custom_variables', {}) or {}
    out = dict(lead)
    out['custom_variables'] = {k: cv.get(k, '') for k in KEY_CV}
    return out


async def upload_batch(session, batch_idx, leads, semaphore):
    async with semaphore:
        payload = {
            "workspace_id": WORKSPACE_ID,
            "campaign_id": CAMPAIGN_ID,
            "is_overwrite": True,
            "leads": leads,
        }
        headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
        start = time.time()
        try:
            async with session.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                data = await resp.json()
                elapsed = time.time() - start
                emails = [l.get('email', '?') for l in leads]
                print(
                    f"Batch {batch_idx} ({emails[0]} … {emails[-1]}): "
                    f"status={data.get('status')} "
                    f"uploaded={data.get('leads_uploaded')} "
                    f"overwritten={data.get('overwritten')} "
                    f"total_sent={data.get('total_sent')} "
                    f"({elapsed:.1f}s)"
                )
                return data
        except Exception as e:
            print(f"Batch {batch_idx} ERROR: {e}")
            return None


async def main():
    with open(LEADS_JSON_PATH) as f:
        all_leads = json.load(f)
    total = len(all_leads)
    print(f"Total leads in file: {total}")
    print(f"Uploading indices {START_INDEX}–{total-1} ({total - START_INDEX} leads)")
    print(f"Batch size: {BATCH_SIZE}")

    batches = []
    for i in range(START_INDEX, total, BATCH_SIZE):
        chunk = [condense_lead(l) for l in all_leads[i:i + BATCH_SIZE]]
        batches.append((i, chunk))
    print(f"Total batches: {len(batches)}\n")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [upload_batch(session, i, leads, semaphore) for i, leads in batches]
        results = await asyncio.gather(*tasks)

    total_uploaded = sum(r.get('leads_uploaded', 0) for r in results if r)
    total_overwritten = sum(r.get('overwritten', 0) for r in results if r)
    total_sent = sum(r.get('total_sent', 0) for r in results if r)
    errors = sum(1 for r in results if r is None)
    print()
    print("=" * 60)
    print(
        f"DONE: {total_sent} sent | {total_uploaded} new | "
        f"{total_overwritten} overwritten | {errors} errors"
    )
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
