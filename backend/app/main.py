from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Support and IT Operations Intelligence Platform",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to ResolveIQ API",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
    }