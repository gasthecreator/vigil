---
status: accepted
date: 2026-10-16
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0009. Asynchronous Task Queue Selection for Follow-Up Guardian Notifications and Longitudinal ML Ingestion

## Context and Problem Statement
The Vigil precision oncology decision-support platform (Master Plan §6.6, §9.3) requires asynchronous background task processing for:
1. **Follow-Up Guardian (M6) Escalation Evaluation:** Periodic evaluation of active follow-up tasks against the escalation ladder.
2. **Outbound Notification Delivery:** Multi-channel patient reminders (SMS, WhatsApp Business API templates, coordinator worklist dispatch) with retry backoffs and delivery receipt tracking.
3. **Longitudinal Simulation & Batch Ingestion:** Asynchronous execution of intensive inference suites (e.g. M10 Missed-Signal Audits, synthetic cohort benchmarking).

The operational deployment environment ranges from single-node local hospital servers running Docker Compose without dedicated DevOps staff, to distributed cloud deployments for centralized research.

## Decision Drivers
1. **Operational Simplicity:** Minimal operational footprint. Avoiding the requirement of running and monitoring separate heavy brokers (e.g. RabbitMQ, Kafka) on edge hospital appliances.
2. **Reliability & Idempotency:** Guaranteed at-least-once task delivery without task loss during worker crashes.
3. **Transactional Integrity:** Ability to schedule tasks within the same database transaction that created the `Observation` or `Alert` (Transactional Outbox pattern).
4. **Visibility & Inspection:** Full auditability and monitoring of queued, running, failed, and retried jobs.

## Considered Options
- **Option 1: Celery + RabbitMQ / Redis**  
  *Pros:* Industry standard in Python ecosystem; rich ecosystem of extensions.  
  *Cons:* High operational overhead; requires external broker container; complex connection pooling; notorious edge failure modes during Redis memory exhaustion.
- **Option 2: Cloud-Native Managed Queues (AWS SQS, Google Cloud Tasks)**  
  *Pros:* Zero infrastructure maintenance.  
  *Cons:* Cloud vendor lock-in; breaks on-premise hospital deployment requirements and offline/edge runtime scenarios.
- **Option 3: Postgres-Native Job Queue (ARQ / Procrastinate / SQLAlchemy Transactional Outbox) with In-Process Worker Fallback (Selected)**  
  *Pros:*
  - Leverages the existing relational database (`PostgreSQL` in production, `SQLite` in local/testing) as the queue backend using `FOR UPDATE SKIP LOCKED`.
  - Enables the **Transactional Outbox Pattern**: inserting a `FollowUpTask` or notification dispatch within the exact same atomic transaction as the `Observation` and `Alert`.
  - Zero external broker dependencies required on hospital hardware.
  - Native integration with Python `asyncio` via `ARQ` (Redis-backed for high-throughput cloud tiers) or database-backed queue for edge appliances.

## Decision Outcome
Chosen option: **Option 3: Postgres-Native Transactional Outbox with ARQ / BackgroundWorker Adapter**.
1. **Transactional Outbox:** All asynchronous notifications and guardian escalations are written to database task records (`FollowUpTask` / `OutboxMessage`) atomically.
2. **Deterministic Evaluation:** State machine and escalation logic in `apps/api/vigil_api/guardian.py` are decoupled from external queue brokers via an injectable clock (`current_time`), enabling full deterministic testing without background daemon dependencies.
3. **Worker Runtime:** Standard background worker runs periodic ticks (e.g. hourly or cron-triggered) invoking `evaluate_tasks(db)` and pulling unsent notifications with exponential backoff.
