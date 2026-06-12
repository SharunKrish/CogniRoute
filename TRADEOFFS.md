# Engineering Tradeoffs & Future Roadmaps — CogniRoute

This document summarizes the technical choices, limitations, and future improvements planned for the CogniRoute application.

---

## 1. Technical Tradeoffs Made

### SQLite in Development vs PostgreSQL in Production
- **Decision**: Used SQLite locally for development speed and zero local setup overhead. Configured the code to parse `DATABASE_URL` dynamically to swap to PostgreSQL for Render deployment or Docker Compose runs.
- **Tradeoff**: SQLite has locking limitations for highly concurrent writes. While suitable for local MVPs, production environments MUST use the PostgreSQL engine configured in our Docker and Render templates.

### Celery/Redis for Queues
- **Decision**: Adopted Celery with Redis for background processing.
- **Tradeoff**: Celery is a heavy-weight task queue that requires a Redis broker service running. For a smaller deployment without a broker, standard Python threads or Django Channels background workers could run inside the web container. However, using Celery ensures that if the Django ASGI process restarts or hangs, task execution state is not lost and queued items will still finish processing.

### Custom JWT Query-String Authentication for WebSockets
- **Decision**: Passed the JWT in the query string parameters during WebSocket connection handshakes (`/ws/updates/?token=<token>`).
- **Tradeoff**: Query string parameters can sometimes be logged in server logs or proxy logs, making them slightly less secure than standard headers. However, since browsers do not support sending custom headers in the native `WebSocket` API constructor, the query string approach is the standard industry practice. We mitigate risk by setting short-lived JWT tokens (2 hours) and verifying signatures on the server side instantly.

---

## 2. Security & Reliability Highlights

- **Database Transaction Protection**: Used `with transaction.atomic()` in views and Celery tasks to ensure audit events and status transitions are rolled back atomically if a database error happens mid-operation.
- **HMAC Signatures**: The webhook endpoint `/api/webhooks/inbound/` uses HMAC SHA256 header signature checks. An attacker cannot submit spam messages to the queue without knowing the webhook secret token.
- **API Throttling**: Integrated default Django REST Framework throttles (`30 requests/min` for anonymous routes, `120 requests/min` for signed-in sessions) to block denial-of-service abuse.
- **Prompt Injection Defense**: The system prompts in `GeminiProvider` explicitly declare that user messages are raw untrusted content. No parts of customer inquiries are executed or treated as instructions.

---

## 3. What I Would Do With "Two More Weeks"

Given more time, I would implement these enterprise-grade features:

1. **AI Cost & Latency Dashboard**: Add charts analyzing the latency and API token cost per request. This helps administrators evaluate whether switching providers (e.g. Gemini 1.5 Flash to Pro) is worth the cost.
2. **User Role-Based Access Controls (RBAC)**: Enhance permissions so that support agents can only view, annotate, and resolve requests assigned to them, while Administrators retain permissions to delete, retry classifications, or modify routing parameters.
3. **Advanced AI Skill Orchestrator (Multi-Agent Routing)**: Extend classification to select and load specialized agent pipelines (e.g. if category is `sales`, load a sales-lead-generator agent that fetches company metadata using a search API and appends it to the internal notes).
4. **Out-of-the-Box OAuth Provider Integration**: Support login using Google OAuth or workspace accounts, eliminating the need to manage internal credentials.
5. **Real-time Live Logs Console**: Build a dashboard view displaying Celery worker status, queue sizes, and live LLM latency graphs in real-time.
