import pika
import json
import logging
import time
import uuid
from typing import Dict, Any
from pydantic import ValidationError
from datetime import datetime

from app.schemas_rabbitmq import RequestMessage, ResponseMessage, ErrorDetail
from app.auth import verify_api_key
from app.database import get_db
from app.idempotency import IdempotencyKeyManager
import app.crud as crud
import app.utils as utils
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RabbitMQServer:
    def __init__(self, host='rabbitmq', port=5672, username='admin', password='admin123'):
        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(username, password)
        self.connection = None
        self.channel = None
        self.idempotency_manager = IdempotencyKeyManager()
        self.connect()
        self.setup_queues()
    
    def connect(self):
        """Установить соединение с RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ server")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def setup_queues(self):
        """Настроить очереди и обработчики"""
        # Настройки для DLQ
        dlq_args = {
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'api.dlq',
            'x-message-ttl': 60000  # 60 секунд
        }
        
        try:
            # Объявляем основную очередь запросов
            self.channel.queue_declare(queue='api.requests', durable=True)
            
            # Объявляем очередь для ответов
            self.channel.queue_declare(queue='api.responses', durable=True)
            
            # Объявляем очередь ошибок
            self.channel.queue_declare(queue='api.errors', durable=True)
            
            # Объявляем Dead Letter Queue
            self.channel.queue_declare(queue='api.dlq', durable=True)
            
            # Пытаемся объявить очередь для повторной обработки с параметрами
            # Если очередь уже существует с другими параметрами, удалим и создадим заново
            try:
                self.channel.queue_declare(queue='api.requests.retry', durable=True, arguments=dlq_args)
            except pika.exceptions.ChannelClosedByBroker as e:
                if "PRECONDITION_FAILED" in str(e):
                    logger.warning("Queue 'api.requests.retry' exists with different parameters. Deleting and recreating...")
                    # Удаляем существующую очередь
                    self.channel.queue_delete(queue='api.requests.retry')
                    # Создаем заново с правильными параметрами
                    self.channel.queue_declare(queue='api.requests.retry', durable=True, arguments=dlq_args)
                else:
                    raise
            
            # Настраиваем QoS для ограничения одновременной обработки
            self.channel.basic_qos(prefetch_count=10)
            
            # Настраиваем обработчик запросов
            self.channel.basic_consume(
                queue='api.requests',
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info("RabbitMQ queues configured successfully")
            
        except Exception as e:
            logger.error(f"Error setting up queues: {e}")
            raise
    
    def process_message(self, ch, method, properties, body):
        """Обработать входящее сообщение"""
        request_id = None
        correlation_id = properties.correlation_id
        
        try:
            
            # Парсим сообщение
            request_data = json.loads(body)
            request = RequestMessage(**request_data)
            request_id = request.id
            
            logger.info(f"Processing request {request_id} - {request.action}")
            
            # Проверяем идемпотентность
            if request.idempotency_key:
                if self.idempotency_manager.check_and_store(request.idempotency_key):
                    saved_response = self.idempotency_manager.get_response(request.idempotency_key)
                    if saved_response:
                        # Отправляем сохраненный ответ
                        response_msg = ResponseMessage(**saved_response)
                        response_msg.correlation_id = correlation_id
                        self.send_response(correlation_id, properties.reply_to, response_msg)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
            
            # Обрабатываем запрос
            response = self.handle_request(request)
            response.correlation_id = correlation_id
            
            # Сохраняем ответ для идемпотентности/err
            if request.idempotency_key:
                self.idempotency_manager.store_response(request.idempotency_key, response.dict())
            
            # Отправляем ответ
            self.send_response(correlation_id, properties.reply_to, response)
            
            # Подтверждаем обработку
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.info(f"Request {request_id} processed successfully")
            
        except ValidationError as e:
            # Ошибка валидации
            logger.error(f"Validation error for request {request_id}: {e}")
            error_response = ResponseMessage(
                correlation_id=correlation_id,
                status="validation_error",
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request format",
                    "details": e.errors()
                }
            )
            self.send_response(correlation_id, properties.reply_to, error_response)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {e}")
            
            # Отправляем ошибку клиенту
            error_response = ResponseMessage(
                correlation_id=correlation_id,
                status="error",
                error={
                    "code": "PROCESSING_ERROR",
                    "message": str(e)
                }
            )
            self.send_response(correlation_id, properties.reply_to, error_response)
            
            # Помещаем сообщение в очередь повторной обработки
            retry_count = properties.headers.get('x-retry-count', 0) if properties.headers else 0
            if retry_count < 3:  # Максимум 3 попытки
                logger.info(f"Retrying request {request_id}, attempt {retry_count + 1}")
                headers = {'x-retry-count': retry_count + 1}
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key='api.requests.retry',
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        correlation_id=properties.correlation_id,
                        reply_to=properties.reply_to,
                        headers=headers
                    )
                )
            
            # Подтверждаем обработку исходного сообщения
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def handle_request(self, request: RequestMessage) -> ResponseMessage:
        """Обработать запрос в зависимости от действия"""
        # Проверяем аутентификацию
        if request.auth and not self.authenticate_request(request.auth):
            return ResponseMessage(
                correlation_id=request.correlation_id,
                status="error",
                error={
                    "code": "UNAUTHORIZED",
                    "message": "Invalid API key"
                }
            )
        
        # Получаем сессию БД
        db = next(get_db())
        
        try:
            # Определяем версию API
            version = request.version
            
            # Обрабатываем действие
            handler_name = f"handle_{request.action}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                result = handler(db, request.data or {}, version, request.fields)
                
                return ResponseMessage(
                    correlation_id=request.correlation_id,
                    status="success",
                    data=result.get("data"),
                    pagination=result.get("pagination")
                )
            else:
                raise ValueError(f"Unknown action: {request.action}")
                
        except ValueError as e:
            # Бизнес-логика ошибки (например, не найден автор)
            return ResponseMessage(
                correlation_id=request.correlation_id,
                status="error",
                error={
                    "code": "NOT_FOUND",
                    "message": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Error handling {request.action}: {e}")
            return ResponseMessage(
                correlation_id=request.correlation_id,
                status="error",
                error={
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            )
        finally:
            db.close()
    
    def authenticate_request(self, api_key: str) -> bool:
        """Проверить API ключ"""
        try:
            from app.auth import verify_api_key
            # Адаптируем под нашу новую систему
            # В реальном проекте можно хранить ключи в Redis или БД
            valid_keys = ["test-api-key", "admin-key-123", "client-key-456"]
            return api_key in valid_keys
        except:
            return False
    
    def send_response(self, correlation_id: str, reply_to: str, response: ResponseMessage):
        """Отправить ответ обратно клиенту"""
        if not reply_to:
            logger.warning(f"No reply_to queue for correlation_id {correlation_id}")
            return
        response_dict = response.dict()
        response_body = json.dumps(response_dict, cls=DateTimeEncoder, ensure_ascii=False)
        encoded_body = response_body.encode('utf-8', errors='replace')
        self.channel.basic_publish(
            exchange='',
            routing_key=reply_to,
            body=encoded_body,
            properties=pika.BasicProperties(
                correlation_id=correlation_id,
                content_type='application/json'
            )
        )
    
    # Обработчики действий
    def handle_get_authors(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Получить список авторов"""
        page = data.get('page', 1)
        size = data.get('size', 100)
        name = data.get('name')
        
        skip = (page - 1) * size
        authors, total = crud.get_authors(db, skip=skip, limit=size, name=name)
        
        result = []
        for author in authors:
            author_data = utils.sqlalchemy_to_dict(author)
            author_data['books_count'] = len(author.books) if hasattr(author, 'books') else 0
            
            if fields:
                from app.schemas import FieldSelector
                author_data = utils.FieldSelector.filter_response(author_data, fields)
            
            result.append(author_data)
        
        return {
            "data": result,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    
    def handle_get_author(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Получить автора по ID"""
        author_id = data.get('id')
        author = crud.get_author(db, author_id)
        
        if not author:
            raise ValueError("Author not found")
        
        author_data = utils.sqlalchemy_to_dict(author)
        if fields:
            from app.schemas import FieldSelector
            author_data = utils.FieldSelector.filter_response(author_data, fields)

        
        
        
        return {"data": author_data}
    
    def handle_create_author(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Создать нового автора"""
        from app.schemas import AuthorCreateV1
        
        author_create = AuthorCreateV1(**data)
        author = crud.create_author(db, author_create)
        
        author_data = utils.sqlalchemy_to_dict(author)
        author_data['books'] = 0
        
        
        if fields:
            from app.schemas import FieldSelector
            author_data = utils.FieldSelector.filter_response(author_data, fields)
        
        
        return {"data": author_data}
    
    def handle_get_books(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Получить список книг"""
        page = data.get('page', 1)
        size = data.get('size', 100)
        title = data.get('title')
        author_id = data.get('author_id')
        is_available = data.get('is_available')
        
        # Для v1 игнорируем is_available
        if version == 'v1':
            is_available = None
        
        skip = (page - 1) * size
        
        books, total = crud.get_books(db, skip=skip, limit=size,
                                     title=title, author_id=author_id,
                                     is_available=is_available)
        
        result = []
        for book in books:
            book_data = utils.sqlalchemy_to_dict(book)
            
            if hasattr(book, 'author') and book.author:
                book_data['author'] = utils.sqlalchemy_to_dict(book.author)
                book_data['author']['books_count'] = len(book.author.books) if hasattr(book.author, 'books') else 0
            
            if fields:
                from app.schemas import FieldSelector
                book_data = utils.FieldSelector.filter_response(book_data, fields)
            result.append(book_data)
        
        return {
            "data": result,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    
    def handle_get_book(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Получить книгу по ID"""
        book_id = data.get('id')
        
        if version == 'v2':
            book = crud.get_book_v2(db, book_id)
        else:
            book = crud.get_book(db, book_id)
        
        if not book:
            raise ValueError("Book not found")
        
        book_data = utils.sqlalchemy_to_dict(book)
        
        if hasattr(book, 'author') and book.author:
            book_data['author'] = utils.sqlalchemy_to_dict(book.author)
            book_data['author']['books_count'] = len(book.author.books) if hasattr(book.author, 'books') else 0
        
        if fields:
            from app.schemas import FieldSelector
            book_data = utils.FieldSelector.filter_response(book_data, fields)
        
        return {"data": book_data}
    
    def handle_create_book(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Создать новую книгу"""
        from app.schemas import BookCreateV1, BookCreateV2
        
        # Проверяем существование автора
        author = crud.get_author(db, data.get('author_id'))
        if not author:
            raise ValueError("Author not found")
        
        if version == 'v2':
            book_create = BookCreateV2(**data)
            book = crud.create_book_v2(db, book_create)
        else:
            book_create = BookCreateV1(**data)
            book = crud.create_book(db, book_create)
        
        book_data = utils.sqlalchemy_to_dict(book)
        
        if hasattr(book, 'author') and book.author:
            book_data['author'] = utils.sqlalchemy_to_dict(book.author)
            book_data['author']['books_count'] = len(book.author.books) if hasattr(book.author, 'books') else 0
        
        if fields:
            from app.schemas import FieldSelector
            book_data = utils.FieldSelector.filter_response(book_data, fields)
        
        return {"data": book_data}
    
    def handle_update_book_availability(self, db: Session, data: Dict[str, Any], version: str, fields: str = None):
        """Обновить доступность книги (только v2)"""
        if version != 'v2':
            raise ValueError("This action is only available in v2")
        
        book_id = data.get('id')
        is_available = data.get('is_available')
        
        if is_available is None:
            raise ValueError("is_available is required")
        
        book = crud.get_book(db, book_id)
        if not book:
            raise ValueError("Book not found")
        
        book.is_available = is_available
        db.commit()
        db.refresh(book)
        
        book_data = utils.sqlalchemy_to_dict(book)
        
        if fields:
            from app.schemas import FieldSelector
            book_data = utils.FieldSelector.filter_response(book_data, fields)
        
        return {"data": book_data}
    
    def start(self):
        """Запустить сервер"""
        logger.info("Starting RabbitMQ server...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping server...")
        except Exception as e:
            logger.error(f"Error in server: {e}")
        finally:
            self.close()
    
    def close(self):
        """Закрыть соединение"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")