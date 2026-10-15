# Postmortem: <incident title>

Date: YYYY-MM-DD · Severity: SEV<n> · Authors: <names> · Status: draft | reviewed | complete
*Blameless: focus on systems and process, assume good faith, never name individuals as the cause.*

## Summary
<What happened, in 2-3 sentences.>

## Impact
- Users/requests affected, duration, data loss (Y/N), revenue/SLO budget consumed

## Timeline (UTC)
| Time | Event |
|---|---|
| hh:mm | detected by <alert/person> |
| hh:mm | mitigation started |
| hh:mm | resolved |

## Detection
<How we found out; why it was or was not caught by monitoring.>

## Root causes and contributing factors
<Dig deep: ask why the system let people act on missing or wrong information.>

## What went well / what went poorly / where we got lucky

## Action items
| Action | Type (prevent/detect/mitigate) | Owner | Priority | Issue | Due |
|---|---|---|---|---|---|

## Lessons learned
<Add or update runbooks, alerts, tests, ADRs.>

<!-- Trigger a postmortem for: user-visible downtime above threshold, any data loss, on-call intervention (rollback/reroute), long time to resolve, or manual detection. Remove end-user identifiers. -->
