import httpx

from app.core.config import settings


SANDBOX_SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"
PROD_SMS_URL = "https://api.africastalking.com/version1/messaging"


def _sms_url() -> str:
    return SANDBOX_SMS_URL if settings.AT_USERNAME == "sandbox" else PROD_SMS_URL


def send_sms(to_phone: str, message: str) -> dict:
    payload = {
        "username": settings.AT_USERNAME,
        "to": to_phone,
        "message": message,
    }
    if settings.AT_SENDER_ID:
        payload["from"] = settings.AT_SENDER_ID

    with httpx.Client(timeout=15) as client:
        response = client.post(
            _sms_url(),
            data=payload,
            headers={
                "apiKey": settings.AT_API_KEY,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
