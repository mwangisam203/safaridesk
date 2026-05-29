# SafariDesk 🦁

> Paid Technical Knowledge Platform for African Developers

A subscription-based platform where developers access premium 
technical content via M-Pesa payments.

## Stack
- **Backend:** FastAPI + Python
- **Database:** PostgreSQL + Alembic
- **Cache/Queue:** Redis + Celery
- **Payments:** M-Pesa Daraja API
- **SMS:** Africa's Talking
- **Deployment:** Docker + AWS

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis
- uv (package manager)

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

# Run migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn main:app --reload
```

Visit http://localhost:8000/docs for the API documentation.

