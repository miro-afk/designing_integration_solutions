import pika
import json
import uuid
import time
import logging
from typing import Optional, Dict, Any
from queue import Queue, Empty
import threading
from datetime import datetime
from threading import Thread, Lock
from pydantic import ValidationError

from app.schemas_rabbitmq import RequestMessage, ResponseMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RabbitMQClient:
    """
    Потокобезопасный клиент RabbitMQ с отдельным соединением на поток
    """
    def __init__(self, host='rabbitmq', port=5672, username='admin', password='admin123'):
        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(username, password)
        self._thread_local = threading.local()
    
    def _get_connection(self):
        """Получить соединение для текущего потока"""
        if not hasattr(self._thread_local, 'connection'):
            self._thread_local.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
        return self._thread_local.connection
    
    def _get_channel(self):
        """Получить канал для текущего потока"""
        if not hasattr(self._thread_local, 'channel'):
            conn = self._get_connection()
            self._thread_local.channel = conn.channel()
            
            # Объявляем очереди
            self._thread_local.channel.queue_declare(queue='api.requests', durable=True)
            self._thread_local.channel.queue_declare(queue='api.responses', durable=True)
        
        return self._thread_local.channel
    
    def send_request(self, request: RequestMessage, timeout: int = 30) -> Optional[ResponseMessage]:
        """
        Отправить запрос и дождаться ответа (синхронно, без потоков)
        """
        try:
            # Получаем канал
            channel = self._get_channel()
            
            # Создаем временную очередь для ответа
            result = channel.queue_declare(queue='', exclusive=True, durable=False)
            reply_queue = result.method.queue
            
            # Генерируем correlation_id
            correlation_id = str(uuid.uuid4())
            
            # Подготавливаем запрос
            request.correlation_id = correlation_id
            request.reply_to = reply_queue
            
            # Создаем очередь для хранения ответа
            response_queue = Queue(maxsize=1)
            
            # Определяем callback для ответа
            def on_response(ch, method, props, body):
                if correlation_id == props.correlation_id:
                    try:
                        response_data = json.loads(body.decode('utf-8'))
                        response = ResponseMessage(**response_data)
                        response_queue.put(response)
                    except Exception as e:
                        logger.error(f"Error parsing response: {e}")
                        response_queue.put(None)
            
            # Подписываемся на очередь ответов
            channel.basic_consume(
                queue=reply_queue,
                on_message_callback=on_response,
                auto_ack=True
            )
            request_dict = request.dict()
            request_body = json.dumps(request_dict, cls=DateTimeEncoder, ensure_ascii=False)
            encoded_body = request_body.encode('utf-8', errors='replace')
            # Отправляем запрос
            channel.basic_publish(
                exchange='',
                routing_key='api.requests',
                body=encoded_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    correlation_id=correlation_id,
                    reply_to=reply_queue,
                    content_type='application/json',
                    content_encoding='utf-8',
                    expiration=str(timeout * 1000)
                )
            )
            
            logger.info(f"Sent request {request.id} with correlation_id {correlation_id}")
            
            # Ждем ответ с таймаутом
            try:
                # Обрабатываем сообщения в течение таймаута
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Обрабатываем одно сообщение
                    channel.connection.process_data_events(time_limit=0.1)
                    
                    # Проверяем, не пришел ли ответ
                    try:
                        response = response_queue.get_nowait()
                        if response:
                            return response
                    except Empty:
                        continue
                
                logger.warning(f"Timeout waiting for response to {correlation_id}")
                return None
                
            finally:
                # Очищаем временную очередь
                try:
                    channel.queue_delete(reply_queue)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            # Закрываем соединение при ошибке
            self.close()
            return None
    
    def close(self):
        """Закрыть соединение для текущего потока"""
        try:
            if hasattr(self._thread_local, 'connection'):
                self._thread_local.connection.close()
                del self._thread_local.connection
            if hasattr(self._thread_local, 'channel'):
                del self._thread_local.channel
        except:
            pass