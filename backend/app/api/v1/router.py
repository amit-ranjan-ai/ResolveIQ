from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.organisations import router as organisations_router
from app.api.v1.team_memberships import router as team_memberships_router
from app.api.v1.teams import router as teams_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(organisations_router)
api_router.include_router(teams_router)
api_router.include_router(team_memberships_router)
api_router.include_router(tickets_router)
api_router.include_router(users_router)


@api_router.get("/status")
def api_status():
    return {
        "message": "ResolveIQ API v1 is working",
        "status": "healthy",
        "version": "v1",
    }
