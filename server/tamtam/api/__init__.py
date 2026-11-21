"""Routes de l'API, toutes sous /api/v1."""
from fastapi import APIRouter

from . import admin, auth, connect, posts, projects

router = APIRouter(prefix="/api/v1")
for module in (auth, projects, connect, posts, admin):
    router.include_router(module.router)
