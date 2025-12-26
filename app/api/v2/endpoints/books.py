from fastapi import APIRouter, Depends, HTTPException, status, Query, Request,Response
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
    is_available: Optional[bool] = None,  # Новая возможность в v2
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Получить список книг с пагинацией
    
    Новое в v2: фильтрация по is_available
    """
    books, total = crud.get_books(
        db, skip=skip, limit=limit, 
        title=title, author_id=author_id,
        is_available=is_available  # v2 поддерживает фильтрацию по доступности
    )
    result = []
    for book in books:
        book = utils.book_to_pydantic_v2(book)
        result+=book
    response = {
        "items": result,
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }
    

    
    return response

@router.get("/{book_id}", response_model=schemas.BookV2)
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
    
    Новое в v2: возвращает поле is_available
    """
    db_book = crud.get_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return utils.sqlalchemy_to_dict(db_book)

@router.post("/", response_model=schemas.BookV2, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_book(
    request: Request,
    response: Response,
    book: schemas.BookCreateV2,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = None
):
    """
    Создать новую книгу
    
    Новое в v2: поддерживает поле is_available при создании
    
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
    
    db_book = crud.create_book_v2(db=db, book=book)
    
    # Сохраняем ответ для идемпотентности
    if idempotency_key:
        idempotency_manager.store_response(idempotency_key, db_book)
    
    return utils.sqlalchemy_to_dict(db_book)

@router.put("/{book_id}", response_model=schemas.BookV2)
@limiter.limit("60/minute")
async def update_book(
    request: Request,
    response: Response,
    book_id: int,
    book_update: schemas.BookUpdateV2,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Обновить книгу
    
    Новое в v2: поддерживает обновление поля is_available
    """
    if book_update.author_id:
        author = crud.get_author(db, author_id=book_update.author_id)
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
    
    db_book = crud.update_book_v2(db, book_id=book_id, book_update=book_update)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return utils.sqlalchemy_to_dict(db_book)

@router.patch("/{book_id}/availability", response_model=schemas.BookV2)
@limiter.limit("60/minute")
async def update_book_availability(
    request: Request,
    response: Response,
    book_id: int,
    is_available: bool,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Обновить доступность книги
    
    Новая конечная точка в v2 для удобного управления доступностью
    """
    db_book = crud.get_book(db, book_id=book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db_book.is_available = is_available
    db.commit()
    db.refresh(db_book)
    
    return utils.sqlalchemy_to_dict(db_book)