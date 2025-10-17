"""
Trends Agent
Detección de tendencias y cambios temporales
"""

from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult


class TrendsAgent(BaseAgent):
    """
    Agente de detección de tendencias
    Compara periodo actual con anteriores
    """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Detecta tendencias
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con tendencias detectadas
        """
        # Obtener análisis actual
        current_quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        
        if not current_quantitative:
            return {'error': 'No hay análisis cuantitativo para este periodo'}
        
        # Obtener análisis anterior
        previous_periodo = self._get_previous_periodo(periodo)
        previous_quantitative = self._get_analysis('quantitative', categoria_id, previous_periodo) if previous_periodo else None
        
        tendencias = []
        
        if previous_quantitative:
            # Comparar SOV
            current_sov = current_quantitative.get('sov_percent', {})
            previous_sov = previous_quantitative.get('sov_percent', {})
            
            for marca in current_sov.keys():
                current_val = current_sov.get(marca, 0)
                previous_val = previous_sov.get(marca, 0)
                
                cambio = current_val - previous_val
                
                if abs(cambio) > 5:  # Cambio significativo
                    tendencias.append({
                        'marca': marca,
                        'metrica': 'SOV',
                        'cambio_puntos': cambio,
                        'direccion': '↑' if cambio > 0 else '↓',
                        'significancia': 'alta' if abs(cambio) > 10 else 'media'
                    })
        
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'periodo_comparado': previous_periodo,
            'tendencias': tendencias,
            'resumen': self._generate_summary(tendencias)
        }
        
        self.save_results(categoria_id, periodo, resultado)
        return resultado
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}
    
    def _get_previous_periodo(self, periodo: str) -> str:
        """Calcula periodo anterior"""
        year, month = map(int, periodo.split('-'))
        if month == 1:
            return f"{year-1}-12"
        else:
            return f"{year}-{month-1:02d}"
    
    def _generate_summary(self, tendencias: list) -> str:
        """Genera resumen de tendencias"""
        if not tendencias:
            return "No se detectaron cambios significativos"
        
        crecimiento = [t for t in tendencias if t['cambio_puntos'] > 0]
        decrecimiento = [t for t in tendencias if t['cambio_puntos'] < 0]
        
        summary = f"{len(crecimiento)} marcas en crecimiento, {len(decrecimiento)} en decrecimiento"
        return summary

