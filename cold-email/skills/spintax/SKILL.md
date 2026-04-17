---
name: spintax
description: |
  Write PlusVibe-compatible spintax for cold-email copy — randomised variations like
  `{{random|Hi|Hey|Hello}}` and fallback defaults like `{{fallback|{{first_name}}|there}}`.
  Use this skill whenever drafting or editing email subject lines or body copy that will
  be sent through PlusVibe (or the pipl.ai engine it's built on) and the user wants
  deliverability-friendly variation, or whenever you see existing spintax in a campaign
  and need to extend or fix it. Typical triggers: "add spintax to this email", "spin the
  first line", "vary the opener", "add a fallback for first_name", "why isn't my spintax
  working", "write a cold email with variations", or any PlusVibe email template where
  multiple variants of a phrase are desired. Pair with the `liquid-syntax` skill when the
  email also needs conditional logic (if/else, day-of-week, industry-based) — spintax is
  for random variation, liquid is for rules.
---

# PlusVibe Spintax

Spintax produces randomised variations of a phrase so that each outgoing email is subtly
unique. This improves deliverability (spam filters flag identical bulk sends) and lets
FundLevel campaigns feel less templated without writing N separate emails.

Source: https://help.plusvibe.ai/en/articles/8606174-spintax-guide

## When to use spintax vs. liquid

- **Spintax** — pick one of N options at random. No input needed. Use for openers,
  transitions, sign-offs, anything where any of the variants is acceptable.
- **Liquid** (see `liquid-syntax` skill) — choose based on a rule (lead's industry, day
  of week, whether a field is blank). Use when the choice is deterministic.

A single line can combine both: liquid decides the branch, spintax varies the wording
inside that branch.

## Random spintax

Syntax: `{{random|option1|option2|option3}}`

```
{{random|Hi|Hey|Hello}} {{first_name}},
```

Will render as `Hi Kareem,` or `Hey Kareem,` or `Hello Kareem,` per send.

**Case-insensitive keyword.** `{{random|...}}`, `{{RANDOM|...}}`, `{{rAnDoM|...}}` all
work identically. Stick to lowercase `random` for consistency in FundLevel templates.

**Spaces are preserved.** `{{random| hello | hi }}` will emit a leading and trailing
space on every variant. Don't pad options unless you mean it.

**Empty options are allowed.** `{{random|Just checking in.||}}` renders either the
phrase or nothing — a way to sometimes include a sentence and sometimes skip it.

## Fallback spintax

Syntax: `{{fallback|{{variable}}|default}}`

Use when a dynamic variable might be blank and you want a graceful default.

```
Hi {{fallback|{{first_name}}|there}},
```

Renders `Hi Kareem,` when `first_name` is populated, `Hi there,` when it isn't.

**Case-insensitive keyword.** `{{FALLBACK|...}}`, `{{fallback|...}}`, etc. all work.

**Spaces are preserved** in the fallback text, same as random.

## Hard rules (don't violate these)

1. **One variable per option, not per block.** This is the single most common break.
   The rule is about how many variables appear in a *single option*, not the total
   references across all options:

   ```
   BAD:  {{random|Hello {{first_name}} {{last_name}}|Hi there}}
         ↑ first option has TWO different variables — errors

   GOOD: {{random|Hello {{first_name}}|Hey {{first_name}}|Hi there}}
         ↑ each option has at most one variable; same variable repeated across
           options is fine
   ```

   The same variable reused across multiple options (e.g. `{{inf_name}}` in every
   branch) is totally fine — it's only when a single option tries to interpolate two
   or more different variables that PlusVibe errors at send time.

2. **Nesting is fine.** `{{fallback|{{first_name}}|friend}}` is one variable inside
   fallback — allowed. Liquid-assigned variables (`{% assign inf_name = ... %}`)
   behave the same as lead variables inside spintax.

3. **Whitespace is not trimmed.** `{{random| hello |hi}}` produces `" hello "` half the
   time. If variants have different punctuation spacing, double-check the rendered
   preview.

4. **Empty `||` is intentional, use it deliberately.** `{{random|Quick note.||}}` will
   sometimes output nothing. Fine for optional sentences, dangerous mid-sentence.

## Patterns FundLevel actually uses

**Opener variation** (top of every cold email):

```
{{random|Hey|Hi|Hello}} {{fallback|{{first_name}}|there}},
```

**Soft check-in transition** (bump emails):

```
{{random|Just circling back|Following up|Bumping this}} on my note from last week.
```

**Sign-off variation:**

```
{{random|Thanks|Cheers|Appreciate it}},
{{sender_first_name}}
```

**Signature name variation** (pair with `| slice` in liquid to get initials —
see `liquid-syntax` skill for the `fi` / `li` assigns):

```
{{random|{{sender_first_name}}|{{sender_first_name}} {{sender_last_name}}|{{fi}}. {{sender_last_name}}|{{sender_first_name}} {{li}}.}}
```

Note each option here is a separate composition of the same-ish name — the rule is
"one variable per option", but an option can still include multiple variables if
that's what it needs (`{{sender_first_name}} {{sender_last_name}}`). In practice
PlusVibe is lenient with sender-side variables; the hard failure case is multiple
*lead*-side variables in one option. When in doubt, simplify.

**Title / company variation** (sign-off line):

```
{{random|Managing Director|Founder|CEO|Owner}}{{random| at|,}} Fundlevel{{random|| Media}}
```

The trailing `{{random|| Media}}` is the empty-string trick — sometimes the company
shows as "Fundlevel", sometimes "Fundlevel Media".

**Conditional filler** (sometimes include, sometimes don't):

```
{{random|Happy to share some examples if useful.||}}
```

**Punctuation/emoji micro-variation** at sentence ends:

```
...would love your take{{random|. ;)|. :)| :)| ;)}}
```

Small touches like a winking emoji half the time make bulk sends feel less
templated without changing the message.

## Workflow when drafting

1. Write the email in plain prose first. Don't spintax as you go — it muddies the read.
2. Identify 2-4 spots where variation is valuable: opener, a transition, sign-off, maybe
   one mid-body phrase. Don't spintax every sentence — it becomes noise and can hurt
   readability when the variants don't flow equally well.
3. Add `{{random|...}}` blocks. Verify each has **≤1 variable**.
4. Wrap every dynamic variable that could be blank (`first_name`, `company_name`) in
   `{{fallback|...|default}}`. Leads imported from messy CSVs often have gaps.
5. Tell the user to hit **Preview Email** and **Test Email** in PlusVibe before launching.
   The preview re-rolls the spintax on each click, which is the best way to sanity-check
   that every variant reads naturally.

## Common bugs to watch for

- **Two variables in one spintax:** e.g. `{{random|Hi {{first_name}} {{last_name}}|Hello}}`.
  Split into `Hi {{first_name}} {{last_name}}` outside spintax, then `{{random|, hope you're well.|.|!}}` inside.
- **Forgotten fallback on `first_name`:** blank-name leads send `Hi ,` which looks broken.
  Always `{{fallback|{{first_name}}|there}}` (or another neutral default).
- **Trailing space before punctuation:** `{{random|Hi |Hey |Hello }} {{first_name}},`
  → double space. Pull the trailing space out: `{{random|Hi|Hey|Hello}} {{first_name}},`.
- **Variants with inconsistent tone:** one variant is formal, another casual. The
  recipient gets whichever — make sure *any* of them would be acceptable in the reader's
  eyes.

## Verification

There's no programmatic validator — you're checking by eye. Before reporting a draft as
done:

1. Grep for `{{random|` and `{{fallback|` in the draft and mentally render each. Confirm
   each block has at most one `{{...}}` variable inside.
2. Read the email aloud with the first option of every random block, then again with
   the last option. Both should flow naturally.
3. Remind the user to Preview/Test in PlusVibe — spintax bugs only surface at send time
   and cost a deliverability hit if missed.
