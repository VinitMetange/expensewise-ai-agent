"""Database layer using SQLAlchemy async with PostgreSQL"""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, JSON, Boolean, select, update
from sqlalchemy.sql import func

from api.config import settings

engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")
    storage_provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserCredentialsModel(Base):
    __tablename__ = "user_credentials"

    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), default="google_drive")
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OAuthStateModel(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(100), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


async def init_db():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes"""
    async with AsyncSessionLocal() as session:
        yield session


# --- User operations ---

async def get_user(phone: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserModel).where(UserModel.phone == phone))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "phone": user.phone,
            "name": user.name,
            "currency": user.currency,
            "timezone": user.timezone,
            "language": user.language,
            "storage_provider": user.storage_provider,
            "is_onboarded": user.is_onboarded,
        }


async def create_user(phone: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        user = UserModel(phone=phone, **(data or {}))
        db.add(user)
        await db.commit()
        return await get_user(phone)


async def update_user(phone: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(UserModel).where(UserModel.phone == phone).values(**data)
        )
        await db.commit()
        return await get_user(phone)


# --- Credentials operations ---

async def get_user_credentials(phone: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserCredentialsModel).where(UserCredentialsModel.phone == phone)
        )
        creds = result.scalar_one_or_none()
        if not creds:
            return None
        return {
            "access_token": creds.access_token,
            "refresh_token": creds.refresh_token,
            "expires_at": creds.token_expiry,
            "provider": creds.provider,
        }


async def save_user_credentials(phone: str, creds_data: Dict[str, Any]) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserCredentialsModel).where(UserCredentialsModel.phone == phone)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await db.execute(
                update(UserCredentialsModel)
                .where(UserCredentialsModel.phone == phone)
                .values(**creds_data)
            )
        else:
            creds = UserCredentialsModel(phone=phone, **creds_data)
            db.add(creds)
        await db.commit()
        return True


async def update_user_credentials(phone: str, data: Dict[str, Any]) -> bool:
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(UserCredentialsModel)
            .where(UserCredentialsModel.phone == phone)
            .values(**data)
        )
        await db.commit()
        return True


# --- Conversation history ---

async def save_message(phone: str, role: str, content: str) -> None:
    import uuid
    async with AsyncSessionLocal() as db:
        msg = ConversationModel(
            id=str(uuid.uuid4()),
            phone=phone,
            role=role,
            content=content,
        )
        db.add(msg)
        await db.commit()


async def get_conversation_history(phone: str, limit: int = 10) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationModel)
            .where(ConversationModel.phone == phone)
            .order_by(ConversationModel.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]


# --- OAuth state management ---

async def save_oauth_state(state: str, phone: str) -> None:
    async with AsyncSessionLocal() as db:
        oauth = OAuthStateModel(state=state, phone=phone)
        db.add(oauth)
        await db.commit()


async def get_oauth_state(state: str) -> Optional[str]:
    """Returns phone number associated with state"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OAuthStateModel).where(OAuthStateModel.state == state)
        )
        record = result.scalar_one_or_none()
        if record:
            await db.delete(record)
            await db.commit()
            return record.phone
        return None
