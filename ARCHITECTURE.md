# Technical Architecture — CogniRoute

This document explains the system design, data models, and workflow architecture implemented in the CogniRoute application.

---

## 1. Relational Database Schema Rationale

CogniRoute implements a clean relational schema to ensure auditability, transactional consistency, and fast search indexing.

```
┌──────────────────┐       ┌──────────────────────┐
│     accounts     │       │   customer_requests  │
│      (User)      │       │                      │
│ ──────────────── │       │ ──────────────────── │
│  id        (PK)  │◄──┐   │  id             (PK) │
│  username  (UK)  │   │   │  source_channel      │
│  role   (choice) │   │   │  customer_name       │
│                  │   │   │  original_message    │
│                  │   │   │  status        (IDX) │
│                  │   │   │  cat_snapshot  (IDX) │
│                  │   │   │  pri_snapshot  (IDX) │
│                  │   │   │  idempotency   (UK)  │
│                  │   │   │  created_at    (IDX) │
└──────────────────┘   │   └──────────────────────┘
         │             │        │          │
         │             │        │          ├────────────────────┐
         ▼             │        ▼                               ▼
┌──────────────────┐   │   ┌──────────────────────┐   ┌──────────────────────┐
│  internal_notes  │   │   │  ai_classifications  │   │    request_events    │
│                  │   │   │                      │   │     (Audit Log)      │
│ ──────────────── │   │   │ ──────────────────── │   │ ──────────────────── │
│  id         (PK) │   │   │  id             (PK) │   │  id             (PK) │
│  request_id (FK) │───┘   │  request_id     (FK) │   │  request_id     (FK) │
│  author_id  (FK) │       │  provider    (char)  │   │  event_type    (IDX) │
│  body     (text) │       │  category    (char)  │   │  old_value     (str) │
│  created_at(IDX) │       │  priority    (char)  │   │  new_value     (str) │
└──────────────────┘       │  summary     (text)  │   │  actor         (str) │
                           │  confidence  (float) │   │  metadata     (JSON) │
                           │  reason      (text)  │   │  timestamp     (IDX) │
                           │  raw_output  (JSON)  │   └──────────────────────┘
                           │  status       (IDX)  │
                           │  error_message(text) │
                           │  retry_count  (int)  │
                           │  created_at   (IDX)  │
                           └──────────────────────┘
```

### Separating Classification Details from Request Attributes
The `AIClassification` database table is separate from the `CustomerRequest` table. This design addresses several critical production needs:
1. **Historical Audits**: As AI models update or prompt parameters change, a single request may undergo several classification runs (especially after manual trigger retries). Storing them in a separate table preserves every classification attempt.
2. **Failure Logging**: If the AI API crashes or times out, we store the error string in the classification attempt record and preserve the original request state.
3. **Multi-Model Comparisons**: It allows running evaluations comparing Gemini vs OpenAI side-by-side on the same request object.
4. **Fast Queries via Snapshots**: To keep dashboard queries fast, the latest successful classification category and priority are copied into the `category_snapshot` and `priority_snapshot` fields of the request table. This allows indexed filtering without performing joins.

---

## 2. Background Classification Pipeline

When a customer request is received (via the API or a WhatsApp webhook):
1. **Atomic DB Save**: The request is created in `new` status. An event `created` is logged.
2. **Celery Task Dispatch**: The request status is set to `queued`, an event `queued` is logged, and a Celery worker task `classify_request.delay(request_id)` is dispatched.
3. **Response Issued**: The API issues a `201 Created` response to the client immediately, containing the request ID. **The API call does not block on AI latency.**
4. **Worker Execution**: The Celery worker picks up the task, logs `classification_started`, and queries the active AI Provider class.
5. **DB Update & Broadcast**: Upon completing the query, the worker updates the snapshots, writes the `AIClassification` results, logs the `classified` event inside a transaction block, and broadcasts the event to the Redis channels layer.

---

## 3. Real-time Synchronization (Django Channels)

- **WebSocket Authentication**: Browsers do not natively allow passing Custom Headers during standard `new WebSocket()` creation. CogniRoute secures WebSockets by passing the JWT access token in the query string (`/ws/updates/?token=jwt_here`). A custom `JWTAuthMiddleware` interceptor decodes this query parameter and associates the authenticated user to the connection scope. If the token is invalid or missing, it rejects the handshake with a `4003 Forbidden` code.
- **Channel Layer broadcasting**: When events occur (e.g. Note logged, Status changed, AI finished), the Django thread notifies the group `dashboard_updates` via `channels_redis`.
- **UI Patching**: The SPA dashboard listens to this socket and patches row items in-place or reloads page data without requiring a full browser refresh.
