# ENGINEERING_LOG.md — EstimAI
Lightweight, timestamped log of decisions, bugs, fixes, and todos. Keep each entry one or two lines. Update as you commit.

> Tip: Add a shell helper to append quickly (optional):
> ```bash
> log() { echo "- $(date +'%Y-%m-%d %H:%M') — $*" >> docs/ENGINEERING_LOG.md; tail -3 docs/ENGINEERING_LOG.md; }
> ```

## Entries
- 2025-08-27 — Initialized NEXT_STEPS and ENGINEERING_LOG templates.
- 2025-08-27 — Planned tickets: Estimate Agent MVP; Tighten Leveler & Risk; Bid PDF; Async Jobs.
- 2025-08-27 16:20 — Completed Estimate Agent MVP; tests passing; artifacts persist.
- 2025-09-01 14:00 — PR 6: Added smoke + lifecycle tests for /bid, /artifacts, /jobs endpoints; async polling with retries; 6/6 tests passing.

