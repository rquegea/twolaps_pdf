"""
Quantitative Agent
Análisis cuantitativo: SOV, menciones, co-ocurrencias
"""

from typing import Dict, Any
from collections import defaultdict
from sqlalchemy import func, extract
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import Query, QueryExecution, Marca


class QuantitativeAgent(BaseAgent):
    """
    Agente de análisis cuantitativo
    Calcula métricas numéricas sin usar LLM
    """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis cuantitativo
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con SOV, menciones y co-ocurrencias
        """
        year, month = map(int, periodo.split('-'))
        
        # 1. Obtener marcas de la categoría
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas para esta categoría'}
        
        # 2. Obtener ejecuciones del periodo
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            extract('month', QueryExecution.timestamp) == month,
            extract('year', QueryExecution.timestamp) == year
        ).all()
        
        if not executions:
            return {'error': 'No hay datos de queries para este periodo'}
        
        # 3. Contar menciones por marca
        menciones_por_marca = defaultdict(int)
        textos_por_marca = defaultdict(list)
        
        for marca in marcas:
            for execution in executions:
                texto_lower = execution.respuesta_texto.lower()
                
                # Buscar aliases
                for alias in marca.aliases:
                    if alias.lower() in texto_lower:
                        menciones_por_marca[marca.nombre] += 1
                        textos_por_marca[marca.nombre].append({
                            'query_id': execution.query_id,
                            'provider': execution.proveedor_ia,
                            'timestamp': execution.timestamp.isoformat()
                        })
                        break  # Solo contar una vez por ejecución
        
        # 4. Calcular SOV (Share of Voice)
        total_menciones = sum(menciones_por_marca.values())
        
        if total_menciones == 0:
            return {
                'error': 'No se encontraron menciones de marcas en el periodo',
                'total_executions': len(executions)
            }
        
        sov = {
            marca: (count / total_menciones * 100)
            for marca, count in menciones_por_marca.items()
        }
        
        # 5. Co-ocurrencias (marcas mencionadas juntas)
        co_ocurrencias = defaultdict(int)
        
        for execution in executions:
            texto_lower = execution.respuesta_texto.lower()
            marcas_en_texto = []
            
            for marca in marcas:
                for alias in marca.aliases:
                    if alias.lower() in texto_lower:
                        marcas_en_texto.append(marca.nombre)
                        break
            
            # Contar pares de marcas
            marcas_en_texto = list(set(marcas_en_texto))  # Eliminar duplicados
            for i, marca1 in enumerate(marcas_en_texto):
                for marca2 in marcas_en_texto[i+1:]:
                    pair = tuple(sorted([marca1, marca2]))
                    co_ocurrencias[f"{pair[0]} + {pair[1]}"] += 1
        
        # 6. Ranking de marcas
        ranking = sorted(
            menciones_por_marca.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 7. Preparar resultado
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'total_menciones': total_menciones,
            'total_executions': len(executions),
            'num_marcas_mencionadas': len(menciones_por_marca),
            'menciones_por_marca': dict(menciones_por_marca),
            'sov_percent': sov,
            'ranking': [
                {'marca': marca, 'menciones': count, 'sov': sov[marca]}
                for marca, count in ranking
            ],
            'co_ocurrencias': dict(co_ocurrencias),
            'metadata': {
                'queries_analizadas': len(set(e.query_id for e in executions)),
                'proveedores': list(set(e.proveedor_ia for e in executions)),
                'fecha_analisis': func.now().isoformat() if hasattr(func.now(), 'isoformat') else None
            }
        }
        
        # Guardar resultados
        self.save_results(categoria_id, periodo, resultado)
        
        return resultado

