from app.models.article import ArticleTier


ARTICLES = [
    {
        "title": "How to Build a FastAPI Backend",
        "slug": "how-to-build-a-fastapi-backend",
        "summary": (
            "Design a maintainable FastAPI backend by separating HTTP concerns, "
            "business rules, persistence, configuration, and background work."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """A useful backend is more than a collection of routes. It is a system that accepts untrusted input, applies business rules, changes durable state, and produces a predictable response. FastAPI makes the HTTP layer pleasant, but the long-term quality of the application depends on the boundaries you build around it.

## Start with responsibilities

Keep route functions focused on HTTP concerns: validation, authentication, status codes, and response models. Put business decisions in services, database structure in models, and input/output contracts in schemas. This separation makes payment rules, subscription expiry, and content access testable without starting a web server.

A practical layout is app/api for routes, app/schemas for contracts, app/models for persistence, app/services for business logic, and app/tasks for work that can happen later. These folders are not decoration. They communicate where a change belongs and prevent one large file from becoming the entire application.

## Follow one request end to end

When a request reaches an endpoint, validate it with a Pydantic schema, resolve the current user, call a service, commit the transaction, and return a response schema. Avoid returning raw database objects when the public contract should expose fewer fields.

```
@router.post("/subscriptions")
def subscribe(body: SubscriptionCreate, db: Session = Depends(get_db)):
    subscription = activate_subscription(db, body)
    db.commit()
    return subscription
```

The service should own rules such as extending remaining time, upgrading a tier, or rejecting a duplicate payment. The route should not need to know every branch.

## Build for failure

Database writes can fail, external APIs can time out, and background workers can retry. Use transactions around related changes, unique constraints for idempotency, explicit timeouts for network calls, and structured logs with stable identifiers. Never treat an external request as proof that money moved; wait for the provider callback or reconciliation result.

## Production checklist

Before deployment, use environment-based configuration, run migrations separately from application startup, expose health checks, restrict CORS, and place the app behind a reverse proxy. Add tests at three levels: service tests for rules, API tests for contracts, and a small number of integration tests against real infrastructure.

The strongest backend is not the one with the most abstractions. It is the one where a new feature has an obvious home and a failed operation leaves the system in a state you can understand and recover.""",
    },
    {
        "title": "How to Build a REST API with FastAPI",
        "slug": "how-to-build-rest-api-fastapi",
        "summary": (
            "Build predictable REST endpoints with clear resource models, validation, "
            "status codes, pagination, authentication, and stable error contracts."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """REST is less about matching a URL pattern and more about giving clients a predictable contract. A well-designed API makes resources easy to identify, operations easy to understand, and failures easy to handle.

## Model resources before routes

Start with the nouns in the domain: users, articles, subscriptions, and transactions. Use collection URLs such as /articles and item URLs such as /articles/{slug}. HTTP methods then describe the operation: GET reads, POST creates, PATCH changes part of a resource, and DELETE removes it.

Avoid action-heavy paths when the action can be represented as a resource change. A payment initiation may still need a command-like endpoint because it starts an external workflow, but its resulting transaction should have a resource clients can query.

## Make contracts explicit

Use separate Pydantic models for create, update, list, and detail responses. A registration request accepts a password, but a user response must never return a password hash. A list response may omit a large article body to save bandwidth.

Choose status codes deliberately: 201 for creation, 204 for a successful response with no body, 400 for invalid business input, 401 when authentication is missing or invalid, 403 when identity is known but access is denied, and 404 when the resource does not exist.

## Design for collections

Collections grow. Add pagination before returning thousands of rows becomes a crisis. Define stable sorting, cap page size, and include enough metadata for the client to request the next page. Search should normalize input and use database indexes appropriate to the query pattern.

## Treat errors as part of the API

Clients need a stable error shape, not a different string from every endpoint. Include a machine-readable code, a human message, and optional field details. Do not leak stack traces, SQL fragments, provider secrets, or internal exception names.

## Protect and evolve the contract

Authenticate with short-lived access tokens, enforce authorization at the resource boundary, and rate-limit sensitive operations such as login and payment initiation. Keep OpenAPI documentation accurate because it becomes the shared language between backend, frontend, tests, and future integrations.

Version only when you need to break clients. Additive fields are usually safe, while renaming fields or changing meaning is not. A dependable API grows through explicit contracts and careful compatibility, not clever route names.""",
    },
    {
        "title": "PostgreSQL for Backend Developers",
        "slug": "postgresql-for-backend-developers",
        "summary": (
            "Use PostgreSQL confidently through sound schemas, constraints, indexes, "
            "transactions, query analysis, and operational habits."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """PostgreSQL is not merely a place to put application objects. It is the system responsible for preserving truth when requests overlap, workers retry, and application code contains bugs. Good backend design uses the database as an active safety boundary.

## Encode rules in the schema

Choose types that reflect the domain. Use timestamps with time zones for real moments, numeric types for exact monetary values, and foreign keys for relationships. Add NOT NULL, UNIQUE, and CHECK constraints for rules that must remain true regardless of which code path writes the row.

For example, a provider receipt number should be unique. That constraint is stronger than an application query followed by an insert because two concurrent requests can both pass the query.

## Understand transactions

A transaction groups related changes into one atomic decision. When confirming a payment, updating the transaction and activating the subscription should commit together. If one step fails, roll back both.

Keep transactions short. Do not hold one open while waiting for an SMS or payment provider. Commit durable state first, then enqueue notification work.

## Index for real queries

Indexes speed reads but add storage and write cost. Index foreign keys used in joins, columns used for frequent filtering, and stable ordering keys. A composite index should follow the query pattern; an index on status and created_at can support a reconciler that repeatedly finds old pending transactions.

Use EXPLAIN ANALYZE when performance matters. It shows whether PostgreSQL scans the whole table, uses an index, or badly estimates row counts. Guessing from the SQL text is not enough.

## Operate the database

Use Alembic migrations for every schema change and test both upgrade and rollback paths where practical. Backups are only useful if restoration has been rehearsed. Monitor connection count, slow queries, storage growth, locks, and failed transactions.

Application sessions should be short-lived and always closed. In production, use a connection pool sized for the database rather than the number of web requests you hope to serve.

PostgreSQL rewards explicit design. Constraints protect correctness, transactions protect multi-step changes, indexes protect latency, and operational discipline protects recovery.""",
    },
    {
        "title": "Understanding JWT Authentication",
        "slug": "understanding-jwt-authentication",
        "summary": (
            "Understand what JWTs prove, what they do not prove, and how to implement "
            "short-lived access tokens and controlled refresh sessions safely."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """A JSON Web Token is a signed claim, not an encrypted session and not permanent proof that a user should still have access. Understanding that distinction prevents many authentication mistakes.

## What a token contains

A JWT has a header, payload, and signature. The payload may contain a subject identifier, expiry time, token type, and limited authorization claims. Anyone holding the token can usually decode the payload, so never place passwords, secrets, or sensitive personal data inside it.

The signature allows the server to detect modification. It does not hide the contents. The server must also validate the expected algorithm, expiry, issuer or audience when used, and token type.

## Access and refresh tokens

Access tokens should be short-lived and sent with API requests. Refresh tokens live longer and are used only to obtain a new access token. Keeping the roles separate limits exposure: stealing a short-lived access token gives an attacker less time, while refresh usage can be monitored and revoked.

```
claims = {
    "sub": str(user.id),
    "type": "access",
    "exp": expires_at,
}
```

Do not accept a refresh token where an access token is expected. Validate the type claim in addition to the signature.

## Storage and revocation

For browser applications, secure HttpOnly cookies reduce exposure to JavaScript, but they require CSRF protection. In-memory access tokens avoid persistent browser storage but disappear on refresh. There is no universal storage choice; decide from the threat model.

Stateless tokens are difficult to revoke immediately. Common strategies include short access-token expiry, server-side refresh-session records, token rotation, and a revoked-session version stored for the user. Password changes and account suspension should invalidate refresh sessions.

## Operational safety

Use a strong secret or asymmetric keys, rotate keys deliberately, and keep clock skew small. Rate-limit login and refresh endpoints. Return generic login failures so attackers cannot enumerate accounts, and log security events without logging raw tokens.

JWT is useful when multiple clients or services need a portable signed identity claim. It is not automatically safer than a server session. Security comes from expiry, validation, storage, revocation, and careful authorization after identity is established.""",
    },
    {
        "title": "Introduction to Docker for Developers",
        "slug": "introduction-to-docker-for-developers",
        "summary": (
            "Learn how images, containers, volumes, networks, and Compose create "
            "repeatable development and deployment environments."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """Docker packages an application and its operating-system dependencies into a repeatable image. The same image can run on a laptop, in CI, and on a server, reducing the gap between “works on my machine” and production.

## Images and containers

An image is an immutable template assembled from Dockerfile layers. A container is a running instance of that image with a writable temporary layer. Rebuilding an image should be normal; manually changing a running container should not be part of deployment.

Order Dockerfile steps to use caching well. Copy dependency files and install packages before copying frequently changing source code. Use a small base image, pin important versions, and run as a non-root user.

```
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

## State belongs outside containers

Containers are disposable. Store PostgreSQL data in a named volume and uploaded assets in durable object storage or a mounted volume. Configuration and secrets should enter through environment variables or a secret manager, not be baked into the image.

## Networks and Compose

Docker Compose defines a local system: API, PostgreSQL, Redis, Celery worker, and scheduler. Services reach each other by service name on the Compose network. Inside the API container, localhost means that same container, not the database container.

Add health checks and dependency retry logic. Startup order does not guarantee that PostgreSQL is ready to accept connections.

## Production considerations

Build once and promote the same image between environments. Scan dependencies, keep images updated, limit container privileges, set memory and CPU boundaries, and send logs to standard output. Run database migrations as an explicit release step.

Docker improves repeatability, but it does not replace architecture or operations. A containerized application can still have unsafe secrets, missing backups, poor observability, and incorrect retry behavior. Use containers to make the system reproducible, then engineer the system itself.""",
    },
    {
        "title": "Celery and Redis: Background Tasks Explained",
        "slug": "celery-redis-background-tasks-explained",
        "summary": (
            "Move slow and retryable work out of HTTP requests while keeping Celery "
            "tasks idempotent, observable, and safe under duplicate delivery."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """Background processing keeps web requests fast when work can happen after the response. Sending email, delivering SMS, reconciling payments, and expiring subscriptions are good candidates because they involve network waiting or scheduled execution.

## The moving parts

The API publishes a task message to a broker such as Redis. A Celery worker consumes the message and executes the task. Celery Beat publishes scheduled tasks at configured times; it does not execute them itself, so both Beat and at least one worker must run.

The API should store the important state before publishing a task. For a payment confirmation, commit the confirmed transaction and active subscription, then enqueue the message. Notification failure should not undo a valid payment.

## Design for duplicate execution

Task delivery is generally at least once. A worker may complete the work and crash before acknowledging the message, causing it to run again. Every task must therefore be idempotent or protected by a durable uniqueness rule.

Use a notification log keyed by event and channel, or let the service recognize that the desired state already exists. Never extend a subscription twice merely because a callback or task was retried.

## Retries need policy

Retry transient failures such as timeouts and provider 5xx responses with exponential backoff and jitter. Do not retry permanent failures forever, such as an invalid phone number. Set network timeouts so a worker cannot hang indefinitely.

```
@celery.task(bind=True, autoretry_for=(TimeoutError,),
             retry_backoff=True, retry_jitter=True, max_retries=5)
def send_receipt(self, transaction_id: int):
    ...
```

Pass stable identifiers into tasks rather than large serialized objects. Load fresh database state when the task runs because the message may wait in the queue.

## Observe the queue

Monitor queue depth, oldest-task age, success and failure rates, retry count, and task duration. Route urgent user notifications separately from slow bulk work if one workload could block another.

Celery is not simply “run this later.” It is a distributed system where messages can be delayed, duplicated, or fail. Reliable task design starts by accepting those facts and making each operation recoverable.""",
    },
    {
        "title": "M-Pesa Daraja API Integration Guide",
        "slug": "mpesa-daraja-api-integration-guide",
        "summary": (
            "Implement STK Push as an asynchronous, idempotent payment workflow with "
            "secure callbacks, reconciliation, and subscription activation."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """M-Pesa STK Push is an asynchronous payment workflow. The initial API response means Safaricom accepted the request for processing; it does not mean the customer paid. Your system must wait for a successful callback or later reconciliation before granting paid access.

## Initiate the request

Normalize Kenyan phone numbers to the international form expected by Daraja. Create a local pending transaction before calling the provider, then store the returned CheckoutRequestID and MerchantRequestID. These identifiers connect the callback to your transaction.

Use the current timestamp and passkey to generate the request password. Keep consumer credentials and the passkey in environment variables, and use separate sandbox and production configuration.

## Handle callbacks defensively

The callback endpoint is public and can receive duplicates, delayed messages, malformed payloads, or identifiers you do not recognize. Parse it safely, find the matching transaction, and process the result inside a database transaction.

For a success result, record the receipt, amount, phone number, and provider timestamp. Verify that the paid amount and intended plan match what you initiated. Protect the provider receipt with a unique constraint and make repeated callbacks return successfully without applying benefits twice.

## Activate access only after confirmation

Once payment is durably confirmed, activate the chosen tier. A renewal of the same tier should extend from the current expiry when time remains. An upgrade needs an explicit product rule: switch immediately, prorate value, or start the new plan after the existing period. Record the decision so customer support can explain it.

Send SMS and email receipts as background tasks after the database commit. Notifications are consequences of payment, not part of the payment transaction itself.

## Reconcile missing outcomes

Callbacks can be lost. A scheduled reconciler should query old pending transactions, ask Daraja for their status, and feed the result through the same idempotent confirmation service used by callbacks. Mark transactions for manual review after a sensible retry window rather than leaving them pending forever.

Before going live, use HTTPS callbacks, verify production credentials and shortcode ownership, restrict sensitive logs, test cancellation and insufficient-funds paths, and monitor callback latency and unmatched identifiers. Payment reliability comes from the complete lifecycle, not merely receiving a successful STK prompt.""",
    },
    {
        "title": "Alembic Database Migrations in Practice",
        "slug": "alembic-database-migrations-in-practice",
        "summary": (
            "Evolve SQLAlchemy schemas safely with reviewed migrations, staged data "
            "changes, backward-compatible releases, and tested recovery paths."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """A model change in Python does not change an existing database. Alembic records the ordered schema operations required to move each environment from one known revision to the next.

## Generate, then review

Autogenerate compares SQLAlchemy metadata with the database and creates a candidate migration. It cannot understand your intent. Always inspect the generated upgrade and downgrade functions for incorrect type changes, missing constraints, unsafe defaults, or accidental table removal.

```
uv run alembic revision --autogenerate -m "add payment receipt index"
uv run alembic upgrade head
uv run alembic current
```

Run migrations against a disposable database before applying them to shared environments.

## Separate schema and data risk

Adding a nullable column is usually safe. Adding a required column to a large populated table may lock it or fail because old rows have no value. A safer sequence is to add the column as nullable, deploy code that writes it, backfill existing rows in controlled batches, and finally add the NOT NULL constraint.

Renaming or removing columns needs backward compatibility when old and new application versions may run together. Use an expand-and-contract release: add the new structure, migrate readers and writers, then remove the old structure in a later release.

## Make deployments predictable

Run migrations once as a release step, not independently in every web worker. Back up critical data, understand lock behavior, and monitor long-running migrations. For large indexes, use PostgreSQL features such as concurrent index creation where appropriate, noting that some operations cannot run inside Alembic’s normal transaction.

Downgrade scripts are valuable but not always sufficient. Reversing a dropped column cannot recover its data. For destructive changes, restoration may require a backup and a roll-forward fix.

## Keep history trustworthy

Commit migration files with the model change that requires them. Never rewrite a migration that has already reached another environment; create a new corrective revision. Resolve branch heads explicitly when parallel work creates multiple revisions.

Migrations are production code. Review them for correctness, performance, compatibility, and recovery just as carefully as an API endpoint.""",
    },
    {
        "title": "Git and GitHub for Backend Developers",
        "slug": "git-github-for-backend-developers",
        "summary": (
            "Use focused commits, short-lived branches, reviewable pull requests, and "
            "protected CI workflows to collaborate without losing context."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """Git records snapshots of a project and the relationships between them. Good Git practice is not about memorizing commands; it is about creating a history that helps teammates review, debug, and recover changes.

## Make commits tell the story

A commit should represent one coherent reason for change. Separate a schema migration, business-rule update, test coverage, and documentation when they can stand independently. This makes review clearer and allows a problematic change to be reverted without discarding unrelated work.

Write imperative messages that describe the outcome: “Add idempotent callback handling” is more useful than “payment changes.” Before committing, inspect both git status and git diff --staged so generated files, secrets, and debugging output do not slip in.

## Keep branches short-lived

Create a branch for a focused change and update it regularly from the shared base branch. Long-lived branches accumulate conflicts and hide integration problems. Rebase can create a clean local story, but never rewrite public history other people may already depend on.

## Build reviewable pull requests

A strong pull request explains the problem, the chosen behavior, important tradeoffs, and how it was verified. Keep the diff narrow enough for a reviewer to understand. Link migrations, configuration changes, operational steps, and screenshots when they affect deployment or user experience.

Automated checks should run formatting, tests, and security or dependency scans. Protect the main branch, require review for risky areas, and prevent merges when checks fail.

## Recover with confidence

Use git log and git show to understand history, git bisect to locate a regression, and git revert to undo a published commit safely. Avoid force-pushing shared branches and avoid destructive reset commands when uncommitted work may exist.

Never commit .env files, API keys, database passwords, private certificates, or production data. Removing a secret from the latest commit does not remove it from history; rotate the credential immediately.

Git works best when history is treated as communication. Small coherent commits and clear pull requests preserve the reasoning future maintainers will otherwise have to rediscover.""",
    },
    {
        "title": "Python Virtual Environments and Dependency Management",
        "slug": "python-virtual-environments-dependency-management",
        "summary": (
            "Keep Python projects reproducible by isolating environments, declaring "
            "dependencies, locking resolved versions, and separating runtime from tools."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """Python projects share an interpreter but should not share an uncontrolled package directory. A virtual environment isolates installed packages so one project can upgrade FastAPI without breaking another.

## Isolation and declaration are different

A virtual environment answers “where are packages installed?” A project file such as pyproject.toml answers “what does this application depend on?” A lock file answers “which exact versions were resolved together?”

All three matter. An isolated environment without declared dependencies cannot be reproduced, while a dependency list without isolation can still conflict with global packages.

## Use uv as the project workflow

With uv, create or synchronize the environment from project metadata rather than installing packages by hand.

```
uv sync
uv add httpx
uv add --dev pytest
uv run pytest
```

Commit pyproject.toml and uv.lock. Do not commit the virtual environment directory. In CI and production, use the locked resolution so deployments do not unexpectedly select a newer transitive package.

## Separate runtime and development tools

The application needs FastAPI, SQLAlchemy, and the database driver at runtime. Test runners, linters, and type checkers belong in a development group. This keeps production images smaller and reduces the software exposed to vulnerabilities.

Use version ranges intentionally. Very loose ranges increase surprise; exact pins in project metadata make routine upgrades cumbersome. A lock file provides exact reproducibility while the declared range communicates compatibility.

## Upgrade deliberately

Read release notes for core frameworks, update a focused group of packages, run the full test suite, and inspect deprecation warnings. Security updates may require faster action, but they still deserve verification.

Keep Python itself consistent across local development, CI, and production. Native packages can depend on system libraries and CPU architecture, so validate the final deployment image rather than assuming a local wheel proves production compatibility.

Dependency management is supply-chain management. Reproducible locks, reviewed upgrades, vulnerability scanning, and minimal production environments turn package installation from an informal habit into an engineering process.""",
    },
    {
        "title": "Writing Tests for FastAPI with Pytest",
        "slug": "writing-tests-fastapi-pytest",
        "summary": (
            "Test FastAPI contracts and business rules with focused fixtures, dependency "
            "overrides, realistic edge cases, and controlled external services."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """Tests are most valuable when they protect behavior you care about, not when they simply execute lines of code. For a FastAPI system, test business rules directly and use API tests to confirm that HTTP contracts expose those rules correctly.

## Build a layered test suite

Service tests are fast and precise. They can verify subscription extension, grace periods, upgrade decisions, and idempotent payment confirmation without routing or serialization. API tests then verify authentication, validation, status codes, and response shapes.

Keep a smaller set of integration tests for PostgreSQL, Redis, and provider adapters. Mocking everything can hide transaction, constraint, and serialization problems.

## Override dependencies

FastAPI dependency overrides let tests provide a controlled database session or authenticated user. Clear overrides after each test so state cannot leak into another case.

```
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
response = client.get("/api/v1/content/articles")
assert response.status_code == 200
```

Prefer fixtures that create the minimum state a test needs. A giant shared fixture makes failures difficult to understand and encourages tests to depend on execution order.

## Test boundaries and failures

For content gating, cover anonymous limits, registered free access, active BASIC and PRO subscriptions, expiry, grace periods, and downgrade behavior. For payments, cover duplicate callbacks, wrong amounts, missing identifiers, provider timeouts, and reconciliation of pending transactions.

Freeze or inject time for expiry tests. Assertions against the real current clock become flaky around day boundaries.

Mock external HTTP, email, and SMS at the adapter boundary. Assert what your code sends and how it reacts, while leaving provider behavior to contract or sandbox tests. Celery tasks can be called synchronously in unit tests, with separate checks that the application enqueues the correct task.

## Keep tests trustworthy

Tests should be deterministic, independent, and readable as examples of intended behavior. Avoid excessive implementation-detail assertions that break during harmless refactoring. When a production bug appears, first reproduce it with a failing test, then fix it.

Coverage can reveal untested areas, but a high percentage does not prove meaningful scenarios were tested. Prioritize money movement, authorization, data loss, retries, and time-based state because failures there carry the highest cost.""",
    },
    {
        "title": "Linux Command Line for Developers",
        "slug": "linux-command-line-for-developers",
        "summary": (
            "Navigate, inspect, combine, and troubleshoot Linux systems using commands "
            "that support real backend development and production diagnosis."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """The Linux command line is a composable toolkit. Small programs read text, transform it, and pass results to the next program. Learning that model is more useful than memorizing a long list of commands.

## Navigate and inspect safely

Use pwd to confirm location, ls -la to include hidden files, and find or rg --files to locate files. Read text with less, inspect recent log lines with tail, and use head when only the start matters.

Before changing files, verify the target. Commands such as rm, chmod, and recursive copy can have a wide blast radius. Prefer explicit paths and inspect with ls or stat first.

## Search and compose

Ripgrep searches source trees quickly while respecting ignore files. Pipes connect standard output from one command to standard input of another.

```
rg -n "ERROR|Timeout" app tests
journalctl -u safaridesk --since "30 minutes ago" | tail -n 100
ps aux | rg "uvicorn|celery"
```

Redirect output with care: > replaces a file and >> appends. Use tee when you need to see output and store it.

## Understand processes and ports

Use ps to inspect processes, top or htop for resource use, ss to see listening sockets, and systemctl or journalctl for managed services. A running process is not necessarily a healthy service; confirm its port and call a health endpoint.

Signals let processes shut down or reload. Start with normal termination rather than force-killing, so workers can finish tasks and release resources.

## Permissions and ownership

Linux separates user, group, and other permissions. Avoid solving permission problems with chmod 777. Determine which process user needs access, set appropriate ownership, and grant the smallest required permission.

## Remote diagnosis

Use ssh keys instead of passwords, copy files with scp or rsync, and inspect disk space with df and directory size with du. Check memory, load, logs, DNS resolution, and connectivity before assuming application code is at fault.

The shell becomes powerful when commands are small, observable steps. Inspect first, make one change, verify the result, and preserve command history as part of your debugging evidence.""",
    },
    {
        "title": "Deploying FastAPI to a Linux VPS",
        "slug": "deploying-fastapi-to-linux-vps",
        "summary": (
            "Deploy FastAPI behind a reverse proxy with managed processes, HTTPS, "
            "migrations, workers, observability, backups, and a repeatable release path."
        ),
        "tier": ArticleTier.BASIC,
        "author": "Sam",
        "body": """A production deployment is a chain of responsibilities: DNS sends traffic to the server, a reverse proxy terminates HTTPS, an application server runs FastAPI, PostgreSQL stores state, Redis carries background work, and system services keep processes alive.

## Prepare the server

Create a non-root deployment user, install security updates, configure a firewall, and allow only SSH, HTTP, and HTTPS from the public internet. Use SSH keys, disable unnecessary password login, and keep database and Redis ports private.

Place configuration in protected environment files or a secret manager. Never clone production secrets from source control.

## Run FastAPI as a managed service

Uvicorn should bind to a private interface or Unix socket behind Nginx or Caddy. Use systemd, Docker Compose, or another supervisor to restart the process after failure and start it after reboot.

Run Celery workers and Celery Beat as separate managed processes. The API does not execute queued SMS, email, reconciliation, or expiry tasks by itself.

## Put a reverse proxy in front

The proxy serves HTTPS, forwards requests, sets forwarding headers, applies body-size limits, and can serve static assets efficiently. Obtain and automatically renew a TLS certificate. Configure the application to trust forwarded headers only from the proxy.

## Release in controlled steps

Build or install dependencies from a lock file, run tests, back up critical data, apply Alembic migrations once, restart services, and call the health endpoint. For incompatible schema changes, use an expand-and-contract migration so old and new application versions can overlap safely.

Keep a rollback plan. Application rollback is straightforward only when the database remains compatible.

## Observe and recover

Centralize logs for the API, proxy, workers, and scheduler. Monitor HTTP errors, latency, CPU, memory, disk, database connections, queue age, and failed tasks. Alert on symptoms users feel rather than merely on process existence.

Automate PostgreSQL backups and practice restoring them. Store backups away from the VPS. Document how to rotate credentials, renew certificates, restart each service, and recover a failed deployment.

A VPS can run a serious application when the release process is repeatable and failure is expected. Production readiness comes from controlled change, visibility, and recovery, not from getting the first successful response over the public internet.""",
    },
]


ARTICLES_BY_SLUG = {article["slug"]: article for article in ARTICLES}
