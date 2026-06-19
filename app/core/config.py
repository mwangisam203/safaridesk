from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # App
    APP_NAME: str = "SafariDesk"
    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 1
    AUTH_EMAIL_DELIVERY_MODE: str = "direct"  # direct or celery
    RATE_LIMIT_ENABLED: bool = True

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # M-Pesa
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_BUSINESS_SHORT_CODE: str = "174379"
    MPESA_PASSKEY: str = ""
    MPESA_CALLBACK_URL: str = ""
    MPESA_ENVIRONMENT: str = "sandbox"

    # Africa's Talking
    AT_USERNAME: str = "sandbox"
    AT_API_KEY: str = ""
    AT_SENDER_ID: str = ""

    # Mail
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@safaridesk.com"
    MAIL_SERVER: str = "smtp.mailtrap.io"
    MAIL_PORT: int = 587

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    S3_BUCKET_NAME: str = ""
    S3_PUBLIC_BASE_URL: str = ""
    IMAGE_STORAGE_BACKEND: str = "local"
    IMAGE_UPLOAD_DIR: str = "frontend/public/uploads"
    IMAGE_UPLOAD_MAX_MB: int = 8
    IMAGE_MAX_WIDTH: int = 2000
    IMAGE_MAX_HEIGHT: int = 1250

# Single instance used everywhere in the app
settings = Settings()
