#!/usr/bin/env python3
"""
Сервер для обработки сообщений через RabbitMQ
"""

import logging
import time
from app.rabbitmq_server import RabbitMQServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Запуск сервера RabbitMQ"""
    logger.info("Starting Library Management API RabbitMQ Server")
    
    # Несколько попыток подключения к RabbitMQ
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            server = RabbitMQServer(
                host='rabbitmq',
                port=5672,
                username='admin',
                password='admin123'
            )
            server.start()
            break
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_attempts}: Failed to start server: {e}")
            if attempt < max_attempts - 1:
                wait_time = (attempt + 1) * 2
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("Max retry attempts reached. Exiting.")
                raise

if __name__ == "__main__":
    main()