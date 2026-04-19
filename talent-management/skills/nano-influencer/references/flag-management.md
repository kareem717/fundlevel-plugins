# Flag Management — Projects, Favorites, and Hides

NanoInfluencer lets you tag channels with `fav` or `hide` flags, scoped per project. The purpose isn't just bookkeeping — flags shape future searches:

- **`fav`** channels bias similar searches toward "more like this"
- **`hide`** channels are filtered out of future results in that project

Every new search under the same `groupId` inherits those signals. After two or three rounds of curation, nano's recommendations for that project tend to converge on the user's taste.

## The tools

| Tool | Purpose |
|---|---|
| `nanoinfluencer-list-projects` | List all projects. Each has `{ id, title }`. The `id` is the `groupId` you pass elsewhere. |
| `nanoinfluencer-create-project` | Create a new project folder. Returns the project with its id. |
| `nanoinfluencer-get-flags` | Read current flag state for a batch of channels in a project. |
| `nanoinfluencer-set-flags` | Set `fav`, `hide`, or `del` (clear) on channels. |

## When to create a new project

Default project (id `0`) is the catch-all. Spin up a dedicated project via `nanoinfluencer-create-project` when the user wants curated lookalike flows for a specific:

- **Brand client** — e.g. "PostHog sourcing" so fav'd dev-tool creators train future searches for PostHog
- **Niche bet** — e.g. "AI dev creators", "fitness micros"
- **Active campaign** — e.g. "Q2 DevTools campaign"

Rule of thumb: if the user is going to run more than one or two similar-searches in a given niche, it's worth a project. Scratch searches can stay under default.

## Cap: 100 per project

NanoInfluencer enforces a per-project cap of roughly **100 favorited + hidden channels combined**. Once you approach the cap, future flag writes may start failing silently or evicting old flags.

If the user has been curating aggressively and you're near the cap:
- Offer to spin up a new project for the next wave
- Prune obvious losers with `flag: "del"` before adding new hides

## Standard workflow after a triage round

Once the user has reviewed a search result:

```
# Favorite the winners (top 5–10) so they train future searches
nanoinfluencer-set-flags({
  channels: [
    { platform: "ytb", id: "UC...", name: "hdeleon.net" },
    { platform: "ytb", id: "UC...", name: "Oriol Tarrago" }
  ],
  flag: "fav",
  groupId: "42"
})

# Hide the obvious misses so they stop reappearing
nanoinfluencer-set-flags({
  channels: [
    { platform: "ytb", id: "UC...", name: "Off-topic Channel" }
  ],
  flag: "hide",
  groupId: "42"
})

# If a flag was wrong, clear it
nanoinfluencer-set-flags({
  channels: [{ platform: "ytb", id: "UC...", name: "..." }],
  flag: "del",
  groupId: "42"
})
```

**Don't flag every channel.** Flag clear winners and clear misses. The ambiguous middle should stay unflagged — it's neither training signal nor noise. Over-flagging erodes the signal quality because "fav" stops meaning "this is exactly the vibe".

## Batch size

`nanoinfluencer-set-flags` accepts an array of channels in one call. Batch up to ~25 per call for clean behavior. For larger lists, split into multiple calls.

## `email` field on set-flags

When favoriting, include the creator's email if you have it (lifted from the poll response):

```
{ platform: "ytb", id: "UC...", name: "...", email: "contact@example.com" }
```

NanoInfluencer stores this alongside the flag, so the curated project doubles as a contact sheet. Omit if the creator's email field is empty — don't fabricate.

## Reading flag state

Before a new search in an active project, run `nanoinfluencer-get-flags` to see what's already favorited. Useful when the user asks "what's already in my AI creators list?" — you can answer without burning a lookalike search.

```
nanoinfluencer-get-flags({
  platform: "ytb",
  ids: ["UC...", "UC...", "UC..."],
  groupId: "42"
})
# → { channels: [{ id, flag, label, note, ... }, ...] }
```

The returned `channels` array has current flag state per channel. Channels with no flag in that project may return with an empty flag field or be absent — don't depend on exhaustive presence.

## Common mistakes

- **Flagging in the wrong project.** Always confirm `groupId` matches the project the user is actively working in. Flagging in the default project (`0`) when the user meant their curated project is a common drift.
- **Favoriting borderline channels.** Only `fav` clear yeses. Borderline signals dilute training.
- **Forgetting to hide obvious misses.** Under-hiding is more common than over-hiding. If a channel is clearly off-brief, hide it — it saves the user from reviewing it again on the next search.
- **Batch flagging from raw search output without review.** The point of flags is taste signal. Auto-flagging defeats the point. Walk the user through a quick yes/no pass before writing flags.
