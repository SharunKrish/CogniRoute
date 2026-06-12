# Engineering Tradeoffs & Future Roadmaps — CogniRoute

This document summarizes the technical choices, limitations, and future improvements planned for the CogniRoute application.

---

## 1. Technical Tradeoffs Made

### SQLite in Development vs PostgreSQL in Production
- **Decision**: Used SQLite locally for development speed and zero local setup overhead. Configured the code to parse `DATABASE_URL` dynamically to swap to PostgreSQL for Render deployment or Docker Compose runs.
- **Tradeoff**: SQLite has locking limitations for highly concurrent writes. While suitable for local MVPs, production environments MUST use the PostgreSQL engine configured in our Docker and Render templates.

### Celery/Redis for Queues & Production Memory Management
- **Decision**: Adopted Celery with Redis for background processing. In production, we integrated with **Upstash Serverless Redis** and configured Django/Celery to accept `rediss://` TLS URLs with explicit SSL context overrides (`ssl_cert_reqs='none'`) to handle serverless Redis handshakes.
- **Tradeoff**: Celery is a heavy-weight queue manager that defaults to a prefork pool, which spawns multiple processes and easily crashes the 512MB RAM free-tier container limit on Render. To solve this, we configured the production worker command to run Celery with the **solo execution pool** (`-P solo`). This keeps all task processes inside a single thread, reducing the backend container footprint to a stable ~110MB.

### Decoupled Hosting Architecture (Vercel & Render)
- **Decision**: Separated the single-page application (SPA) client onto **Vercel** and deployed the Django server / Celery worker onto **Render**.
- **Tradeoff**: Decoupling the client requires configuring Cross-Origin Resource Sharing (CORS) lists and Cross-Site Request Forgery (CSRF) trusted origins on the Django backend. However, it ensures that static asset delivery is offloaded to Vercel's global Edge CDN network, preserving Render web container CPU and memory strictly for API handling, WebSocket connections, and background classification tasks.

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
2. **Fine-Grained RBAC with Assignment Scoping**: The current system enforces admin-only permissions for destructive actions (delete, retry classification). Enhance this further so that support agents can only view and annotate requests specifically assigned to them, rather than seeing the full queue.
3. **Advanced AI Skill Orchestrator (Multi-Agent Routing)**: Extend classification to select and load specialized agent pipelines (e.g. if category is `sales`, load a sales-lead-generator agent that fetches company metadata using a search API and appends it to the internal notes).
4. **Out-of-the-Box OAuth Provider Integration**: Support login using Google OAuth or workspace accounts, eliminating the need to manage internal credentials.
5. **Real-time Live Logs Console**: Build a dashboard view displaying Celery worker status, queue sizes, and live LLM latency graphs in real-time.
