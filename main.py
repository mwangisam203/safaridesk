from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.observability import configure_logging
from app.api.v1 import auth  # import more routers as you build them
from app.api.v1.payments import router as payments_router
from app.api.v1.content import router as content_router
from app.api.v1.users import router as users_router

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Paid Technical Knowledge Platform for Developers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — controls which domains can call your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers — add more here as you build each feature
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

app.include_router(payments_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
