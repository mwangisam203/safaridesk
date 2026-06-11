export const topicFilters = [
  { id: "all", label: "All articles" },
  { id: "api", label: "APIs" },
  { id: "database", label: "Database" },
  { id: "payments", label: "Payments" },
  { id: "devops", label: "DevOps" },
  { id: "testing", label: "Testing" }
];

const topicRules = {
  api: ["fastapi", "rest api", "jwt", "authentication"],
  database: ["postgresql", "alembic", "database", "sqlalchemy"],
  payments: ["m-pesa", "daraja", "payment"],
  devops: ["docker", "linux", "deploying", "celery", "redis", "virtual environment"],
  testing: ["test", "pytest", "git", "github"]
};

const articleCovers = {
  "deploying-fastapi-to-linux-vps": "/covers/deploying-fastapi-linux-vps.webp",
  "linux-command-line-for-developers": "/covers/linux-command-line.webp",
  "writing-tests-fastapi-pytest": "/covers/fastapi-pytest.webp",
  "python-virtual-environments-dependency-management": "/covers/python-environments.webp",
  "git-github-for-backend-developers": "/covers/git-collaboration.webp",
  "alembic-database-migrations-in-practice": "/covers/alembic-migrations.webp",
  "mpesa-daraja-api-integration-guide": "/covers/mpesa-daraja.webp",
  "celery-redis-background-tasks-explained": "/covers/celery-redis.webp",
  "introduction-to-docker-for-developers": "/covers/docker-introduction.webp",
  "understanding-jwt-authentication": "/covers/jwt-authentication.webp",
  "postgresql-for-backend-developers": "/covers/postgresql-backend.webp",
  "how-to-build-rest-api-fastapi": "/covers/rest-api-fastapi.webp",
  "how-to-build-a-fastapi-backend": "/covers/fastapi-backend.webp"
};

export function matchesTopic(article, topic) {
  if (topic === "all") return true;
  const text = `${article.title} ${article.summary || ""}`.toLowerCase();
  return topicRules[topic]?.some((keyword) => text.includes(keyword));
}

export function coverFor(article) {
  return article.cover_image_url || articleCovers[article.slug] || "/covers/backend-architecture.png";
}

export function readTime(article) {
  const words = `${article.summary || ""} ${article.body || ""}`.trim().split(/\s+/).length;
  return Math.max(4, Math.ceil(words / 210));
}

export function formatDate(value) {
  if (!value) return "Recently";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric"
  }).format(new Date(value));
}
