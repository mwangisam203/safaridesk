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
| SMS | Africa's Talking via Celery tasks |
| Package Manager | uv |

---

## Current Status

SafariDesk currently has:

- Auth endpoints for registration, email verification/resend, login, profile lookup, and logout.
- JWT access and refresh token generation.
- Signed 24-hour email verification links delivered through Celery.
- PostgreSQL models and Alembic migrations for users, subscriptions, transactions, articles, audit logs, free reads, and anonymous reads.
- M-Pesa STK Push initiation for BASIC and PRO subscriptions.
- M-Pesa callback handling with pending transaction lookup and idempotency guard.
- Subscription activation after successful payment callbacks.
- Celery email tasks for payment confirmation and failed payments.
- Celery SMS task for Africa's Talking payment confirmation messages.
- A reconciler task for old pending M-Pesa transactions.
- Article listing, search, full article access, anonymous/free read limits, email capture, and admin article CRUD.
- Payment tests covering STK Push and M-Pesa callback success/failure flows.

Current test status:

```bash
uv run pytest -q
# 64 passed
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
│   ├── content/             # Versioned starter article catalog
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Auth, email, M-Pesa, subscription logic
│   └── tasks/               # Celery email and reconciler tasks
├── alembic/                 # Database migrations
├── frontend/                # React, Vite, and Tailwind reader application
├── scripts/                 # Maintenance and content sync commands
├── tests/                   # Pytest tests
├── main.py                  # FastAPI entry point
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Locked dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
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

---

## Running Locally

Start the API in one terminal:

```bash
uv run uvicorn main:app --reload --port 8000
```

Start the React frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Vite proxies API requests to the FastAPI server
on port `8000`.

For deployed frontends where the API is on a separate origin, set:

```env
VITE_API_BASE_URL=https://api.your-domain.com
```

Leave `VITE_API_BASE_URL` empty during local development to keep using the Vite
proxy.

Expose the API to other devices on your network:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
uv run pytest -q
```

Sync the versioned article catalog into PostgreSQL:

```bash
uv run python -m scripts.sync_articles
```

### Running With Docker

Docker Compose can run the full local SafariDesk stack:

- FastAPI API on `http://localhost:8000`
- React frontend on `http://localhost:3000`
- PostgreSQL exposed on `localhost:5433`
- Redis exposed on `localhost:6380`
- Celery worker
- Celery Beat scheduler

Create the Docker environment file:

```bash
cp .env.docker.example .env.docker
```

Start everything:

```bash
docker compose up --build
```

Docker runs `alembic upgrade head` through the `migrate` service before the API,
worker, and Beat start. If you create a new migration while the stack is already
running, apply it manually with:

```bash
docker compose exec api alembic upgrade head
```

Optional: seed the starter article catalog:

```bash
docker compose exec api python -m scripts.sync_articles
```

Stop the stack:

```bash
docker compose down
```

Remove Docker database and upload volumes when you want a clean reset:

```bash
docker compose down -v
```

Use local terminal commands when you want the fastest edit-refresh loop. Use
Docker when you want the whole app, worker, scheduler, Redis, and database to
run together in a deployment-like environment.

### Backend Deployment

The repository includes a Render Blueprint at `render.yaml` for the first
staging backend service. It deploys the FastAPI API from the root `Dockerfile`,
runs `alembic upgrade head` before the service starts, and uses `/health` as
the platform health check.

Do not paste passwords, Neon URLs, AWS keys, M-Pesa credentials, SMS keys, or
mail passwords into `render.yaml`. That file is committed to GitHub. Values
marked with `sync: false` must be entered in the Render dashboard.

Daraja does not sign or otherwise authenticate its STK Push callback requests.
`MPESA_CALLBACK_SECRET` is what stops anyone who learns a `CheckoutRequestID`
(returned to the user themselves from `/stk-push`) from POSTing a forged
"payment succeeded" body to `mpesa-callback` and getting a subscription
activated without paying. Set it to a long random value and append it as a
`secret` query parameter on `MPESA_CALLBACK_URL`. Leaving it unset disables the
check — fine for quick local experiments, not for anything reachable from the
internet.

The deployed backend exposes the same API surface as local development:

- `GET /health`
- `/api/v1/auth/*`
- `/api/v1/content/articles`
- `/api/v1/content/admin/articles`
- `/api/v1/payments/*`
- `/api/v1/users/*`

Before syncing the Blueprint, create or choose external services for:

