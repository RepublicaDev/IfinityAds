# api package
from fastapi import APIRouter
# Importe aqui os módulos de rota específicos da v1
# Exemplo: from . import auth, products, jobs

router = APIRouter()

# Inclua as sub-rotas aqui
# router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])