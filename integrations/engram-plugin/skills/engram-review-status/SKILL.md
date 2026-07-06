---
name: engram-review-status
description: Check review proposal status for Engram repo/org memory changes made by the current actor.
---

# Engram Review Status

Use this skill when the user asks whether a memory proposal was approved, rejected, or is still pending.

Do not pass a user ID or org ID. Engram returns proposals for the authenticated actor and organization.

## Steps

1. If the user supplied a proposal ID, call `get_memory_review_status(proposal_id=<id>)`.
2. If the user supplied a memory ID, call `get_memory_review_status(memory_id=<id>)`.
3. Otherwise call `get_memory_review_status(limit=10)`.
4. Summarize each result compactly:
   - proposal ID
   - memory ID, if present
   - proposal type
   - status
   - scope type
   - created/updated time
5. If `contains_possible_secret=true`, warn that the proposal may require extra care.