# Клиент для JSONPlaceholder API

Python-клиент для взаимодействия с тестовым REST API JSONPlaceholder.

## Возможности
*   Полный набор CRUD-операций для ресурса `/posts`
*   Обработка ошибок и пагинация
*   Идемпотентное создание постов (проверка дубликатов)
*   Частичное и полное обновление записей

## Быстрый старт
```python
from app import JSONPlaceholderClient
client = JSONPlaceholderClient()

# Получить пост
post = client.get_post(1)

# Создать пост
new_post = client.create_post(
    title="Заголовок",
    body="Текст поста",
    user_id=1
)
```

Формат ответов
Все методы возвращают словари Python или списки словарей, соответствующие структуре JSONPlaceholder.

Пример ответа для get_post(1):

json
{
  "userId": 1,
  "id": 1,
  "title": "...",
  "body": "..."
}