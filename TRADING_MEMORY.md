# Claude Trading Memory

This file persists trading patterns, preferences, and lessons learned.
Claude reads this at session start and updates after successful trades.

---

## User Preferences

- **Always show preview table before trades** - never execute without confirmation
- **Wait for explicit confirmation** ("yes", "go", "confirm", "do it")
- **Table format**: ASCII box drawing with ┌─┬─┐ style
- **Price format**: cents (35¢ not 0.35)
- **Show market IDs** in tables for reference

---

## Successful Patterns

### Ladder Sell (Elon Tweet Markets) - 2026-01-21
**Context**: User had positions across multiple tweet count brackets
**Strategy**: Sell ladder with 1¢ increments to capture price movement

```
Market     | Shares | Orders | Size/Order | Range
-----------|--------|--------|------------|----------
360-379    | 786    | 7      | 100        | 12¢ → 18¢
380-399    | 2,314  | 19     | 120        | 29¢ → 47¢
400-419    | 2,307  | 19     | 120        | 25¢ → 43¢
420-439    | 515    | 5      | 100        | 14¢ → 18¢
```

**Result**: 50 orders placed, 1 matched immediately, 49 live
**Lesson**: User likes granular 1¢ ladders, ~100-120 shares per level

---

## Common Markets

### Elon Tweet Counts (Weekly)
- Pattern: `elon-musk-of-tweets-{date-range}`
- User holds multiple brackets simultaneously
- Prefers sell ladders above current price
- Market IDs change weekly - always fetch fresh

### Oil Tanker Events
- Pattern: `us-forces-seize-another-oil-tanker-by`
- Multiple date brackets (Jan 25, Jan 31, etc.)
- User trades both YES and NO sides

---

## API Notes

- **Position sync delay**: Polymarket data API can lag 1-5 min after trades
- **Token ID caching**: Essential - same market = same token, cache it
- **Rate limits**: ~100 orders/min safe, add 0.1s delay between orders
- **Order status**: "matched" = filled, "live" = on book, "delayed" = pending

---

## Workflow Checklist

1. [ ] Load event with `show_event(slug)`
2. [ ] Show market table with IDs, prices, spreads
3. [ ] Confirm user's position sizes (API may be stale)
4. [ ] Build preview table with all orders
5. [ ] Wait for explicit confirmation
6. [ ] Execute with small delays between orders
7. [ ] Show result summary table
8. [ ] Update this memory file if new pattern learned

---

## Session Log

### 2026-01-21
- Tested new cockpit.py trading interface
- Placed 50 sell ladder orders across 4 Elon tweet markets
- All orders successful (1 matched, 49 live)
- User confirmed preview→execute flow works well
