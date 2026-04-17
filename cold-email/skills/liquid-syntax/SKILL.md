---
name: liquid-syntax
description: |
  Write PlusVibe-compatible Liquid templating for cold-email copy — conditional logic
  (`{% if ... %}`), date/time-based branches, industry or job-title personalization,
  logical operators, and nested conditionals. Use this skill whenever drafting or editing
  PlusVibe email copy that needs to branch on a lead's data (industry, company_size,
  job_title, whether a field is blank) or on the current date/time (day-of-week opener,
  morning/afternoon greeting). Typical triggers: "add an if statement for industry",
  "different opener for Monday vs. Friday", "greet by time of day", "show this only if
  company_name is set", "personalize by job title", "add conditional logic to this
  email", or any request involving `{% if %}`, `{% elsif %}`, `{% assign %}`, Liquid
  filters, or date math in a PlusVibe template. Pair with the `spintax` skill when the
  email also needs random variation — liquid picks the branch, spintax varies the words
  inside the branch.
---

# PlusVibe Liquid Syntax

Liquid is a standard templating language (originally Shopify's) that PlusVibe uses for
conditional logic in email copy. Unlike spintax, which picks randomly, Liquid chooses
based on rules: lead data fields, the current day/hour, logical combinations.

Sources:
- PlusVibe's guide: https://help.plusvibe.ai/en/articles/10748974-liquid-syntax-guide-for-plusvibe
- Shopify's canonical Liquid reference: https://shopify.dev/docs/api/liquid

## Looking up tags and filters beyond this guide

PlusVibe implements standard Liquid, so any tag or filter in the Shopify reference works
here (modulo Shopify-specific objects like `product` or `cart`, which don't exist in
the PlusVibe context). If the user asks for something not covered below — an unusual
filter (`| truncate`, `| capitalize`, `| default`), a loop (`{% for %}`), string
manipulation — use the **Context7 MCP** to pull the official docs:

```
mcp__context7__query-docs(
  libraryId: "/websites/shopify_dev_api_liquid",
  query: "<specific filter or tag you need, e.g. 'truncate filter syntax'>"
)
```

Context7 returns current, code-example-backed snippets from shopify.dev. Prefer this
over guessing when the user's request goes outside the patterns in this skill.

## Liquid vs. spintax — pick the right tool

- **Liquid** — deterministic. Same inputs → same output. Use when the choice depends on
  the lead or the send time.
- **Spintax** (see `spintax` skill) — random. Use when any of several phrasings is
  fine and you want each send to differ for deliverability.

The two compose cleanly: Liquid selects the branch, spintax varies the wording:

```
{% if industry == "technology" %}
{{random|Noticed|Saw}} you're in tech — {{random|thought|figured}} our dev tooling might land well.
{% else %}
{{random|Hope|Trust}} this lands at a useful moment.
{% endif %}
```

## The one rule people forget: brace the variable OUTSIDE, not INSIDE

This is the single most common bug:

- **In regular email text**, reference a variable with double braces: `{{first_name}}`.
- **Inside a Liquid tag** (`{% ... %}`), reference it bare: `first_name`.

```
{% if first_name != blank %}
Nice to meet you, {{first_name}}!        ← braces, we're in text
{% elsif company_name != blank %}
Hello there, someone from {{company_name}}!  ← braces, we're in text
{% else %}
Welcome!
{% endif %}
```

The `first_name != blank` test uses the bare name because we're inside `{% %}`. The
`{{first_name}}` output uses braces because we're in output text.

If you write `{% if {{first_name}} != blank %}`, PlusVibe errors. If you write
`Hi first_name,` in body text, the literal string `first_name` goes out. Both happen.
Check every template before handing it back.

## Basic if/elsif/else

```
{% if first_name != blank %}
Nice to meet you, {{first_name}}!
{% elsif company_name != blank %}
Hello there, someone from {{company_name}}!
{% else %}
Welcome!
{% endif %}
```

Comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=`, `contains`.
Special value: `blank` (empty or missing field).

## Date- and time-based branches

**Day of week** — `'%u'` returns 1 (Monday) through 7 (Sunday). `| plus: 0` coerces the
string to a number so `<` comparisons work.

```
{% assign today_number = 'now' | date: '%u' | plus: 0 %}
{% if today_number < 4 %}
Hope you're having a good start to the week.
{% else %}
Hope you're having a good week.
{% endif %}
```

Same pattern for meeting scheduling:

```
{% assign today_number = 'now' | date: '%u' | plus: 0 %}
{% if today_number < 4 %}
Are you available anytime this week?
{% else %}
Are you available anytime next week?
{% endif %}
```

**Hour of day** — `'%H'` returns 00-23.

```
{% assign hour = 'now' | date: '%H' | plus: 0 %}
{% if hour < 12 %}
Good morning, {{first_name}}!
{% elsif hour < 17 %}
Good afternoon, {{first_name}}!
{% else %}
Good evening, {{first_name}}!
{% endif %}
```

Note the time zone caveat: `'now'` resolves to PlusVibe's server time, not the
recipient's. For most FundLevel campaigns that's close enough, but don't promise a
true-local-time greeting.

## Industry / field-based personalization

```
{% if industry == "technology" %}
I noticed you work in tech and thought our developer tools might interest you.
{% elsif industry == "healthcare" %}
Our HIPAA-compliant solutions have helped many healthcare providers like {{company_name}}.
{% elsif industry == "finance" %}
Many financial institutions have improved their ROI by {{percentage}}% using our platform.
{% else %}
Our platform can be tailored to meet the specific needs of your industry.
{% endif %}
```

String comparisons are case-sensitive: `"technology"` does not match `"Technology"`.
If the lead data is inconsistently cased (common with imported CSVs), either normalize
before import or use `contains` with care.

## Logical operators: `and`, `or`

```
{% if job_title contains "Manager" or job_title contains "Director" %}
As a leader in your organization, you might be interested in our management solutions.
{% elsif job_title contains "Developer" and industry == "technology" %}
Our developer tools have helped tech professionals like you improve productivity by 40%.
{% endif %}
```

Liquid has no parentheses for grouping — evaluation is right-to-left with `and`
binding tighter than `or`. If precedence matters, rewrite with nested `{% if %}` blocks.

## Nested conditionals

```
{% if company_size > 100 %}
  {% if industry == "retail" %}
  Our enterprise retail solution has helped companies like yours increase sales by 25%.
  {% elsif industry == "manufacturing" %}
  Our manufacturing platform has helped large companies reduce costs by 15%.
  {% else %}
  Our enterprise solutions are designed for organizations of your size.
  {% endif %}
{% else %}
Our small business package might be perfect for {{company_name}}.
{% endif %}
```

`company_size > 100` only works if the field is numeric. Custom variables uploaded as
strings will compare lexicographically — `"99"` is NOT less than `"100"` as strings.
If in doubt, `| plus: 0` to coerce: `{% if company_size | plus: 0 > 100 %}`.

## Assigning intermediate values

```
{% assign today_number = 'now' | date: '%u' | plus: 0 %}
```

Use `{% assign %}` for values you'll reference multiple times or that need a filter
chain. Assigned variables are scoped to the template and can't be overwritten from
outside.

## Whitespace control: `{%- ... -%}` (critical)

A plain `{% assign %}` tag leaves a blank line in the rendered output. Chain five
assigns at the top of an email and the recipient opens a message with five empty
lines before "Hey first_name". Always use the hyphen-trimmed form when the tag
shouldn't produce visible whitespace:

- `{%- assign x = y -%}` — trims whitespace on both sides.
- `{%- if ... -%}` / `{%- elsif ... -%}` / `{%- else -%}` / `{%- endif -%}` — same.

FundLevel production templates open with a dense block of `{%- assign -%}` tags on
one line, all hyphen-trimmed, so the email body starts cleanly:

```
{%- assign fi = sender_first_name | slice: 0, 1 | upcase -%}{%- assign li = sender_last_name | slice: 0, 1 | upcase -%}{%- if custom_sponsorship_primary_type == "Dedicated" -%}{%- assign sponsor_type = "a dedicated video" -%}{%- elsif ... -%}...{%- endif -%}{{random|Hey|Hi}} {{first_name}}{{random|!|,}}
```

Use the non-trimmed form `{% %}` only when you specifically want the surrounding
newline (rare in email context — usually you're assigning silently).

## Filters used in FundLevel campaigns

Liquid has a large filter library (see Context7 lookup above). The ones that actually
show up in production templates:

- **`| slice: start, length`** — substring. `sender_first_name | slice: 0, 1` gives
  the first character. Combined with `| upcase` for initials: `fi = "K"`, used in
  signature variants like `"K. Yakubu"`.
- **`| upcase` / `| downcase`** — case normalization. Subject lines often lowercase
  the creator name: `custom_influencer_primary_first_names | downcase`.
- **`| plus: N` / `| minus: N` / `| times: N`** — arithmetic, also coerces strings
  to numbers. Always chain `| plus: 0` onto a `| date:` output before comparing.
- **`| append: "str"`** — string concatenation.
  `"back in " | append: pub_year` → `"back in 2024"`.
- **`| date: "<format>"`** — strftime format codes. The ones used in FundLevel
  campaigns:
  - `%Y` — 4-digit year (`2026`)
  - `%-m` — month, no zero-padding (`4`, not `04`)
  - `%B` — full month name (`April`)
  - `%W` — week of year, Monday-start (`00`-`53`)
  - `%-j` — day of year, no zero-padding (`107`)
  - `%u` — day of week, 1 (Mon) to 7 (Sun)
  - `%H` — hour, 24-hour
- **`| default: "fallback"`** — emits the fallback if the value is `nil`, `false`,
  or empty string. Simpler than an `{% if %}` when there are no filters to apply.

## The relative-time pattern

A frequently-useful FundLevel snippet: turn a dated event (a YouTube video's publish
date) into a natural-language phrase like "last week" or "back in 2024". The pattern
computes year/month/week/day diffs against `"now"` and cascades through `{% elsif %}`
from coarsest to finest:

```
{%- assign now_year  = "now" | date: "%Y"  | plus: 0 -%}
{%- assign now_month = "now" | date: "%-m" | plus: 0 -%}
{%- assign now_week  = "now" | date: "%W"  | plus: 0 -%}
{%- assign now_day   = "now" | date: "%-j" | plus: 0 -%}
{%- assign pub_year  = custom_sponsorship_primary_youtube_video_published_at | date: "%Y"  | plus: 0 -%}
{%- assign pub_month = custom_sponsorship_primary_youtube_video_published_at | date: "%-m" | plus: 0 -%}
{%- assign pub_week  = custom_sponsorship_primary_youtube_video_published_at | date: "%W"  | plus: 0 -%}
{%- assign pub_day   = custom_sponsorship_primary_youtube_video_published_at | date: "%-j" | plus: 0 -%}
{%- assign year_diff  = now_year | minus: pub_year -%}
{%- assign month_diff = now_month | minus: pub_month | plus: year_diff | times: 12 -%}
{%- assign week_diff  = now_week | minus: pub_week -%}
{%- assign day_diff   = now_day | minus: pub_day -%}
{%- if year_diff >= 2 -%}{%- assign time_phrase = "back in " | append: pub_year -%}
{%- elsif year_diff == 1 and now_month <= 2 -%}{%- assign time_phrase = "late last year" -%}
{%- elsif year_diff == 1 -%}{%- assign time_phrase = "last year" -%}
{%- elsif month_diff >= 6 -%}{%- assign time_phrase = "earlier this year" -%}
{%- elsif month_diff >= 3 -%}{%- assign time_phrase = "a few months back" -%}
{%- elsif month_diff == 2 -%}{%- assign time_phrase = "a couple months ago" -%}
{%- elsif month_diff == 1 -%}{%- assign time_phrase = "last month" -%}
{%- elsif week_diff >= 2 -%}{%- assign time_phrase = "a few weeks ago" -%}
{%- elsif week_diff == 1 or day_diff >= 7 -%}{%- assign time_phrase = "last week" -%}
{%- elsif day_diff >= 2 -%}{%- assign time_phrase = "earlier this week" -%}
{%- else -%}{%- assign time_phrase = "recently" -%}{%- endif -%}
```

Then drop `{{time_phrase}}` into the body: `"Saw the partnership with {{creator}}
{{time_phrase}}..."`.

Caveats: the week/day-of-year diffs go negative across year boundaries
(`week_diff = now_week - pub_week` is wrong in January for a December publish). The
`year_diff >= 2` and `year_diff == 1` branches catch those cases first, which is why
the ordering matters — don't reshuffle the cascade.

## Fallback-with-filters pattern (preferred over `{{fallback|...}}` when you need filtering)

The spintax `{{fallback|{{field}}|default}}` is clean but can't apply filters. When the
dynamic value needs normalization (downcase for a subject line, slice for an initial),
use an `{% if %}` + `{% assign %}` instead:

```
{%- if custom_influencer_primary_first_names != blank -%}
  {%- assign inf_name = custom_influencer_primary_first_names | downcase -%}
{%- else -%}
  {%- assign inf_name = "your creator" -%}
{%- endif -%}
```

Now `{{inf_name}}` is either the lowercased real name or the string default, and you
can use it safely in both liquid and spintax blocks below.

## Combining liquid assigns with spintax

Once you've built a liquid variable (`{% assign inf_name = ... %}`), it's treated the
same as any lead variable inside `{{random|...}}`. Subject line example:

```
{%- if custom_influencer_primary_first_names != blank -%}{%- assign inf_name = custom_influencer_primary_first_names | downcase -%}{%- else -%}{%- assign inf_name = "your creator" -%}{%- endif -%}{{random|{{inf_name}}?|{{inf_name}} roi?|{{inf_name}} results?|{{inf_name}} worth it?|how'd {{inf_name}} go?|happy with {{inf_name}}?}}
```

The same `{{inf_name}}` appears in every option — PlusVibe's "one variable per spintax
section" rule means one *unique* variable per option, not one reference total. See the
spintax skill for that nuance.

## Hard rules

1. **Inside `{% %}`, no braces on variables.** `{% if first_name != blank %}`, not
   `{% if {{first_name}} != blank %}`.
2. **Inside body text, always braces.** `{{first_name}}`, never `first_name`.
3. **Always close tags.** `{% if %}` needs `{% endif %}`; `{% for %}` needs `{% endfor %}`.
4. **Quote string literals.** `industry == "technology"`, not `industry == technology`
   (the latter compares to a variable named `technology`, which is usually blank).
5. **Coerce numeric comparisons when in doubt.** `| plus: 0` on both sides if either
   might be a string.
6. **Case-sensitive string comparisons.** If the data is inconsistent, use `contains`
   or normalize upstream.

## Patterns FundLevel actually uses

**Safe first-name opener** (prefer this over plain `{{first_name}}` when the CSV is
messy):

```
{% if first_name != blank %}
Hi {{first_name}},
{% else %}
Hi there,
{% endif %}
```

*(The spintax fallback `{{fallback|{{first_name}}|there}}` does the same thing in one
line — reach for it when there's no other conditional logic in play.)*

**Day-of-week opener** with weekend handling:

```
{% assign today_number = 'now' | date: '%u' | plus: 0 %}
{% if today_number < 4 %}
Hope the week's off to a solid start.
{% elsif today_number < 6 %}
Hope you're wrapping the week well.
{% else %}
Hope you're having a good weekend — no rush on this.
{% endif %}
```

**Title-based value prop** (buyer vs. practitioner framing):

```
{% if job_title contains "VP" or job_title contains "Director" or job_title contains "Head" %}
Figured this would be relevant given you own the {{department}} budget.
{% else %}
Thought you'd want to flag this to whoever owns {{department}} spend.
{% endif %}
```

## Workflow when drafting

1. Write the email as plain prose with variables, no branching.
2. Identify where a branch materially helps — usually the opener, one value-prop line,
   or a CTA. Liquid is noise if every line branches.
3. List the branch conditions explicitly (on paper/in the turn) before writing Liquid.
   Most bugs come from a missing `{% else %}` or a typo'd field name.
4. Verify every referenced field exists on the leads you're sending to. If 30% of leads
   are missing `industry`, your `{% else %}` branch better read well — that's the
   majority case.
5. Tell the user to hit **Preview Email** and **Test Email** in PlusVibe. The preview
   lets them pick a specific lead and see each branch render — the only reliable way to
   catch a broken field name or comparison.

## Common bugs to watch for

- **`{{first_name}}` inside `{% if %}`** — `{% if {{first_name}} != blank %}` errors.
  Drop the braces inside the tag.
- **Bare variable in body text** — `Hi first_name,` sends literally. Add the braces.
- **Unquoted string** — `{% if industry == technology %}` treats `technology` as an
  (empty) variable, so the branch never fires. Quote it: `"technology"`.
- **String/number comparison** — `company_size > 100` against a string field is
  lexicographic. `"99" > "100"` is true. Coerce with `| plus: 0`.
- **Missing `{% endif %}`** — PlusVibe will either error or silently include everything
  after the `{% if %}` verbatim. Always pair tags.
- **Case-mismatched string literal** — `"Technology"` ≠ `"technology"`. Normalize or
  switch to `contains`.
- **Unclosed `{% assign %}` reference** — assigned vars are only in scope for the
  current template, not across a multi-step sequence.

## Verification

There's no programmatic validator — you're checking by eye and by Preview.

1. Grep for `{% if`, `{% elsif`, `{% else`, `{% endif` and confirm they balance.
2. For each condition, confirm the referenced field exists in the campaign's lead
   schema. A typo like `industy == "tech"` never matches and the `{% else %}` branch
   always fires — subtle and ugly.
3. Inside `{% %}` tags: no `{{...}}`. Outside: every variable has `{{...}}`.
4. Tell the user to Preview with 2-3 real leads that exercise different branches before
   launching. Liquid bugs show up at send time and are invisible in static proofreading.
