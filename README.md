# SafariDesk

> Paid Technical Knowledge Platform for African Developers
> Built in Nairobi, Kenya

SafariDesk is a subscription-based platform where developers across Africa can
access premium technical content and pay with M-Pesa.

No credit card required. Just a Kenyan phone number.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Queue | Redis + Celery |
| Payments | M-Pesa Daraja API |
| Email | Mailtrap/dev SMTP via Celery tasks |
| Package Manager | uv |

---

## Current Status

SafariDesk currently has:

- Auth endpoints for registration, login, Swagger OAuth2 token login, profile lookup, and logout.
- JWT access and refresh token generation.
- PostgreSQL models and Alembic migrations for users, subscriptions, transactions, articles, audit logs, free reads, and anonymous reads.
- M-Pesa STK Push initiation for BASIC and PRO subscriptions.
- M-Pesa callback handling with pending transaction lookup and idempotency guard.
- Subscription activation after successful payment callbacks.
- Celery email tasks for payment confirmation and failed payments.
- A reconciler task for old pending M-Pesa transactions.
- Article listing, search, full article access, anonymous/free read limits, email capture, and admin article CRUD.
- Payment tests covering STK Push and M-Pesa callback success/failure flows.

Current test status:

```bash
uv run pytest -q
# 4 passed
```

---

## Project Structure

```text
safaridesk/
├── app/
│   ├── api/v1/
│   │   ├── auth.py          # Auth endpoints
│   │   ├── content.py       # Articles, gating, email capture, admin article CRUD
│   │   ├── payments.py      # M-Pesa STK Push and callback endpoints
│   │   └── users.py         # User subscription status endpoint
│   ├── core/
│   │   ├── celery_app.py    # Celery app configuration
│   │   ├── config.py        # Environment settings
│   │   ├── dependencies.py  # Auth/subscription dependencies
│   │   └── security.py      # JWT and password hashing
│   ├── db/
│   │   ├── base.py          # SQLAlchemy engine/session base
│   │   └── session.py       # FastAPI DB session dependency
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Auth, email, M-Pesa, subscription logic
│   └── tasks/               # Celery email and reconciler tasks
├── alembic/                 # Database migrations
├── tests/                   # Pytest tests
├── main.py                  # FastAPI entry point
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Locked dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis, for Celery/background jobs
- uv

### Setup

```bash
# Clone the repo
git clone https://github.com/mwangisam203/safaridesk.git
cd safaridesk

# Install dependencies
uv sync

# Create and fill your environment file
cp .env.example .env

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

If `.env.example` is not present in your local checkout, create `.env` with the
variables listed in `app/core/config.py`.

---

## Running Locally

Start the API:

```bash
uv run uvicorn main:app --reload --port 8000
```

Expose the API to other devices on your network:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
uv run pytest -q
```

---

## API Endpoints

### System

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Welcome message | No |
| GET | `/health` | Health check | No |

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login and return JWT tokens | No |
| POST | `/api/v1/auth/token` | Swagger OAuth2 login | No |
| GET | `/api/v1/auth/me` | Get current user | Yes |
| POST | `/api/v1/auth/logout` | Logout client-side JWT session | Yes |
| POST | `/api/v1/auth/test-email` | Send test email | No |

### Payments

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/payments/stk-push` | Start M-Pesa STK Push for BASIC/PRO subscription | Yes |
| POST | `/api/v1/payments/mpesa-callback` | Safaricom M-Pesa callback endpoint | No |

### Content

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/content/articles` | List published articles | No |
| GET | `/api/v1/content/articles/search?q=...` | Search published articles | No |
| GET | `/api/v1/content/articles/{slug}` | Read article with tier/free-read rules | No |
| POST | `/api/v1/content/email-capture` | Capture anonymous reader email after soft wall | No |
| POST | `/api/v1/content/admin/articles` | Create article | Admin |
| PATCH | `/api/v1/content/admin/articles/{slug}` | Update article | Admin |
| DELETE | `/api/v1/content/admin/articles/{slug}` | Delete article | Admin |

### Users

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/users/me/subscription` | Get current user's subscription status | Yes |

---

## Database Schema

### Users

Stores account identity, phone number, password hash, account status, admin flag,
and denormalized subscription tier for fast access checks.

### Subscriptions

