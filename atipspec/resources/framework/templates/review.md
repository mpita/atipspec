---
tree: <fingerprint from the packet>
reviewer: <client or model that wrote this review>
session: <isolated, only when this session never saw the author's conversation; shared otherwise>
---

# Review: <title>

## Criteria

- AC-001: PASS. <a test that passed in the evidence report, path:line, or path::test>
- AC-002: PASS. <for a manual criterion: what was done and what was observed>
- AC-003: FAIL. <what is missing or wrong, precisely>

## Findings

- F1 [blocker]: <regression, spec conflict or unmet requirement not tied to one criterion>
- F2 [major]: <should be fixed before archive; only a risk exception under a trust policy defers it>
- F3 [minor]: <worth noting; does not block>

## Notes

<what the author needs to know to act on this review>