- PostgreSQL, such as Neon or Render Postgres
- Redis or a Redis-compatible service
- SMTP credentials
- Africa's Talking credentials
- M-Pesa Daraja credentials
- S3 bucket and public CDN/base URL

Set dashboard-managed Render variables marked with `sync: false`, especially:

```env
APP_BASE_URL=https://safaridesk-api.onrender.com
FRONTEND_URL=https://your-frontend-domain.com
DATABASE_URL=...
REDIS_URL=...
AUTH_EMAIL_DELIVERY_MODE=direct
MPESA_CALLBACK_SECRET=...
MPESA_CALLBACK_URL=https://safaridesk-api.onrender.com/api/v1/payments/mpesa-callback?secret=...
MAIL_USERNAME=...
MAIL_PASSWORD=...
AT_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
S3_PUBLIC_BASE_URL=...
```

For early production without a paid worker, keep:

```env
AUTH_EMAIL_DELIVERY_MODE=direct
```

With that setting, registration verification emails and password reset emails
send inside the web request. This is acceptable for low traffic, but the request
can be slower if SMTP is slow.

Full background work requires three live pieces:

- Render Key Value or another Redis-compatible service.
- `safaridesk-worker`, running:
  `celery -A app.core.celery_app.celery_app worker --loglevel=info`
- `safaridesk-beat`, running:
  `celery -A app.core.celery_app.celery_app beat --loglevel=info`

Use the same `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `FRONTEND_URL`, and mail
variables on the web service and worker. Beat also needs `DATABASE_URL`,
`REDIS_URL`, and `SECRET_KEY`. When you add a worker, set
`AUTH_EMAIL_DELIVERY_MODE=celery` on the web service. Without worker + Redis,
payment emails/SMS, subscription reminders, expiry processing, and reconciliation
jobs will not run.

After deployment, verify:

```bash
curl https://safaridesk-api.onrender.com/health
```

Then test login, public article listing, password reset email, verification
email resend, a protected admin article route, and Swagger at `/docs`.

Where those values live:

- `render.yaml` line near `DATABASE_URL`: declares that Render needs the
  database variable, but does not store the secret.
- Render dashboard: open the `safaridesk-api` service, then go to
  **Environment** and paste the real value there.
- Neon dashboard: open **Connect**, copy the pooled connection string, then use
  it as Render's `DATABASE_URL`.

For the Neon pooled URL, Render should receive:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require&channel_binding=require
```

For local Docker Compose, keep using `.env.docker`; do not put the Neon URL in
`.env.docker.example`.

### Content Workflow

PostgreSQL is the runtime source of truth for published articles. The catalog in
`app/content/article_catalog.py` provides versioned starter content and can be
synced repeatedly without creating duplicate rows or resetting publication
dates and view counts.

Use the catalog for content that should be reproducible across local, test, and
demo environments. Ongoing editorial work should be managed through protected
admin article endpoints, with draft, preview, publish, and unpublish controls.
Admin access is granted by the database `is_admin` flag, not by hard-coding an
email address in application code.

To bootstrap the first admin without editing SQL manually, register the user
normally, point `DATABASE_URL` at the target database, then run:

```bash
uv run python -m scripts.promote_admin tedpierson328@gmail.com
```

After the first admin exists, use `/admin/users` to manage user access from the
application.

### Admin Publishing

Verified, active users with `is_admin=true` can open the editorial workspace at
`http://localhost:3000/admin/articles`.

The admin workflow supports:

- Listing published articles and drafts
- Showing author, view count, status, tier, and last update in the article table
- Creating and editing articles in Markdown
- Live editor preview and protected full-screen draft preview before publishing
- BASIC or PRO access-tier selection
- Categories, featured status, cover image URLs, and image alt text
- Admin cover-image uploads with type and size validation
- Automatic WebP conversion, metadata removal, and large-image resizing
- SEO titles and descriptions
- Publishing, unpublishing, and deleting articles
- Audit records for article creation, updates, publishing, unpublishing, and deletion

The frontend hides admin navigation from regular users, but FastAPI performs the
authoritative active, verified, and admin checks for every management request.
Cover images can use project paths such as `/covers/example.webp` during local
development or CDN/S3 URLs in production. The editor accepts JPEG, PNG, and
WebP uploads up to 8 MB. Development uploads are written to
`frontend/public/uploads/articles/` and are intentionally excluded from Git.

For production image storage, configure:

```env
IMAGE_STORAGE_BACKEND=s3
IMAGE_UPLOAD_MAX_MB=8
IMAGE_MAX_WIDTH=2000
IMAGE_MAX_HEIGHT=1250
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-1
S3_BUCKET_NAME=safaridesk-assets
S3_PUBLIC_BASE_URL=https://cdn.safaridesk.com
```

