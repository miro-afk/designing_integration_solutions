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

router = APIRouter(prefix="/authors", tags=["authors"])

@router.get("/", response_model=schemas.PaginatedResponse)
@limiter.limit("100/minute")
async def read_authors(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    name: Optional[str] = None,
    fields: Optional[str] = Query(None, description="Поля для включения в ответ (через запятую)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Получить список авторов с пагинацией
    """
    authors, total = crud.get_authors(db, skip=skip, limit=limit, name=name)
    result = []
    for author in authors:
        author_data = utils.sqlalchemy_to_dict(author)
        if fields:
            author_data = schemas.FieldSelector.filter_response(author_data, fields)
        result.append(author_data)
    response = {
        "items": result,
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }

    
    return response

@router.get("/{author_id}", response_model=schemas.AuthorV1)
@limiter.limit("100/minute")
async def read_author(
    request: Request,
    response: Response,
    author_id: int,
    fields: Optional[str] = Query(None, description="Поля для включения в ответ (через запятую)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Получить автора по ID
    """
    db_author = crud.get_author(db, author_id=author_id)
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    
    author_data = utils.sqlalchemy_to_dict(db_author)
    if fields:
        author_data = schemas.FieldSelector.filter_response(author_data, fields)
    return author_data

@router.post("/", response_model=schemas.AuthorV1, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_author(
    request: Request,
    response: Response,
    author: schemas.AuthorCreateV1,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = None
):
    """
    Создать нового автора
    
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
    
    db_author = crud.create_author(db=db, author=author)
    
    # Сохраняем ответ для идемпотентности
    if idempotency_key:
        idempotency_manager.store_response(idempotency_key, db_author)
    
    return utils.sqlalchemy_to_dict(db_author)

@router.put("/{author_id}", response_model=schemas.AuthorV1)
@limiter.limit("60/minute")
async def update_author(
    request: Request,
    response: Response,
    author_id: int,
    author_update: schemas.AuthorUpdateV1,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Обновить автора
    """
    db_author = crud.update_author(db, author_id=author_id, author_update=author_update)
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return utils.sqlalchemy_to_dict(db_author)

@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_author(
    request: Request,
    response: Response,
    author_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Удалить автора
    """
    success = crud.delete_author(db, author_id=author_id)
    if not success:
        raise HTTPException(status_code=404, detail="Author not found")
    return None