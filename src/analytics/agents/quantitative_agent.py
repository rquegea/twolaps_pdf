"""
Quantitative Agent
Análisis cuantitativo: SOV, menciones, co-ocurrencias
"""

from typing import Dict, Any, List
from collections import defaultdict
from sqlalchemy import func
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
        # Parsear periodo a ventana temporal [inicio, fin)
        start, end, _ = self._parse_periodo(periodo)
        
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
            QueryExecution.timestamp >= start,
            QueryExecution.timestamp < end
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
        
        # 7. Outliers (alto/bajo SOV y cambios bruscos vs periodo anterior si existe)
        outliers = {
            'sov_altos': [],
            'sov_bajos': [],
            'cambios_bruscos': []
        }
        try:
            values = list(sov.values())
            if values:
                mean_val = sum(values) / len(values)
                # Umbrales simples: ±1.5x de la media
                high_thr = mean_val * 1.5
                low_thr = mean_val * 0.5
                for marca, val in sov.items():
                    if val >= high_thr:
                        outliers['sov_altos'].append({'marca': marca, 'sov': val, 'umbral': high_thr, 'razon': '>= 1.5x media'})
                    elif val <= low_thr:
                        outliers['sov_bajos'].append({'marca': marca, 'sov': val, 'umbral': low_thr, 'razon': '<= 0.5x media'})
        except Exception:
            pass

        # Cambios bruscos: comparar con periodo anterior
        try:
            prev_period = self._get_previous_periodo_generic(periodo)
            if prev_period:
                prev_quant = self._get_analysis('quantitative', categoria_id, prev_period) or {}
                prev_sov = prev_quant.get('sov_percent', {}) or {}
                for marca, curr in sov.items():
                    prev = float(prev_sov.get(marca, 0) or 0)
                    delta = curr - prev
                    if abs(delta) >= 5.0:  # cambio significativo en puntos
                        outliers['cambios_bruscos'].append({
                            'marca': marca,
                            'sov_actual': curr,
                            'sov_anterior': prev,
                            'cambio_puntos': round(delta, 2),
                            'periodo_anterior': prev_period,
                            'razon': '>= 5 pp vs periodo anterior'
                        })
        except Exception:
            pass

        # 9. Métricas de concentración (HHI)
        def _compute_hhi(sov_map: Dict[str, float]) -> Dict[str, float]:
            try:
                shares = list(sov_map.values())
                hhi = sum((s)**2 for s in shares)  # shares en % ⇒ HHI en 0..10000
                # Normalización 0..1 (dividir entre 10000)
                hhi_norm = hhi / 10000.0
                return {'hhi': round(hhi, 2), 'hhi_normalized': round(hhi_norm, 4)}
            except Exception:
                return {'hhi': 0.0, 'hhi_normalized': 0.0}

        concentration = _compute_hhi(sov)

        # 10. Share shift por marca vs periodo anterior (pp y % relativo)
        share_shift: List[Dict[str, Any]] = []
        try:
            prev_period = self._get_previous_periodo_generic(periodo)
            if prev_period:
                prev_quant = self._get_analysis('quantitative', categoria_id, prev_period) or {}
                prev_sov = prev_quant.get('sov_percent', {}) or {}
                for marca, curr in sov.items():
                    prev = float(prev_sov.get(marca, 0) or 0)
                    delta = curr - prev
                    rel = ((delta / prev) * 100.0) if prev > 0 else 0.0
                    share_shift.append({
                        'marca': marca,
                        'delta_pp': round(delta, 2),
                        'delta_rel_pct': round(rel, 1),
                        'periodo_anterior': prev_period
                    })
                # ordenar por magnitud absoluta
                share_shift = sorted(share_shift, key=lambda x: abs(x.get('delta_pp', 0.0)), reverse=True)
        except Exception:
            share_shift = []

        # 11. Series base para Trends (últimos 6 periodos)
        sov_trend_data: Dict[str, List[Dict[str, Any]]] = {}
        try:
            periods = self._get_last_periods_generic(periodo, n=6)
            for p in periods:
                q_prev = self._get_analysis('quantitative', categoria_id, p) or {}
                sov_p = q_prev.get('sov_percent', {}) or {}
                for marca, val in sov_p.items():
                    sov_trend_data.setdefault(marca, []).append({'periodo': p, 'sov': float(val)})
        except Exception:
            sov_trend_data = {}

        # 12. Serie intra-rango por día si el periodo es un rango
        sov_by_day: Dict[str, List[Dict[str, Any]]] = {}
        try:
            _, _, gran = self._parse_periodo(periodo)
            if gran == 'range':
                # Construir por día usando las mismas ejecuciones
                # Mapear aliases por marca
                alias_map = {m.nombre: [a.lower() for a in (m.aliases or [])] for m in marcas}
                from datetime import timedelta
                days = []
                cur = start
                while cur < end:
                    days.append(cur.date().isoformat())
                    cur += timedelta(days=1)
                # Contar por día
                by_day_counts: Dict[str, Dict[str, int]] = {d: {k: 0 for k in alias_map.keys()} for d in days}
                for e in executions:
                    d = e.timestamp.date().isoformat()
                    if d not in by_day_counts:
                        continue
                    text = (e.respuesta_texto or '').lower()
                    for marca, aliases in alias_map.items():
                        if any(a in text for a in aliases):
                            by_day_counts[d][marca] += 1
                # Convertir a SOV por día
                sov_by_day = {m: [] for m in alias_map.keys()}
                for d in days:
                    counts = by_day_counts.get(d, {})
                    total = sum(counts.values())
                    for marca in alias_map.keys():
                        val = (counts.get(marca, 0) / total * 100.0) if total else 0.0
                        sov_by_day[marca].append({'periodo': d, 'sov': float(val)})
                sov_by_day = {m: v for m, v in sov_by_day.items() if any(pt['sov'] > 0 for pt in v)}
        except Exception:
            sov_by_day = {}

        # 8. Preparar resultado
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
            'outliers': outliers,
            'concentration': {
                'num_brands': len(sov),
                **concentration,
            },
            'share_shift': share_shift,
            'sov_trend_data': sov_trend_data,
            'sov_by_day': sov_by_day,
            'metadata': {
                'queries_analizadas': len(set(e.query_id for e in executions)),
                'proveedores': list(set(e.proveedor_ia for e in executions)),
                'fecha_analisis': None
            }
        }
        
        # Guardar resultados
        self.save_results(categoria_id, periodo, resultado)
        
        return resultado

