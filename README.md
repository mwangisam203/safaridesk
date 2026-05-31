# SafariDesk README

---

# SafariDesk 🦁

> Paid Technical Knowledge Platform for African Developers
> Built in Nairobi, Kenya 🇰🇪

SafariDesk is a subscription-based platform where developers across
Africa access premium technical content, paid via M-Pesa.
No credit card required — just a Kenyan phone.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Cache/Queue | Redis + Celery (Sprint 2) |
| Payments | M-Pesa Daraja API (Sprint 2) |
| SMS | Africa's Talking (Sprint 3) |
| Email | Mailtrap (dev) / Resend (prod) |
| Deployment | Docker + AWS (Sprint 6) |
| Package Manager | uv |

---

## Project Structure

```
safaridesk/
├── app/
│   ├── api/v1/
│   │   └── auth.py           # Auth endpoints
│   ├── core/
│   │   ├── config.py         # Environment settings
│   │   ├── security.py       # JWT + password hashing
│   │   └── dependencies.py   # FastAPI dependencies
│   ├── db/
│   │   ├── base.py           # SQLAlchemy engine
│   │   └── session.py        # Database session
│   ├── models/
│   │   ├── user.py           # Users table
│   │   ├── subscription.py   # Subscriptions table
│   │   ├── transaction.py    # Transactions table
│   │   └── audit_log.py      # Audit logs table
│   ├── schemas/
│   │   ├── auth.py           # Request/response schemas
│   │   └── user.py           # User response schema
│   └── services/
│       ├── auth_service.py   # Auth business logic
│       └── email_service.py  # Email utilities
├── alembic/                  # Database migrations
├── .env.example              # Environment template
├── main.py                   # FastAPI entry point
└── pyproject.toml            # Dependencies
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL
- uv

### Setup

```bash
# Clone the repo
git clone https://github.com/mwangisam203/safaridesk.git
cd safaridesk

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Fill in your values in .env

# Run database migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for interactive API documentation.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/v1/auth/register | Register new user | No |
| POST | /api/v1/auth/login | Login, returns JWT | No |
| POST | /api/v1/auth/token | Swagger OAuth2 login | No |
| GET | /api/v1/auth/me | Get current user | Yes |
| POST | /api/v1/auth/logout | Logout | Yes |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Welcome message |
| GET | /health | Health check |

---

## Database Schema

### Users
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String | Unique, indexed |
| phone_number | String | Unique, +254 format |
| hashed_password | String | bcrypt hash |
| full_name | String | Display name |
| subscription_tier | Enum | free / basic / pro |
| is_active | Boolean | Account status |
| is_verified | Boolean | Email verified |
| is_admin | Boolean | Admin flag |
| created_at | DateTime | UTC timestamp |

### Subscriptions
Tracks subscription lifecycle — status, tier, expiry, auto-renewal.

### Transactions
Records every payment attempt with M-Pesa receipt as idempotency key.

### Audit Logs
Append-only log of every significant action — never updated, never deleted.

---

## Sprint Progress

### ✅ Sprint 1 — Auth System (Complete)
- [x] Project structure and folder organization
- [x] PostgreSQL database with 4 tables
- [x] Alembic migrations
- [x] User registration with Kenyan phone validation
- [x] JWT authentication — access + refresh tokens
- [x] Protected routes with dependency injection
- [x] Password hashing with bcrypt
- [x] Email service setup with Mailtrap

### 🔄 Sprint 2 — M-Pesa Payments (Next)
- [ ] M-Pesa Daraja API integration
- [ ] STK Push — prompt user to pay
- [ ] Webhook handler with idempotency
- [ ] Subscription upgrade on confirmed payment
- [ ] Email confirmation via Celery

### 📋 Sprint 3 — Subscription Lifecycle
- [ ] Celery background jobs
- [ ] Subscription expiry automation
- [ ] Renewal reminder emails
- [ ] Africa's Talking SMS notifications

### 📋 Sprint 4 — Refunds and Reporting
- [ ] B2C refund system
- [ ] Payment history dashboard
- [ ] Admin revenue reports
- [ ] PDF receipt generation

### 📋 Sprint 5 — Security and Testing
- [ ] Redis rate limiting
- [ ] Full audit logging
- [ ] Pytest coverage on all payment flows

### 📋 Sprint 6 — Deployment
- [ ] Docker + Docker Compose
- [ ] AWS EC2 + RDS + ElastiCache
- [ ] GitHub Actions CI/CD
- [ ] Custom domain + HTTPS

---

## Key Design Decisions

**Why FastAPI?**
Modern, fast, automatic OpenAPI docs, native async support,
and excellent Pydantic integration for request validation.

**Why JWT with two tokens?**
Access tokens expire in 30 minutes limiting damage from theft.
Refresh tokens allow seamless renewal without re-login.

**Why PostgreSQL ENUM for subscription_tier?**
Database-level enforcement. It's impossible to store an invalid tier.
No application-level bug can corrupt this data.

**Why store phone as +254 format?**
M-Pesa Daraja API requires E.164 international format.
Normalizing at registration means no conversion needed at payment time.

**Why audit_logs is append-only?**
In financial systems, every action must be traceable.
Audit logs are never updated or deleted — they are the source of truth
for disputes, debugging, and compliance.

---

## Environment Variables

See `.env.example` for the full list of required variables.

---

## Author

**Sam Mwangi**
Backend Developer | Python · FastAPI · PostgreSQL · Fintech
Nairobi, Kenya 🇰🇪
GitHub: github.com/mwangisam203
```

#  Expose To Other Devices
uv run uvicorn main:app --reload --host 0.0.0.0

#  Production-ish Run
uv run uvicorn main:app --host 0.0.0.0 --port 8000

## Install/Sync Dependencies
uv sync


##postgres use keys
q       quit
Space   next page
b       previous page
Enter   move down one line
/word   search for word
n       next search result