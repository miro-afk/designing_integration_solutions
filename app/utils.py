from typing import List
import app.models as models
import app.schemas as schemas
def sqlalchemy_to_dict(model_instance, exclude: List[str] = None) -> dict:
    """
    Преобразует SQLAlchemy объект в словарь
    """
    if not model_instance:
        return {}
    
    exclude = exclude or []
    result = {}
    
    # Получаем все атрибуты модели
    for key, value in model_instance.__dict__.items():
        # Пропускаем служебные атрибуты SQLAlchemy
        if key.startswith('_'):
            continue
            
        # Пропускаем исключенные поля
        if key in exclude:
            continue
        
        result[key] = value
    
    return result


def filter_model_fields(model_instance, fields: str = None) -> dict:
    """
    Фильтрует поля модели на основе запроса
    """
    if not model_instance:
        return {}
        
    if not fields:
        return model_instance
    
    # Применяем фильтр
    selector = schemas.FieldSelector()
    return selector.filter_response(model_instance, fields)