The AWS identity should have narrowly scoped `s3:PutObject` access to the
bucket's `articles/*` prefix. Serve uploaded objects through a public,
read-only CloudFront distribution or another configured CDN; AWS credentials
must never be exposed to the frontend. PostgreSQL stores only the resulting
URL and meaningful cover-image alt text. Changing image storage does not
require a database migration.

Active, verified admins can also discover and read every published BASIC and PRO
article without a paid subscription. Admin reads never consume the registered
free-article allowance, and the user's stored subscription tier remains
unchanged.

### Browser Sessions

Access tokens expire after 30 minutes and refresh tokens after 7 days by
default. The frontend automatically rotates the token pair after an API request
receives `401 Unauthorized`, retries the original request once, and keeps the
user signed in across browser refreshes.

The user is logged out when the refresh token is missing, expired, invalid, or
belongs to an inactive account. Access and refresh tokens carry different token
types and cannot be used interchangeably.

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
| GET | `/api/v1/auth/verify-email?token=...` | Verify email using signed link | No |
| POST | `/api/v1/auth/resend-verification` | Send another verification email | Yes |
| POST | `/api/v1/auth/resend-verification-email` | Send verification email by account email | No |
| POST | `/api/v1/auth/forgot-password` | Request password reset email | No |
| POST | `/api/v1/auth/reset-password` | Reset password using signed token | No |
| POST | `/api/v1/auth/logout` | Logout client-side JWT session | Yes |
| POST | `/api/v1/auth/test-email` | Send test email | No |

### Payments

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/payments/plans` | List selectable BASIC/PRO subscription plans | No |
| POST | `/api/v1/payments/stk-push` | Start M-Pesa STK Push for BASIC/PRO subscription | Verified user |
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
| GET | `/api/v1/users/admin/users` | List users for admin management | Admin |
| PATCH | `/api/v1/users/admin/users/{id}` | Update user tier/status/admin flags | Admin |

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
- [x] Signed email verification links with resend support
- [x] Verification required for payments and admin content management
- [x] Auth tests for registration, login, inactive accounts, and protected profile access

### Sprint 2 - M-Pesa Payments: Mostly Implemented

- [x] M-Pesa Daraja service integration
- [x] STK Push endpoint
- [x] Selectable BASIC/PRO plans before payment
- [x] Pending transaction persistence
- [x] M-Pesa callback endpoint
- [x] Callback idempotency guard for already-processed transactions
- [x] Subscription upgrade on confirmed payment
- [x] Payment confirmation/failure email tasks via Celery
- [x] Payment flow tests for STK Push and callback success/failure
- [x] Harden reconciler completion behavior around missing receipt numbers
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
- [x] Tests for content gating and subscription expiry
- [x] Tests for subscription activation and admin article management
- [x] Subscription expiry automation with 3-day grace period and FREE downgrade
- [x] Renewal reminder email/SMS notifications in the final 4 days
- [x] Africa's Talking SMS payment confirmation notifications

### Sprint 4 - Refunds and Reporting: Planned

- [ ] B2C refund system
- [ ] Payment history dashboard/API
- [ ] Admin revenue reports
- [ ] PDF receipt generation

### Sprint 5 - Security and Testing: Planned

- [ ] Redis rate limiting
- [ ] Full audit logging
- [x] Broader pytest coverage across auth, content, subscription, and payment flows
- [x] Pydantic/SQLAlchemy/password-hashing deprecation cleanup

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
- `APP_BASE_URL`
- `FRONTEND_URL`
- `EMAIL_VERIFICATION_EXPIRE_HOURS`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_BUSINESS_SHORT_CODE`
- `MPESA_PASSKEY`
- `MPESA_CALLBACK_URL`
- `MPESA_CALLBACK_SECRET`
- `MPESA_ENVIRONMENT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_SERVER`
- `MAIL_PORT`
- `IMAGE_STORAGE_BACKEND`
- `IMAGE_UPLOAD_DIR`
- `IMAGE_UPLOAD_MAX_MB`
- `IMAGE_MAX_WIDTH`
- `IMAGE_MAX_HEIGHT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `S3_PUBLIC_BASE_URL`

---

## Author

**Sam Mwangi**  
Backend Developer | Python | FastAPI | PostgreSQL | Fintech  
Nairobi, Kenya  
GitHub: github.com/mwangisam203
