# Runbook: <alert or symptom name>

Owner: <team> · Last verified: YYYY-MM-DD · Linked alert: <url> · Dashboard: <url>

## Impact
<What users experience; severity guide.>

## Diagnose
1. Check <dashboard/metric>; expected value <...>
2. `<command to inspect logs/state>`
3. Common causes: <cause → how to confirm>

## Mitigate (fastest safe action first)
1. <rollback / disable flag / scale / failover>: `<command>`
2. Verify recovery: <metric returns to ...>

## Escalate
<When and to whom; on-call rotation link.>

## Follow-up
<Create postmortem if: ... ; file issue for permanent fix.>
