#!/usr/bin/env python3
"""
Клиент для тестирования API через RabbitMQ
"""

import logging
import json
from app.rabbitmq_client import RabbitMQClient
from app.schemas_rabbitmq import RequestMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api():
    """Протестировать различные API вызовы"""
    client = RabbitMQClient()
    
    try:
        # Пример 1: Получить список авторов
        logger.info("Test 1: Get authors")
        request = RequestMessage(
            version="v1",
            action="get_authors",
            auth="test-api-key",  # Замените на реальный ключ
            data={"page": 1, "size": 10}
        )
        response = client.send_request(request)
        logger.info(f"Response: {response}")
        
        # Пример 2: Создать автора
        logger.info("\nTest 2: Create author")
        request = RequestMessage(
            version="v1",
            action="create_author",
            auth="test-api-key",
            data={
                "name": "Фёдор Достоевский",
                "nationality": "Русский",
                "bio": "Великий русский писатель"
            },
            idempotency_key="create-author-123"  # Для идемпотентности
        )
        response = client.send_request(request)
        logger.info(f"Response: {response}")
        
        # Пример 3: Получить книги с фильтрацией (v2)
        logger.info("\nTest 3: Get books with availability filter (v2)")
        request = RequestMessage(
            version="v2",
            action="get_books",
            auth="test-api-key",
            data={
                "page": 1,
                "size": 5,
                "is_available": True
            },
            fields="id,title,is_available,author.name"  # Опциональные поля
        )
        response = client.send_request(request)
        logger.info(f"Response: {response}")
        
        # Пример 4: Обновить доступность книги
        logger.info("\nTest 4: Update book availability")
        request = RequestMessage(
            version="v2",
            action="update_book_availability",
            auth="test-api-key",
            data={
                "id": 1,
                "is_available": False
            }
        )
        response = client.send_request(request)
        logger.info(f"Response: {response}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        client.close()

def interactive_mode():
    """Интерактивный режим для тестирования"""
    client = RabbitMQClient()
    
    print("\n" + "="*50)
    print("Library Management API - RabbitMQ Client")
    print("="*50)
    
    while True:
        print("\nAvailable actions:")
        print("1. Get authors")
        print("2. Get author by ID")
        print("3. Create author")
        print("4. Get books")
        print("5. Create book")
        print("6. Update book availability (v2 only)")
        print("7. Exit")
        
        choice = input("\nSelect action (1-7): ").strip()
        
        if choice == '7':
            break
        
        try:
            if choice == '1':
                page = input("Page (default 1): ").strip() or "1"
                size = input("Size (default 10): ").strip() or "10"
                name = input("Name filter (optional): ").strip() or None
                version = input("API version (v1/v2, default v1): ").strip() or "v1"
                fields = input("Fields (optional, comma-separated): ").strip() or None
                
                request = RequestMessage(
                    version=version,
                    action="get_authors",
                    auth="test-api-key",
                    data={
                        "page": int(page),
                        "size": int(size),
                        "name": name
                    },
                    fields=fields
                )
                
            elif choice == '2':
                author_id = input("Author ID: ").strip()
                version = input("API version (v1/v2, default v1): ").strip() or "v1"
                fields = input("Fields (optional, comma-separated): ").strip() or None
                
                request = RequestMessage(
                    version=version,
                    action="get_author",
                    auth="test-api-key",
                    data={"id": int(author_id)},
                    fields=fields
                )
            
            elif choice == '3':
                name = input("Author name: ").strip()
                nationality = input("Nationality: ").strip()
                bio = input("Bio (optional): ").strip() or None
                version = input("API version (v1/v2, default v1): ").strip() or "v1"
                
                request = RequestMessage(
                    version=version,
                    action="create_author",
                    auth="test-api-key",
                    data={
                        "name": name,
                        "nationality": nationality,
                        "bio": bio
                    },
                    idempotency_key=f"create-author-{name}"
                )
            
            elif choice == '4':
                page = input("Page (default 1): ").strip() or "1"
                size = input("Size (default 10): ").strip() or "10"
                title = input("Title filter (optional): ").strip() or None
                author_id = input("Author ID filter (optional): ").strip() or None
                version = input("API version (v1/v2, default v1): ").strip() or "v1"
                fields = input("Fields (optional, comma-separated): ").strip() or None
                
                data = {
                    "page": int(page),
                    "size": int(size),
                    "title": title
                }
                
                if author_id:
                    data["author_id"] = int(author_id)
                
                # Добавляем фильтр по доступности только для v2
                if version == 'v2':
                    available = input("Filter by availability (true/false/empty): ").strip()
                    if available.lower() in ['true', 'false']:
                        data["is_available"] = available.lower() == 'true'
                
                request = RequestMessage(
                    version=version,
                    action="get_books",
                    auth="test-api-key",
                    data=data,
                    fields=fields
                )
            elif choice == '5':
                # Создание книги
                title = input("Book title: ").strip()
                isbn = input("ISBN: ").strip()
                author_id = input("Author ID: ").strip()
                description = input("Description (optional): ").strip() or None
                year_published = input("Year published (optional): ").strip() or None
                publisher = input("Publisher (optional): ").strip() or None
                pages = input("Pages (optional): ").strip() or None
                language = input("Language (default 'en'): ").strip() or "en"
                version = input("API version (v1/v2, default v2): ").strip() or "v2"
                
                # Для v2 спрашиваем доступность
                is_available = None
                if version == 'v2':
                    available = input("Available (true/false, default true): ").strip() or "true"
                    if available.lower() in ['true', 'false']:
                        is_available = available.lower() == 'true'
                
                # Формируем данные
                data = {
                    "title": title,
                    "isbn": isbn,
                    "author_id": int(author_id),
                    "language": language
                }
                
                # Добавляем опциональные поля
                if description:
                    data["description"] = description
                if year_published:
                    data["year_published"] = int(year_published)
                if publisher:
                    data["publisher"] = publisher
                if pages:
                    data["pages"] = int(pages)
                if is_available is not None:
                    data["is_available"] = is_available
                
                # Создаем запрос
                request = RequestMessage(
                    version=version,
                    action="create_book",
                    auth="test-api-key",
                    data=data,
                    idempotency_key=f"create-book-{isbn}"
                )
            elif choice == '6':
                book_id = input("Book ID: ").strip()
                available = input("Available (true/false): ").strip().lower()
                fields = input("Fields (optional, comma-separated): ").strip() or None
                
                request = RequestMessage(
                    version="v2",
                    action="update_book_availability",
                    auth="test-api-key",
                    data={
                        "id": int(book_id),
                        "is_available": available == 'true'
                    },
                    fields=fields
                )
            
            else:
                print("Invalid choice")
                continue
            
            # Отправляем запрос
            print(f"\nSending request: {request.action}")
            response = client.send_request(request, timeout=60)
            
            if response:
                print(f"\nResponse status: {response.status}")
                if response.data:
                    print(f"Data: {json.dumps(response.data, indent=2, ensure_ascii=False)}")
                if response.error:
                    print(f"Error: {response.error}")
                if response.pagination:
                    print(f"Pagination: {response.pagination}")
            else:
                print("No response received (timeout)")
                
        except Exception as e:
            print(f"Error: {e}")
    
    client.close()
    print("\nGoodbye!")

if __name__ == "__main__":
    # test_api()
    interactive_mode()