"""Google OAuth2 routes for connecting user's Google Drive"""
import uuid
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow

from api.config import settings
from api.database import (
    get_user, create_user, update_user,
    save_user_credentials, save_oauth_state, get_oauth_state
)
from integrations.whatsapp.sender import WhatsAppSender

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.appdata",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def create_flow(redirect_uri: str = None) -> Flow:
    """Create Google OAuth flow"""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri or settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri or settings.google_redirect_uri,
    )
    return flow


@router.get("/google/initiate/{phone}")
async def initiate_google_auth(phone: str):
    """Generate Google OAuth URL for a user's phone number"""
    try:
        state = str(uuid.uuid4())
        await save_oauth_state(state, phone)
        flow = create_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Error initiating auth for {phone}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate auth")


@router.get("/google/callback")
async def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback"""
    if error:
        return HTMLResponse(
            content=f"<html><body><h2>Authorization failed: {error}</h2>"
                    "<p>Please try again by messaging ExpenseWise on WhatsApp.</p></body></html>"
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    phone = await get_oauth_state(state)
    if not phone:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    try:
        flow = create_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        await save_user_credentials(phone, {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "provider": "google_drive",
        })
        user = await get_user(phone)
        if user:
            await update_user(phone, {"storage_provider": "google_drive", "is_onboarded": True})
        else:
            await create_user(phone, {"storage_provider": "google_drive", "is_onboarded": True})
        sender = WhatsAppSender()
        await sender.send_message(
            phone,
            "Your Google Drive is now connected! ExpenseWise will save your expenses there.\n\n"
            "You're all set! Try:\n"
            "- 'Spent $50 on groceries'\n"
            "- 'Show this month's expenses'\n"
            "- 'Set $500 food budget'"
        )
        return HTMLResponse(
            content="<html><body>"
                    "<h2>Google Drive Connected!</h2>"
                    "<p>Your account is ready. Go back to WhatsApp to start tracking expenses.</p>"
                    "<p>You can close this window.</p>"
                    "</body></html>"
        )
    except Exception as e:
        logger.error(f"Error in OAuth callback for {phone}: {e}")
        return HTMLResponse(
            content="<html><body>"
                    "<h2>Connection Failed</h2>"
                    "<p>Something went wrong. Please try again.</p>"
                    "</body></html>",
            status_code=500
        )


@router.get("/status/{phone}")
async def auth_status(phone: str):
    """Check if user has connected their Google Drive"""
    user = await get_user(phone)
    if not user:
        return {"connected": False, "is_onboarded": False}
    return {
        "connected": user.get("storage_provider") is not None,
        "storage_provider": user.get("storage_provider"),
        "is_onboarded": user.get("is_onboarded", False),
    }


@router.delete("/disconnect/{phone}")
async def disconnect_storage(phone: str):
    """Disconnect user's cloud storage"""
    await update_user(phone, {"storage_provider": None, "is_onboarded": False})
    return {"message": "Storage disconnected successfully"}
