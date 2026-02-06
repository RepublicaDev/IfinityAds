from fastapi import APIRouter
from app.api.v1 import router as v1_router
from app.api.v2 import router as v2_router

router = APIRouter()

# Aqui montamos a árvore de rotas: /api/v1 e /api/v2
router.include_router(v1_router, prefix="/v1")
router.include_router(v2_router, prefix="/v2")