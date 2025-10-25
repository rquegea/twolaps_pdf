"""
Trends Agent
Detección de tendencias y cambios temporales
"""

from typing import Dict, Any, List
from datetime import timedelta
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult, Query, QueryExecution, Marca


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
        
        # Obtener análisis anterior y construir series de 6 periodos (granularidad dinámica)
        previous_periodo = self._get_previous_periodo_generic(periodo)
        previous_quantitative = self._get_analysis('quantitative', categoria_id, previous_periodo) if previous_periodo else None
        
        tendencias = []

        # Construcción de series temporales (últimos 6 periodos) según granularidad
        periodos_hist = self._get_last_periods_generic(periodo, n=6)
        sov_trend_data: Dict[str, List[Dict[str, Any]]] = {}
        sentiment_trend_data: Dict[str, List[Dict[str, Any]]] = {}

        # Recopilar quantitative y qualitative/sentiment por cada periodo
        for p in periodos_hist:
            q = self._get_analysis('quantitative', categoria_id, p) or {}
            s = self._get_analysis('qualitative', categoria_id, p) or self._get_analysis('qualitativeextraction', categoria_id, p) or {}

            sov_p = q.get('sov_percent', {}) or {}
            sent_p = s.get('sentimiento_por_marca', {}) or {}

            # Agregar SOV por marca
            for marca, val in sov_p.items():
                sov_trend_data.setdefault(marca, []).append({'periodo': p, 'sov': float(val)})

            # Agregar sentimiento medio por marca
            for marca, data in sent_p.items():
                score = None
                if isinstance(data, dict):
                    score = data.get('score_medio') or data.get('score')
                elif isinstance(data, (int, float)):
                    score = float(data)
                if score is not None:
                    sentiment_trend_data.setdefault(marca, []).append({'periodo': p, 'score': float(score)})
        
        # Si estamos en una semana y solo tenemos el snapshot del periodo actual,
        # construimos una serie intra-semana (por días) a partir de QueryExecution
        try:
            _, _, gran = self._parse_periodo(periodo)
            if gran == 'weekly':
                intra = self._build_intra_week_sov_series(categoria_id, periodo)
                # Usar la serie diaria solo si aporta al menos 2 puntos en alguna marca
                if isinstance(intra, dict) and any(len(v) >= 2 for v in intra.values()):
                    sov_trend_data = intra
        except Exception:
            # No bloquear el flujo por errores en la serie intra-semana
            pass
        
        # Soporte adicional para periodos de tipo rango (YYYY-MM-DD..YYYY-MM-DD):
        # construir serie diaria SOV y snapshot de sentimiento
        try:
            _, _, gran2 = self._parse_periodo(periodo)
            if gran2 == 'range':
                intra_range = self._build_intra_range_sov_series(categoria_id, periodo)
                if isinstance(intra_range, dict) and any(len(v) >= 2 for v in intra_range.values()):
                    sov_trend_data = intra_range
                # Si no hay serie de sentimiento, usar snapshot del periodo actual
                if not sentiment_trend_data:
                    s_now = self._get_analysis('qualitative', categoria_id, periodo) or \
                            self._get_analysis('qualitativeextraction', categoria_id, periodo) or {}
                    sent_now = s_now.get('sentimiento_por_marca', {}) or {}
                    for marca, data in sent_now.items():
                        score = None
                        if isinstance(data, dict):
                            score = data.get('score_medio') or data.get('score')
                        elif isinstance(data, (int, float)):
                            score = float(data)
                        if score is not None:
                            sentiment_trend_data.setdefault(marca, []).append({'periodo': periodo, 'score': float(score)})
        except Exception:
            pass

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
            'resumen': self._generate_summary(tendencias),
            # Series temporales para gráficos
            'sov_trend_data': sov_trend_data,
            'sentiment_trend_data': sentiment_trend_data
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
    
    # Delegamos en BaseAgent los helpers genéricos de periodos
    
    def _build_intra_range_sov_series(self, categoria_id: int, periodo: str) -> Dict[str, List[Dict[str, Any]]]:
        """Construye serie diaria de SOV dentro de un rango de fechas (YYYY-MM-DD..YYYY-MM-DD)."""
        start, end, gran = self._parse_periodo(periodo)
        if gran != 'range':
            return {}

        # Marcas configuradas en la categoría y sus aliases
        marcas = self.session.query(Marca).filter_by(categoria_id=categoria_id).all()
        alias_map = {m.nombre: [a.lower() for a in (m.aliases or [])] for m in marcas}
        if not alias_map:
            return {}

        # Obtener todas las ejecuciones con texto en la ventana del rango
        executions = self.session.query(QueryExecution).join(Query). \
            filter(
                Query.categoria_id == categoria_id,
                QueryExecution.respuesta_texto.isnot(None),
                QueryExecution.timestamp >= start,
                QueryExecution.timestamp < end
            ).all()

        if not executions:
            return {}

        # Contar menciones por marca por día
        by_day: Dict[str, Dict[str, int]] = {}
        for e in executions:
            d = e.timestamp.date().isoformat()
            text = (e.respuesta_texto or "").lower()
            day_counts = by_day.setdefault(d, dict.fromkeys(alias_map.keys(), 0))
            for marca, aliases in alias_map.items():
                if any(alias in text for alias in aliases):
                    day_counts[marca] += 1

        # Generar lista de días completos del rango [start, end)
        days = []
        cur = start
        while cur < end:
            days.append(cur.date().isoformat())
            cur += timedelta(days=1)

        # Convertir a SOV (%) por día
        series: Dict[str, List[Dict[str, Any]]] = {m: [] for m in alias_map.keys()}
        for d in days:
            counts = by_day.get(d, dict.fromkeys(alias_map.keys(), 0))
            total = sum(counts.values())
            for marca in alias_map.keys():
                val = (counts.get(marca, 0) / total * 100) if total else 0.0
                series[marca].append({'periodo': d, 'sov': float(val)})

        # Eliminar marcas sin valores
        series = {m: vals for m, vals in series.items() if any(p['sov'] > 0 for p in vals)}
        return series

    def _build_intra_week_sov_series(self, categoria_id: int, periodo: str) -> Dict[str, List[Dict[str, Any]]]:
        """Construye serie diaria de SOV dentro de una semana concreta.
        Devuelve {marca: [{periodo: 'YYYY-MM-DD', sov: %}, ...]}.
        """
        start, end, gran = self._parse_periodo(periodo)
        if gran != 'weekly':
            return {}

        # Marcas configuradas en la categoría y sus aliases
        marcas = self.session.query(Marca).filter_by(categoria_id=categoria_id).all()
        alias_map = {m.nombre: [a.lower() for a in (m.aliases or [])] for m in marcas}
        if not alias_map:
            return {}

        # Obtener todas las ejecuciones con texto en la semana
        executions = self.session.query(QueryExecution).join(Query).\
            filter(
                Query.categoria_id == categoria_id,
                QueryExecution.respuesta_texto.isnot(None),
                QueryExecution.timestamp >= start,
                QueryExecution.timestamp < end
            ).all()

        if not executions:
            return {}

        # Contar menciones por marca por día
        by_day: Dict[str, Dict[str, int]] = {}
        for e in executions:
            d = e.timestamp.date().isoformat()
            text = (e.respuesta_texto or "").lower()
            day_counts = by_day.setdefault(d, dict.fromkeys(alias_map.keys(), 0))
            for marca, aliases in alias_map.items():
                if any(alias in text for alias in aliases):
                    day_counts[marca] += 1

        # Generar lista de días completos de la semana [start, end)
        days = []
        cur = start
        while cur < end:
            days.append(cur.date().isoformat())
            cur += timedelta(days=1)

        # Convertir a SOV (%) por día
        series: Dict[str, List[Dict[str, Any]]] = {m: [] for m in alias_map.keys()}
        for d in days:
            counts = by_day.get(d, dict.fromkeys(alias_map.keys(), 0))
            total = sum(counts.values())
            for marca in alias_map.keys():
                val = (counts.get(marca, 0) / total * 100) if total else 0.0
                series[marca].append({'periodo': d, 'sov': float(val)})

        # Eliminar marcas sin ningún valor > 0 para limpiar el gráfico
        series = {m: vals for m, vals in series.items() if any(p['sov'] > 0 for p in vals)}
        return series
    
    def _generate_summary(self, tendencias: list) -> str:
        """Genera resumen de tendencias"""
        if not tendencias:
            return "No se detectaron cambios significativos"
        
        crecimiento = [t for t in tendencias if t['cambio_puntos'] > 0]
        decrecimiento = [t for t in tendencias if t['cambio_puntos'] < 0]
        
        summary = f"{len(crecimiento)} marcas en crecimiento, {len(decrecimiento)} en decrecimiento"
        return summary

