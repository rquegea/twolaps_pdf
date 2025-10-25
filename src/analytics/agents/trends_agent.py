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
                    # NUEVO: tendencias intra-rango (primer día vs último día)
                    try:
                        for marca, serie in intra_range.items():
                            if not serie or len(serie) < 2:
                                continue
                            start_val = float(serie[0].get('sov', 0) or 0.0)
                            end_val = float(serie[-1].get('sov', 0) or 0.0)
                            delta = end_val - start_val
                            rel = ((delta / start_val) * 100.0) if start_val > 0 else 0.0
                            if abs(delta) >= 2.0 or abs(rel) >= 8.0:
                                tendencias.append({
                                    'marca': marca,
                                    'metrica': 'SOV',
                                    'cambio_puntos': round(delta, 2),
                                    'cambio_rel_pct': round(rel, 1),
                                    'periodo_inicio': serie[0].get('periodo'),
                                    'periodo_fin': serie[-1].get('periodo'),
                                    'direccion': '↑' if delta > 0 else '↓',
                                    'significancia': 'alta' if abs(delta) >= 4.0 or abs(rel) >= 16.0 else 'media'
                                })
                    except Exception:
                        pass
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
                current_val = float(current_sov.get(marca, 0) or 0)
                previous_val = float(previous_sov.get(marca, 0) or 0)

                cambio = current_val - previous_val
                rel = 0.0
                if previous_val > 0:
                    rel = (cambio / previous_val) * 100.0

                # Más sensible: 3 pp absolutos o 10% relativo
                if abs(cambio) >= 3.0 or abs(rel) >= 10.0:
                    tendencias.append({
                        'marca': marca,
                        'metrica': 'SOV',
                        'cambio_puntos': round(cambio, 2),
                        'cambio_rel_pct': round(rel, 1),
                        'direccion': '↑' if cambio > 0 else '↓',
                        'significancia': 'alta' if abs(cambio) >= 6.0 or abs(rel) >= 20.0 else 'media'
                    })

        # ===== Enriquecer con detección de picos (último valor vs historial) y posibles drivers =====
        def _detect_peak(serie_vals: list[float]) -> bool:
            try:
                if not serie_vals or len(serie_vals) < 3:
                    return False
                last = float(serie_vals[-1])
                base = [float(v) for v in serie_vals[:-1] if v is not None]
                if not base:
                    return False
                base_mean = sum(base) / len(base)
                # Pico si supera en >= 30% al promedio previo o en >= 4 pp absolutos
                return (last - base_mean) >= 4.0 or (base_mean > 0 and (last - base_mean) / base_mean >= 0.30)
            except Exception:
                return False

        # Mapear series por marca para picos (prefiere multi-periodo; si no, intra-range)
        series_por_marca: dict[str, list[float]] = {}
        if sov_trend_data:
            for marca, puntos in sov_trend_data.items():
                try:
                    series_por_marca[marca] = [float(p.get('sov', 0) or 0.0) for p in puntos]
                except Exception:
                    pass
        elif 'sov_percent' in current_quantitative:
            # Solo snapshot, sin picos
            series_por_marca = {}

        # Posibles drivers desde otros agentes (SOLO del periodo solicitado; sin fallback mensual para evitar ruido)
        campaign_data = self._get_analysis('campaign_analysis', categoria_id, periodo) or {}
        channel_data = self._get_analysis('channel_analysis', categoria_id, periodo) or {}
        qual_now = self._get_analysis('qualitative', categoria_id, periodo) or self._get_analysis('qualitativeextraction', categoria_id, periodo) or {}
        sent_now = qual_now.get('sentimiento_por_marca', {}) or {}

        def _drivers_para_marca(marca: str) -> list[str]:
            drivers: list[str] = []
            # Campañas
            try:
                camps = campaign_data.get('campanas_especificas') or []
                hit_camps = [c for c in camps if isinstance(c, dict) and c.get('marca') == marca]
                if hit_camps:
                    nombres = [c.get('nombre_campana') or c.get('mensaje_central') for c in hit_camps if c]
                    if nombres:
                        drivers.append(f"campañas: {', '.join([str(n) for n in nombres if n])[:80]}")
                elif campaign_data.get('marca_mas_activa') and marca in str(campaign_data.get('marca_mas_activa')):
                    drivers.append("campañas: marca destacada en actividad")
            except Exception:
                pass
            # Canales
            try:
                disp = channel_data.get('disponibilidad_por_marca') or []
                hits = [d for d in disp if isinstance(d, dict) and d.get('marca') == marca]
                if hits:
                    canales = hits[0].get('canales_presencia') or []
                    drivers.append(f"canales: presencia en {', '.join(canales)[:50]}")
                elif channel_data.get('marca_mejor_distribuida') and marca in str(channel_data.get('marca_mejor_distribuida')):
                    drivers.append("canales: mejor distribución")
            except Exception:
                pass
            # Sentimiento
            try:
                s = sent_now.get(marca)
                score = None
                if isinstance(s, dict):
                    score = s.get('score_medio') or s.get('score')
                elif isinstance(s, (int, float)):
                    score = float(s)
                if score is not None:
                    drivers.append(f"sentimiento: {float(score):+0.2f}")
            except Exception:
                pass
            return drivers

        # Enriquecer elementos existentes y marcar picos
        for t in tendencias:
            marca = t.get('marca')
            if not marca:
                continue
            serie_vals = series_por_marca.get(marca) or []
            t['pico'] = _detect_peak(serie_vals)
            # Añadir muestras (nº puntos en serie)
            try:
                t['muestras'] = len(sov_trend_data.get(marca, []) or [])
            except Exception:
                pass
            drv = _drivers_para_marca(marca)
            if drv:
                t['posibles_drivers'] = drv
            # Estimar driver_confidence
            try:
                delta = abs(float(t.get('cambio_puntos', 0) or 0.0))
                rel = abs(float(t.get('cambio_rel_pct', 0) or 0.0))
                score = 0.0
                # Magnitud
                if delta >= 6.0 or rel >= 20.0:
                    score += 0.5
                elif delta >= 3.0 or rel >= 10.0:
                    score += 0.35
                # Evidencias externas
                evid = 0
                if drv:
                    for d in drv:
                        if d.startswith('campañas:'):
                            evid += 1
                        if d.startswith('canales:'):
                            evid += 1
                        if d.startswith('sentimiento:'):
                            evid += 1
                score += min(evid * 0.15, 0.45)
                conf = 'alta' if score >= 0.75 else ('media' if score >= 0.5 else 'baja')
                t['driver_confidence'] = conf
            except Exception:
                pass

        # Gating: filtrar tendencias poco significativas y sin drivers
        filtered_tendencias = []
        for t in tendencias:
            try:
                abs_pp = abs(float(t.get('cambio_puntos', 0) or 0.0))
                abs_rel = abs(float(t.get('cambio_rel_pct', 0) or 0.0))
                has_driver = bool(t.get('posibles_drivers'))
                if (abs_pp >= 2.0 or abs_rel >= 8.0) and has_driver:
                    filtered_tendencias.append(t)
            except Exception:
                # Si no podemos evaluar, omitimos la tendencia
                continue
        tendencias = filtered_tendencias
        
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'periodo_comparado': previous_periodo,
            'tendencias': tendencias,
            'resumen': self._generate_summary(tendencias),
            # Series temporales para gráficos
            'sov_trend_data': sov_trend_data,
            'sentiment_trend_data': sentiment_trend_data,
            'metadata': {
                'serie_fuente': 'intra_range' if ('..' in (periodo or '')) else 'historical',
            }
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

