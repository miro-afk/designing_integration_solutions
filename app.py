import requests
from typing import Optional, Dict, Any, List
from requests.exceptions import RequestException
import time

class JSONPlaceholderClient:
    """Клиент для работы с JSONPlaceholder API."""
    
    BASE_URL = "https://jsonplaceholder.typicode.com"
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        # Настраиваем общие заголовки для всех запросов
        self.session.headers.update({
            "Content-type": "application/json; charset=UTF-8",
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Выполняет HTTP-запрос с обработкой ошибок."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()  # Генерирует исключение для кодов 4xx/5xx
            # Для операции DELETE сервер возвращает пустой объект {}
            return response.json() if response.content else {}
        except RequestException as e:
            print(f"Ошибка при выполнении запроса {method} {url}: {e}")
            if hasattr(e.response, 'status_code'):
                print(f"Код статуса: {e.response.status_code}")
                try:
                    print(f"Ответ сервера: {e.response.json()}")
                except:
                    print(f"Текст ответа: {e.response.text}")
            return None
    
    # --- CRUD операции для постов (/posts) ---
    def get_all_posts(self, limit: Optional[int] = None, page: Optional[int] = None) -> Optional[List[Dict]]:
        """Получить все посты с поддержкой пагинации."""
        params = {}
        if limit:
            params['_limit'] = limit
        if page:
            params['_page'] = page
        
        result = self._make_request('GET', '/posts', params=params)
        # Добавляем информацию о пагинации в ответ
        if result and page:
            return {
                "page": page,
                "limit": limit or 10,
                "posts": result
            }
        return result
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Получить конкретный пост по ID."""
        return self._make_request('GET', f'/posts/{post_id}')
    
    def create_post(self, title: str, body: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Создать новый пост. Идемпотентная операция с проверкой дубликатов."""
        # Простая проверка на дубликат: ищем пост с таким же title и user_id
        if self._find_duplicate_post(title, user_id):
            print(f"Пост с заголовком '{title}' для пользователя {user_id} уже существует. Создание пропущено.")
            return None
        
        new_post = {
            "title": title,
            "body": body,
            "userId": user_id
        }
        return self._make_request('POST', '/posts', json=new_post)
    
    def _find_duplicate_post(self, title: str, user_id: int) -> bool:
        """Вспомогательный метод для поиска дубликатов постов."""
        all_posts = self.get_all_posts()
        if all_posts:
            for post in all_posts:
                if post.get('title') == title and post.get('userId') == user_id:
                    return True
        return False
    
    def update_post(self, post_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Обновить пост (полное обновление через PUT)."""
        return self._make_request('PUT', f'/posts/{post_id}', json=kwargs)
    
    def patch_post(self, post_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Частично обновить пост (через PATCH)."""
        return self._make_request('PATCH', f'/posts/{post_id}', json=kwargs)
    
    def delete_post(self, post_id: int) -> bool:
        """Удалить пост."""
        result = self._make_request('DELETE', f'/posts/{post_id}')
        # DELETE запрос возвращает пустой объект {} при успехе
        return result is not None

# --- Пример использования клиента ---
if __name__ == "__main__":
    client = JSONPlaceholderClient()
    
    print("1. Получение всех постов (с пагинацией):")
    posts_page = client.get_all_posts(limit=3, page=2)
    if posts_page:
        for post in posts_page.get('posts', []):
            print(f"  - {post['title'][:30]}... (ID: {post['id']})")
    
    print("\n2. Получение конкретного поста:")
    post = client.get_post(1)
    if post:
        print(f"  Заголовок: {post['title']}")
    
    print("\n3. Создание нового поста (с проверкой дубликатов):")
    new_post = client.create_post(
        title="Изучение API",
        body="JSONPlaceholder отлично подходит для обучения.",
        user_id=1
    )
    if new_post:
        print(f"  Создан пост с ID: {new_post.get('id')}")
    
    print("\n4. Идемпотентность: повторная попытка создать тот же пост:")
    duplicate_post = client.create_post(
        title="Изучение API", 
        body="Повторное тело.", 
        user_id=1
    )
    if not duplicate_post:
        print("  Дубликат не создан (корректное поведение).")
    
    print("\n5. Полное обновление поста:")
    updated = client.update_post(1, title="Обновлённый заголовок", body="Новое содержание", userId=1)
    if updated:
        print(f"  Обновлён пост ID {updated.get('id')}. Новый заголовок: {updated['title']}")
    
    print("\n6. Частичное обновление поста:")
    patched = client.patch_post(1, title="Частично обновлённый заголовок")
    if patched:
        print(f"  Частично обновлён пост ID {patched.get('id')}")
    
    print("\n7. Удаление поста:")
    if client.delete_post(1):
        print("  Пост ID 1 помечен как удалённый (симуляция на JSONPlaceholder)")