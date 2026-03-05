"""Google Drive client for user-owned expense storage"""
import json
import io
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from api.config import settings
from api.models.expense import Expense

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.appdata",
]

EXPENSEWISE_FOLDER = "ExpenseWise"
EXPENSES_FOLDER = "Expenses"
BUDGETS_FILE = "budgets.json"
USER_PROFILE_FILE = "profile.json"


class GoogleDriveClient:
    """Client for interacting with user's Google Drive to store expense data"""

    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("drive", "v3", credentials=credentials)
        self._folder_id: Optional[str] = None
        self._expenses_folder_id: Optional[str] = None

    @classmethod
    async def for_user(cls, user_phone: str) -> Optional["GoogleDriveClient"]:
        """Load credentials for user from database and return client"""
        from api.database import get_user_credentials
        creds_data = await get_user_credentials(user_phone)
        if not creds_data:
            return None
        credentials = Credentials(
            token=creds_data.get("access_token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
        )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            from api.database import update_user_credentials
            await update_user_credentials(user_phone, {
                "access_token": credentials.token,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            })
        return cls(credentials)

    async def _get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Get or create a folder in Google Drive"""
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = self.service.files().list(
            q=query, spaces="drive", fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]
        folder = self.service.files().create(body=file_metadata, fields="id").execute()
        return folder["id"]

    async def _ensure_folders(self):
        """Ensure ExpenseWise folder structure exists"""
        if not self._folder_id:
            self._folder_id = await self._get_or_create_folder(EXPENSEWISE_FOLDER)
        if not self._expenses_folder_id:
            self._expenses_folder_id = await self._get_or_create_folder(
                EXPENSES_FOLDER, self._folder_id
            )

    async def save_expense(self, expense: Expense) -> bool:
        """Save expense to user's Google Drive as JSON"""
        try:
            await self._ensure_folders()
            month_folder_name = expense.date.strftime("%Y-%m")
            month_folder_id = await self._get_or_create_folder(
                month_folder_name, self._expenses_folder_id
            )
            expense_data = expense.model_dump()
            expense_data["date"] = expense.date.isoformat()
            expense_data["created_at"] = expense.created_at.isoformat() if expense.created_at else None
            file_name = f"{expense.id}.json"
            content = json.dumps(expense_data, indent=2, default=str)
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="application/json",
                resumable=False,
            )
            existing = self.service.files().list(
                q=f"name='{file_name}' and '{month_folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute().get("files", [])
            if existing:
                self.service.files().update(
                    fileId=existing[0]["id"], media_body=media
                ).execute()
            else:
                self.service.files().create(
                    body={"name": file_name, "parents": [month_folder_id]},
                    media_body=media,
                    fields="id"
                ).execute()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error saving expense to Drive: {e}")
            return False

    async def get_expenses(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Load expenses from Google Drive for a date range"""
        try:
            await self._ensure_folders()
            expenses = []
            current = start_date.replace(day=1)
            while current <= end_date:
                month_name = current.strftime("%Y-%m")
                results = self.service.files().list(
                    q=f"name='{month_name}' and '{self._expenses_folder_id}' in parents and trashed=false",
                    fields="files(id)"
                ).execute().get("files", [])
                if results:
                    month_folder_id = results[0]["id"]
                    files = self.service.files().list(
                        q=f"'{month_folder_id}' in parents and trashed=false",
                        fields="files(id, name)"
                    ).execute().get("files", [])
                    for f in files:
                        content = self._download_file(f["id"])
                        if content:
                            exp = json.loads(content)
                            exp_date = date.fromisoformat(exp["date"])
                            if start_date <= exp_date <= end_date:
                                expenses.append(exp)
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            return expenses
        except Exception as e:
            import logging
            logging.error(f"Error loading expenses from Drive: {e}")
            return []

    def _download_file(self, file_id: str) -> Optional[str]:
        """Download file content from Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue().decode("utf-8")
        except Exception:
            return None

    async def save_budgets(self, budgets: List[Dict[str, Any]]) -> bool:
        """Save budget configuration to Google Drive"""
        try:
            await self._ensure_folders()
            content = json.dumps(budgets, indent=2, default=str)
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="application/json",
                resumable=False,
            )
            existing = self.service.files().list(
                q=f"name='{BUDGETS_FILE}' and '{self._folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute().get("files", [])
            if existing:
                self.service.files().update(fileId=existing[0]["id"], media_body=media).execute()
            else:
                self.service.files().create(
                    body={"name": BUDGETS_FILE, "parents": [self._folder_id]},
                    media_body=media, fields="id"
                ).execute()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error saving budgets: {e}")
            return False

    async def get_budgets(self) -> List[Dict[str, Any]]:
        """Load budget configuration from Google Drive"""
        try:
            await self._ensure_folders()
            files = self.service.files().list(
                q=f"name='{BUDGETS_FILE}' and '{self._folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute().get("files", [])
            if not files:
                return []
            content = self._download_file(files[0]["id"])
            return json.loads(content) if content else []
        except Exception as e:
            import logging
            logging.error(f"Error loading budgets: {e}")
            return []

    async def save_user_profile(self, profile: Dict[str, Any]) -> bool:
        """Save user profile to Google Drive"""
        try:
            await self._ensure_folders()
            content = json.dumps(profile, indent=2, default=str)
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="application/json",
                resumable=False,
            )
            existing = self.service.files().list(
                q=f"name='{USER_PROFILE_FILE}' and '{self._folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute().get("files", [])
            if existing:
                self.service.files().update(fileId=existing[0]["id"], media_body=media).execute()
            else:
                self.service.files().create(
                    body={"name": USER_PROFILE_FILE, "parents": [self._folder_id]},
                    media_body=media, fields="id"
                ).execute()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error saving profile: {e}")
            return False

    async def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Load user profile from Google Drive"""
        try:
            await self._ensure_folders()
            files = self.service.files().list(
                q=f"name='{USER_PROFILE_FILE}' and '{self._folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute().get("files", [])
            if not files:
                return None
            content = self._download_file(files[0]["id"])
            return json.loads(content) if content else None
        except Exception as e:
            import logging
            logging.error(f"Error loading profile: {e}")
            return None

    async def export_to_csv(self, start_date: date, end_date: date) -> Optional[str]:
        """Export expenses to CSV and save in Drive, return file URL"""
        try:
            import csv
            expenses = await self.get_expenses(start_date, end_date)
            if not expenses:
                return None
            await self._ensure_folders()
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["date", "amount", "currency", "category", "description", "merchant", "payment_method"]
            )
            writer.writeheader()
            for exp in expenses:
                writer.writerow({
                    "date": exp.get("date", ""),
                    "amount": exp.get("amount", ""),
                    "currency": exp.get("currency", "USD"),
                    "category": exp.get("category", ""),
                    "description": exp.get("description", ""),
                    "merchant": exp.get("merchant", ""),
                    "payment_method": exp.get("payment_method", ""),
                })
            csv_content = output.getvalue()
            file_name = f"expenses_{start_date.isoformat()}_{end_date.isoformat()}.csv"
            media = MediaIoBaseUpload(
                io.BytesIO(csv_content.encode("utf-8")),
                mimetype="text/csv",
                resumable=False,
            )
            file_metadata = {
                "name": file_name,
                "parents": [self._folder_id],
            }
            result = self.service.files().create(
                body=file_metadata, media_body=media, fields="id, webViewLink"
            ).execute()
            self.service.permissions().create(
                fileId=result["id"],
                body={"type": "anyone", "role": "reader"}
            ).execute()
            return result.get("webViewLink")
        except Exception as e:
            import logging
            logging.error(f"Error exporting CSV: {e}")
            return None
