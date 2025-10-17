"""
Base Agent
Clase base abstracta para todos los agentes de análisis
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import AnalysisResult
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseAgent(ABC):
    """
    Clase base para agentes de análisis
    """
    
    def __init__(self, session: Session, version: str = "1.0.0"):
        """
        Initialize agent
        
        Args:
            session: Sesión de SQLAlchemy
            version: Versión del agente
        """
        self.session = session
        self.version = version
        self.agent_name = self.__class__.__name__.replace('Agent', '').lower()
    
    @abstractmethod
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis
        
        Args:
            categoria_id: ID de la categoría
            periodo: Periodo en formato YYYY-MM
        
        Returns:
            Dict con resultados del análisis
        """
        pass
    
    def save_results(
        self,
        categoria_id: int,
        periodo: str,
        resultado: Dict[str, Any]
    ) -> int:
        """
        Guarda los resultados del análisis en la base de datos
        
        Args:
            categoria_id: ID de la categoría
            periodo: Periodo
            resultado: Dict con resultados
        
        Returns:
            ID del AnalysisResult creado
        """
        # Verificar si ya existe un análisis para este periodo/agente
        existing = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=self.agent_name
        ).first()
        
        if existing:
            # Actualizar existente
            existing.resultado = resultado
            existing.timestamp = datetime.utcnow()
            existing.version_agente = self.version
            self.session.flush()
            analysis_id = existing.id
        else:
            # Crear nuevo
            analysis = AnalysisResult(
                categoria_id=categoria_id,
                periodo=periodo,
                agente=self.agent_name,
                resultado=resultado,
                timestamp=datetime.utcnow(),
                version_agente=self.version
            )
            self.session.add(analysis)
            self.session.flush()
            analysis_id = analysis.id
        
        self.session.commit()
        
        logger.info(
            "analysis_saved",
            agent=self.agent_name,
            categoria_id=categoria_id,
            periodo=periodo,
            analysis_id=analysis_id
        )
        
        return analysis_id
    
    def get_previous_analysis(
        self,
        categoria_id: int,
        periodo: str
    ) -> Dict[str, Any]:
        """
        Obtiene análisis previo del mismo agente (si existe)
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo actual
        
        Returns:
            Dict con resultados o None
        """
        # TODO: Implementar lógica para obtener periodo anterior
        previous = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            agente=self.agent_name
        ).filter(
            AnalysisResult.periodo < periodo
        ).order_by(
            AnalysisResult.periodo.desc()
        ).first()
        
        if previous:
            return previous.resultado
        
        return None

