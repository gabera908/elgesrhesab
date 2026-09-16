"""تجميع كل المسارات في التطبيق."""
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.american_journal import router as american_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.cash_flow import router as cash_flow_router
from app.api.export import router as export_router
from app.api.extra_reports import router as extra_reports_router
from app.api.fiscal import router as fiscal_router
from app.api.income_statement import router as income_router
from app.api.journal_entries import router as entries_router
from app.api.journals_api import router as journals_router
from app.api.opening_balance import router as opening_balance_router
from app.api.partners import router as partners_router
from app.api.reports import router as reports_router
from app.api.settings_api import router as settings_router
from app.api.users_admin import router as users_admin_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(entries_router)
api_router.include_router(journals_router)
api_router.include_router(opening_balance_router)
api_router.include_router(partners_router)
api_router.include_router(fiscal_router)
api_router.include_router(attachments_router)
api_router.include_router(export_router)
api_router.include_router(extra_reports_router)
api_router.include_router(reports_router)
api_router.include_router(income_router)
api_router.include_router(cash_flow_router)
api_router.include_router(american_router)
api_router.include_router(settings_router)
api_router.include_router(users_admin_router)
