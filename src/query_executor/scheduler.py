"""
Scheduler
Lógica para determinar qué queries ejecutar según frecuencia
"""

from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from src.database.models import Query


class QueryScheduler:
    """
    Determina qué queries deben ejecutarse según su frecuencia
    """
    
    # Mapeo de frecuencias a días
    FREQUENCY_DAYS = {
        'daily': 1,
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 90
    }
    
    def __init__(self, session: Session):
        """
        Initialize scheduler
        
        Args:
            session: Sesión de SQLAlchemy
        """
        self.session = session
    
    def get_queries_to_execute(self, categoria_id: int = None) -> List[Query]:
        """
        Obtiene queries que deben ejecutarse ahora
        
        Args:
            categoria_id: Si se especifica, filtra por categoría
        
        Returns:
            Lista de queries a ejecutar
        """
        now = datetime.utcnow()
        queries_to_execute = []
        
        # Filtro base: queries activas
        query_filter = {'activa': True}
        if categoria_id:
            query_filter['categoria_id'] = categoria_id
        
        queries = self.session.query(Query).filter_by(**query_filter).all()
        
        for query in queries:
            if self.should_execute(query, now):
                queries_to_execute.append(query)
        
        return queries_to_execute
    
    def should_execute(self, query: Query, current_time: datetime = None) -> bool:
        """
        Determina si una query debe ejecutarse
        
        Args:
            query: Query a evaluar
            current_time: Tiempo actual (default: now)
        
        Returns:
            True si debe ejecutarse
        """
        if not query.activa:
            return False
        
        current_time = current_time or datetime.utcnow()
        
        # Si nunca se ha ejecutado, ejecutar ahora
        if query.ultima_ejecucion is None:
            return True
        
        # Calcular cuándo debe ejecutarse la siguiente vez
        frequency_days = self.FREQUENCY_DAYS.get(query.frecuencia, 7)
        next_execution = query.ultima_ejecucion + timedelta(days=frequency_days)
        
        return current_time >= next_execution
    
    def get_next_execution_time(self, query: Query) -> datetime:
        """
        Calcula cuándo se ejecutará la próxima vez
        
        Args:
            query: Query
        
        Returns:
            Timestamp de próxima ejecución
        """
        if query.ultima_ejecucion is None:
            return datetime.utcnow()
        
        frequency_days = self.FREQUENCY_DAYS.get(query.frecuencia, 7)
        return query.ultima_ejecucion + timedelta(days=frequency_days)
    
    def get_queries_by_frequency(self, frequency: str) -> List[Query]:
        """
        Obtiene queries activas de una frecuencia específica
        
        Args:
            frequency: Frecuencia (daily, weekly, etc.)
        
        Returns:
            Lista de queries
        """
        return self.session.query(Query).filter_by(
            activa=True,
            frecuencia=frequency
        ).all()
    
    def get_overdue_queries(self) -> List[Query]:
        """
        Obtiene queries que deberían haberse ejecutado pero no se hizo
        
        Returns:
            Lista de queries atrasadas
        """
        now = datetime.utcnow()
        all_active = self.session.query(Query).filter_by(activa=True).all()
        
        overdue = []
        for query in all_active:
            if query.ultima_ejecucion:
                next_exec = self.get_next_execution_time(query)
                # Si la próxima ejecución era hace más de 1 día
                if next_exec < (now - timedelta(days=1)):
                    overdue.append(query)
        
        return overdue

