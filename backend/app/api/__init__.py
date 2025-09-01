from fastapi import APIRouter
from . import routes_projects, routes_jobs

api_router = APIRouter()
api_router.include_router(routes_projects.router)
api_router.include_router(routes_jobs.router)
