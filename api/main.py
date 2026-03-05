"""
ExpenseWise - FastAPI Main Application
Entry point for the ExpenseWise AI Agent backend
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

from api.config import settings
from api.routes import whatsapp, auth, expenses, users, budgets, reports


# ============================================================
# App Lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    logger.info("ExpenseWise AI Agent starting up...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Bedrock Model: {settings.bedrock_model_id}")
    yield
    logger.info("ExpenseWise AI Agent shutting down...")


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="ExpenseWise AI Agent",
    description="WhatsApp-based Agentic AI Expense Management Solution",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://expensewise.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Global Exception Handler
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )


# ============================================================
# Routes
# ============================================================

app.include_router(whatsapp.router, prefix="/webhook", tags=["WhatsApp"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(expenses.router, prefix="/api/v1/expenses", tags=["Expenses"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(budgets.router, prefix="/api/v1/budgets", tags=["Budgets"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


# ============================================================
# Health Check
# ============================================================

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "ExpenseWise AI Agent",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.app_env,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "bedrock_model": settings.bedrock_model_id,
        "debug": settings.debug,
    }


# ============================================================
# Dev Runner
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
