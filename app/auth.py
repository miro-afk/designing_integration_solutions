from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

load_dotenv()

# Простая аутентификация по API ключу
# Выбор обоснован: для внутреннего/административного API достаточно простого ключа
# Не требует сложной инфраструктуры как OAuth
API_KEYS = os.getenv("API_KEYS", "").split(",")

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Проверка API ключа из заголовка Authorization
    """
    api_key = credentials.credentials
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key