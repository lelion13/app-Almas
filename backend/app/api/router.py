from fastapi import APIRouter

from app.api.routers import auth, closings, expense_imports, expenses, imports, mercado_pago, studio, teachers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(closings.router, prefix="/closings", tags=["closings"])
api_router.include_router(imports.router, tags=["imports"])
api_router.include_router(expense_imports.router, tags=["expense-imports"])
api_router.include_router(expenses.router, tags=["expenses"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])
api_router.include_router(mercado_pago.router)
api_router.include_router(studio.router, prefix="/studio", tags=["studio"])
