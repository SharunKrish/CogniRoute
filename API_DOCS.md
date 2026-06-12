# API Documentation — CogniRoute

All requests should be sent to `/api/` or `/api/auth/` and must include `Content-Type: application/json`. Protected endpoints require `Authorization: Bearer <access_token>`.

---

## 1. Authentication Endpoints

### Register New User
* **Method & Route**: `POST /api/auth/register/`
* **Auth**: Public
* **Payload**:
  ```json
  {
    "username": "agent_emma",
    "email": "emma@cognifyr.co",
    "password": "agentpassword123",
    "role": "agent"
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "user": {
      "id": 3,
      "username": "agent_emma",
      "email": "emma@cognifyr.co",
      "role": "agent"
    },
    "message": "User registered successfully."
  }
  ```

### User Login (Obtain Tokens)
* **Method & Route**: `POST /api/auth/login/`
* **Auth**: Public
* **Payload**:
  ```json
  {
    "username": "agent_emma",
    "password": "agentpassword123"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "access": "eyJhbGciOi...",
    "refresh": "eyJhbGciOi..."
  }
  ```

### Refresh Token
* **Method & Route**: `POST /api/auth/refresh/`
* **Auth**: Public
* **Payload**:
  ```json
  {
    "refresh": "refresh_token_here"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "access": "new_access_token_here",
    "refresh": "new_refresh_token_here"
  }
  ```

### Current User Profile
* **Method & Route**: `GET /api/auth/me/`
* **Auth**: Required
* **Success Response (200 OK)**:
  ```json
  {
    "id": 3,
    "username": "agent_emma",
    "email": "emma@cognifyr.co",
    "role": "agent",
    "is_staff": false,
    "is_superuser": false
  }
  ```

---

## 2. Customer Requests Queue Endpoints

### Create Request (Enqueues AI Classification)
* **Method & Route**: `POST /api/requests/`
* **Auth**: Required
* **Headers**: `Idempotency-Key` (Optional UUID or hash string to prevent duplicate submissions)
* **Payload**:
  ```json
  {
    "customer_name": "Tony Stark",
    "customer_email": "tony@starkindustries.com",
    "source_channel": "website",
    "original_message": "Need a pricing quote for custom arc reactor integrations.",
    "idempotency_key": "some-unique-transaction-key"
  }
  ```
* **Success Response (210 Created)**:
  ```json
  {
    "id": 12,
    "source_channel": "website",
    "customer_name": "Tony Stark",
    "customer_email": "tony@starkindustries.com",
    "original_message": "Need a pricing quote...",
    "status": "queued",
    "category_snapshot": null,
    "priority_snapshot": null,
    "idempotency_key": "some-unique-transaction-key",
    "created_at": "2026-06-11T12:00:00Z",
    "updated_at": "2026-06-11T12:00:01Z"
  }
  ```

### List & Filter Requests
* **Method & Route**: `GET /api/requests/`
* **Auth**: Required
* **Parameters (Query String)**:
  * `status`: filter by request status choice (e.g. `new`, `queued`, `classified`, `in_progress`, `resolved`, `closed`)
  * `category`: filter by classification category (`sales`, `support`, `urgent`, `spam`, `other`)
  * `priority`: filter by priority (`low`, `medium`, `high`)
  * `search`: text query matching customer name, email, or message.
  * `page`: page number (pagination defaults to 20 results per page)
* **Success Response (200 OK)**:
  ```json
  {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 12,
        "source_channel": "website",
        "customer_name": "Tony Stark",
        "customer_email": "tony@starkindustries.com",
        "status": "classified",
        "category_snapshot": "sales",
        "priority_snapshot": "medium",
        "created_at": "2026-06-11T12:00:00Z"
      }
    ]
  }
  ```

### Get Request Details
* **Method & Route**: `GET /api/requests/:id/`
* **Auth**: Required
* **Success Response (200 OK)**:
  ```json
  {
    "id": 12,
    "source_channel": "website",
    "customer_name": "Tony Stark",
    "customer_email": "tony@starkindustries.com",
    "original_message": "Need a pricing quote...",
    "status": "classified",
    "category_snapshot": "sales",
    "priority_snapshot": "medium",
    "idempotency_key": "some-unique-transaction-key",
    "created_at": "2026-06-11T12:00:00Z",
    "updated_at": "2026-06-11T12:05:00Z",
    "classifications": [
      {
        "id": 1,
        "provider": "mock",
        "category": "sales",
        "priority": "medium",
        "summary": "[SALES] Quote query from Tony Stark",
        "confidence": 0.92,
        "reason": "Request exhibits purchase interest...",
        "status": "completed",
        "error_message": null,
        "retry_count": 0,
        "created_at": "2026-06-11T12:00:02Z"
      }
    ],
    "notes": [
      {
        "id": 1,
        "author": { "id": 1, "username": "admin", "role": "admin" },
        "body": "Assigned to sales unit",
        "created_at": "2026-06-11T12:04:00Z"
      }
    ],
    "events": [
      { "id": 1, "event_type": "created", "old_value": null, "new_value": "new", "actor": "agent_emma", "timestamp": "2026-06-11T12:00:00Z" },
      { "id": 2, "event_type": "queued", "old_value": "new", "new_value": "queued", "actor": "system", "timestamp": "2026-06-11T12:00:01Z" },
      { "id": 3, "event_type": "classified", "old_value": null, "new_value": "classified", "actor": "system", "timestamp": "2026-06-11T12:00:02Z" }
    ]
  }
  ```

### Patch Request Status
* **Method & Route**: `PATCH /api/requests/:id/status/`
* **Auth**: Required
* **Payload**:
  ```json
  {
    "status": "in_progress"
  }
  ```
* **Success Response (200 OK)**: Detailed Request Object (with updated status and logged status_changed event)

### Add Internal Note
* **Method & Route**: `POST /api/requests/:id/notes/`
* **Auth**: Required
* **Payload**:
  ```json
  {
    "body": "Investigating technical specs of customer request."
  }
  ```
* **Success Response (200 OK)**: Detailed Request Object (with appended notes list and logged note_added event)

### Manual Retry Classification
* **Method & Route**: `POST /api/requests/:id/retry-classification/`
* **Auth**: Required
* **Success Response (200 OK)**: Detailed Request Object (sets request to queued and spawns Celery classifier)

---

## 3. Simulated Inbound Webhook

### Receive Message (WhatsApp/Email simulation)
* **Method & Route**: `POST /api/webhooks/inbound/`
* **Auth**: Public (HMAC Verified)
* **Required Headers**:
  - `X-Webhook-Signature`: HMAC SHA256 signature calculated with webhook secret on request body bytes.
  - Or `X-Cognifyr-Secret`: Plain text secret token matching settings.WEBHOOK_SECRET (for manual/dev testing).
* **Payload**:
  ```json
  {
    "sender_name": "Bruce Banner",
    "sender_email": "banner@avengers.org",
    "channel": "whatsapp",
    "message": "URGENT: Gamma radiation tracker is broken down and crashed!",
    "idempotency_key": "webhook-bruce-gamma-tracker-1"
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "message": "Webhook request enqueued successfully.",
    "request_id": 15,
    "status": "queued"
  }
  ```
