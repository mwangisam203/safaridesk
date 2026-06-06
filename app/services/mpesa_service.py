import base64
import httpx
from datetime import datetime
from app.core.config import settings

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PROD_BASE = "https://api.safaricom.co.ke"


class MpesaService:

    @property
    def base_url(self):
        return SANDBOX_BASE if settings.MPESA_ENVIRONMENT == "sandbox" else PROD_BASE

    async def get_access_token(self) -> str:
        credentials = base64.b64encode(
            f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
        ).decode()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {credentials}"},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()["access_token"]

    def _generate_password(self, timestamp: str) -> str:
        raw = f"{settings.MPESA_BUSINESS_SHORT_CODE}{settings.MPESA_PASSKEY}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    async def initiate_stk_push(
        self, phone: str, amount: int, account_ref: str, description: str
    ) -> dict:
        token = await self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)

        # M-Pesa expects 2547XXXXXXXX — strip leading + if present
        phone_normalized = phone.lstrip("+")

        payload = {
            "BusinessShortCode": settings.MPESA_BUSINESS_SHORT_CODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_normalized,
            "PartyB": settings.MPESA_BUSINESS_SHORT_CODE,
            "PhoneNumber": phone_normalized,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": account_ref,  # e.g. "SAFARIDESK-SUB"
            "TransactionDesc": description,
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
            # Returns: { "MerchantRequestID", "CheckoutRequestID",
            #            "ResponseCode", "ResponseDescription",
            #            "CustomerMessage" }

    async def query_stk_status(self, checkout_request_id: str) -> dict:
        """
        Query Daraja for the real status of an STK push.
        Called by the reconciler for stuck PENDING transactions.
        Returns Daraja's response dict with ResultCode.
        """
        token = await self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)

        payload = {
            "BusinessShortCode": settings.MPESA_BUSINESS_SHORT_CODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
            # Returns: { "ResultCode", "ResultDesc", "ResponseCode" ... }
