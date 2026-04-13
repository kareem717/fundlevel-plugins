# PlusVibe Lead Schema

PlusVibe's `/lead/add` endpoint accepts an array of lead objects. Each lead has a fixed
set of **root fields** (recognized natively by PlusVibe) and an arbitrary
**`custom_variables`** dict for everything else. Anything that needs to be addressable in
an email template (like `{{first_name}}` or `{{sponsorship_primary_youtube_video}}`) must
end up in one of these two places.

## Root fields (native)

Put these at the top level of the lead object, NOT inside `custom_variables`:

| Field | Notes |
|---|---|
| `email` | **Required.** Single email address. |
| `first_name` | |
| `last_name` | |
| `job_title` | |
| `company_name` | |
| `company_website` | Bare domain is fine (e.g. `acme.com`). |
| `linkedin_person_url` | Full URL. |
| `linkedin_company_url` | Full URL. |
| `phone_number` | |
| `city` | |
| `country` | |
| `country_code` | |
| `address_line` | |
| `notes` | |

## `custom_variables`

A dict of string → string. Everything not in the root-field list above goes here.

PlusVibe will accept anything you throw in this dict, but only fields referenced in the
sequence's email templates will actually be used. Sending fields that aren't referenced is
harmless but wastes payload size — filter down for large uploads (see `KEY_CV` in
`scripts/upload_leads.py`).

## Standard FundLevel CSV→JSON mapping

Account ladder CSVs produced upstream use snake_case Attio-style column names. Typical
transform:

```python
def csv_row_to_lead(row):
    return {
        # Root fields
        "email": row['parent_record_email_addresses'].split(',')[0].strip(),
        "first_name": row['parent_record_name_first'],
        "last_name": row['parent_record_name_last'],
        "job_title": row['parent_record_job_title'],
        "company_name": row['parent_record_company_name'],
        "company_website": row['parent_record_company_domains'],
        "linkedin_person_url": row['parent_record_linkedin'],
        "linkedin_company_url": row['parent_record_company_linkedin'],

        # Everything else as custom_variables
        "custom_variables": {
            "entry_id": row['entry_id'],
            "parent_record_record_id": row.get('parent_record_record_id', ''),
            "ladder_rank": row.get('ladder_rank', ''),
            "buyer_type": row.get('buyer_type', ''),
            "grade": row.get('grade', ''),
            "sponsorship_primary_type": row.get('sponsorship_primary_type', ''),
            "sponsorship_primary_youtube_video":
                row.get('sponsorship_primary_youtube_video', ''),
            "sponsorship_primary_youtube_video_youtube_url":
                row.get('sponsorship_primary_youtube_video_youtube_url', ''),
            "influencer_primary_normalized_profile_name":
                row.get('influencer_primary_normalized_profile_name', ''),
            "influencer_primary_first_names":
                row.get('influencer_primary_first_names', ''),
            "influencer_primary_name_drop_phrase":
                row.get('influencer_primary_name_drop_phrase', ''),
            # ... carry over whatever else the sequence templates reference
        },
    }
```

Save the list of transformed dicts as JSON (array at the top level):

```python
import json, csv
with open('top.csv') as f:
    leads = [csv_row_to_lead(row) for row in csv.DictReader(f)]
with open('leads.json', 'w') as f:
    json.dump(leads, f)
```

## Which custom variables are actually used?

This depends on the sequence. To check what a campaign's templates reference, run
`get_campaign_emails(campaign_id)` via MCP and grep the body text for `{{...}}` tokens.
The `KEY_CV` list in the upload script should be a superset of those tokens — anything
else is dead weight.

## Overwrite behavior

The upload payload includes `"is_overwrite": true`. This means:

- Leads with new emails → created fresh.
- Leads with emails already in the campaign → existing lead is **updated** with the new
  field values (any fields you send replace the existing ones; fields you omit are left
  untouched).

Set `is_overwrite` to `false` if you want existing leads to be skipped instead of updated.
The response distinguishes `leads_uploaded` (new) from `overwritten` (updated).
