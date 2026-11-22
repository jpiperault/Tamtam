"""Routes de l'API, toutes sous /api/v1."""
from fastapi import APIRouter

from . import admin, ai, auth, connect, inbox, insights, posts, projects

router = APIRouter(prefix="/api/v1")
for module in (auth, projects, connect, posts, admin, ai, insights, inbox):
    router.include_router(module.router)
