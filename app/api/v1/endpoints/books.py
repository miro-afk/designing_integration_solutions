from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional

import app.crud as crud
import app.schemas as schemas
from app.database import get_db
from app.auth import verify_api_key
from app.rate_limiter import limiter
from app.idempotency import IdempotencyKeyManager
import app.utils as utils

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/", response_model=schemas.PaginatedResponse)
@limiter.limit("100/minute")
async def read_books(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    title: Optional[str] = None,
    author_id: Optional[int] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Получить список книг с пагинацией
    """
    books, total = crud.get_books(
        db, skip=skip, limit=limit, 
        title=title, author_id=author_id,
        is_available=None  # v1 не поддерживает фильтрацию по доступности
    )
    result = []
    for book in books:
        book = utils.book_to_pydantic_v1(book)
        result+=book
    response = {
        "items": result,
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }
    
    return response

@router.get("/{book_id}", response_model=schemas.BookV1)
@limiter.limit("100/minute")
async def read_book(
    request: Request,
    response: Response,
    book_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Получить книгу по ID
    """
    db_book = crud.get_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return utils.sqlalchemy_to_dict(db_book)

@router.post("/", response_model=schemas.BookV1, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_book(
    request: Request,
    response: Response,
    book: schemas.BookCreateV1,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = None
):
    """
    Создать новую книгу
    
    Поддерживает идемпотентность через заголовок Idempotency-Key
    """
    # Проверка идемпотентности
    if idempotency_key:
        idempotency_manager = IdempotencyKeyManager()
        if idempotency_manager.check_and_store(idempotency_key):
            # Возвращаем сохраненный ответ если есть
            saved_response = idempotency_manager.get_response(idempotency_key)
            if saved_response:
                import json
                return json.loads(saved_response)
    
    # Проверяем существование автора
    author = crud.get_author(db, author_id=book.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    db_book = crud.create_book(db=db, book=book)
    
    # Сохраняем ответ для идемпотентности
    if idempotency_key:
        idempotency_manager.store_response(idempotency_key, db_book)
    
    return utils.sqlalchemy_to_dict(db_book)

@router.put("/{book_id}", response_model=schemas.BookV1)
@limiter.limit("60/minute")
async def update_book(
    request: Request,
    response: Response,
    book_id: int,
    book_update: schemas.BookUpdateV1,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Обновить книгу
    """
    if book_update.author_id:
        author = crud.get_author(db, author_id=book_update.author_id)
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
    
    db_book = crud.update_book(db, book_id=book_id, book_update=book_update)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return utils.sqlalchemy_to_dict(db_book)

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_book(
    request: Request,
    response: Response,
    book_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Удалить книгу
    """
    success = crud.delete_book(db, book_id=book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return None