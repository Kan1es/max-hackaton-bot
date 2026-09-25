from fastapi import APIRouter
from app.api.v1.endpoints import applications, classify, health, profiles, programs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(profiles.router)
api_router.include_router(programs.router)
api_router.include_router(applications.router)
api_router.include_router(classify.router)
