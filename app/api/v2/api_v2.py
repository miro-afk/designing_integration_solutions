from fastapi import APIRouter
from app.api.v2.endpoints import books

api_router = APIRouter()

# Авторы остаются без изменений в v2
from app.api.v1.endpoints import authors as authors_v1
api_router.include_router(authors_v1.router)

# Книги с новой версией
api_router.include_router(books.router)