Tracks each user's subscription tier, status, start date, expiry date, and
lifecycle state.

### Transactions

Records M-Pesa payment attempts, request IDs, receipt number, amount, tier,
status, failure reason, raw callback payload, and completion timestamp.

### Articles

Stores technical content with slug, summary, body, author, publication status,
view count, and BASIC/PRO tier.

### Free and Anonymous Reads

Tracks registered FREE-user reads and anonymous fingerprint-based reads so the
content wall can enforce the 10-article window.

### Audit Logs

Intended as an append-only log for significant system actions.

---

## Sprint Progress

### Sprint 1 - Auth System: Complete

- [x] Project structure and folder organization
- [x] PostgreSQL database setup
- [x] Alembic migrations
- [x] User registration with Kenyan phone validation
- [x] JWT authentication with access and refresh tokens
- [x] Protected routes with dependency injection
- [x] Password hashing with bcrypt
- [x] Email service setup

### Sprint 2 - M-Pesa Payments: Mostly Implemented

- [x] M-Pesa Daraja service integration
- [x] STK Push endpoint
- [x] Pending transaction persistence
- [x] M-Pesa callback endpoint
- [x] Callback idempotency guard for already-processed transactions
- [x] Subscription upgrade on confirmed payment
- [x] Payment confirmation/failure email tasks via Celery
- [x] Payment flow tests for STK Push and callback success/failure
- [ ] Harden reconciler completion behavior around missing receipt numbers
- [ ] Add live sandbox/manual Daraja verification notes

### Sprint 3 - Content and Subscription Lifecycle: In Progress

- [x] User subscription status endpoint
- [x] BASIC/PRO article tier model
- [x] Article listing and search
- [x] Anonymous reader soft wall and hard wall
- [x] Email capture for anonymous readers
- [x] FREE registered user read tracking
- [x] Admin article create/update/delete endpoints
- [x] Reconciler task for stale pending payments
- [ ] Subscription expiry automation that downgrades expired users
- [ ] Renewal reminder emails
- [ ] Tests for content gating and subscription expiry
- [ ] Africa's Talking SMS notifications

### Sprint 4 - Refunds and Reporting: Planned

- [ ] B2C refund system
- [ ] Payment history dashboard/API
- [ ] Admin revenue reports
- [ ] PDF receipt generation

### Sprint 5 - Security and Testing: Planned

- [ ] Redis rate limiting
- [ ] Full audit logging
- [ ] Broader pytest coverage across auth, content, subscription, and payment flows
- [ ] Pydantic/SQLAlchemy deprecation cleanup

### Sprint 6 - Deployment: Planned

- [ ] Docker and Docker Compose
- [ ] AWS EC2/RDS/ElastiCache deployment
- [ ] GitHub Actions CI/CD
- [ ] Custom domain and HTTPS

---

## Key Design Decisions

**Why FastAPI?**
Modern, fast, automatic OpenAPI docs, native async support, and strong Pydantic
integration for request validation.

**Why JWT with two tokens?**
Access tokens expire quickly, limiting damage from theft. Refresh tokens allow
renewal without forcing the user to log in repeatedly.

**Why store phone numbers in +254 format?**
M-Pesa Daraja expects Kenyan numbers in international format. Normalizing phone
numbers before payment keeps the payment flow simpler.

**Why store raw M-Pesa callbacks?**
Payment systems need traceability. Keeping the raw callback helps with disputes,
debugging, idempotency reviews, and reconciliation.

**Why track anonymous reads separately from registered free reads?**
Anonymous readers are identified by a long-lived fingerprint cookie, while
registered users are tracked by user ID. Keeping those flows separate makes the
content wall easier to reason about.

---

## Environment Variables

The app loads settings from `.env` through `app/core/config.py`.

Required:

- `SECRET_KEY`
- `DATABASE_URL`

Common local/development values:

- `REDIS_URL`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_BUSINESS_SHORT_CODE`
- `MPESA_PASSKEY`
- `MPESA_CALLBACK_URL`
- `MPESA_ENVIRONMENT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_SERVER`
- `MAIL_PORT`

---

## Author

**Sam Mwangi**  
Backend Developer | Python | FastAPI | PostgreSQL | Fintech  
Nairobi, Kenya  
GitHub: github.com/mwangisam203
