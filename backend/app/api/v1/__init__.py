"""API v1 router configuration."""

from fastapi import APIRouter
from app.api.v1.documents import router as documents_router
from app.api.v1.pdf import router as pdf_router
from app.api.v1.quiz import router as quiz_router
from app.api.v1.chat import router as chat_router
from app.api.v1.reframe import router as reframe_router
from app.api.v1.progress import router as progress_router
from app.api.v1.evaluation import router as evaluation_router   # NEW


api_router = APIRouter()

# Include all sub-routers
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(pdf_router, prefix="/pdf", tags=["pdf"])
api_router.include_router(quiz_router, prefix="/quiz", tags=["quiz"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(reframe_router, prefix="/reframe", tags=["reframe"])
api_router.include_router(progress_router, prefix="/progress", tags=["progress"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])  # NEW