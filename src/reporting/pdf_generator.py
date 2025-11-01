"""
PDF Generator
Generador de informes PDF a partir de reports en BD
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader
# Import diferido para evitar que la app falle al cargar si faltan libs nativas.
def _load_weasyprint():
    from weasyprint import HTML, CSS
    return HTML, CSS
from src.database.connection import get_session
from src.database.models import Report, Categoria, Mercado
from src.utils.logger import setup_logger, log_report_generation
def _lazy_import_charts():
    # Import diferido para evitar cargar matplotlib al iniciar la app
    from src.reporting.chart_generator import generate_all_charts
    return generate_all_charts
import time

logger = setup_logger(__name__)


class PDFGenerator:
    """
    Genera PDFs profesionales desde reports
    """
    
    def __init__(self):
        self.templates_dir = Path("src/reporting/templates")
        self.output_dir = Path("data/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir))
        )
        
        # Registrar filtros personalizados
        self.env.filters['format_percent'] = self._format_percent
        self.env.filters['format_score'] = self._format_score
    
    def generate(self, report_id: int, output_path: Optional[str] = None, agents_stats: dict = None) -> str:
        """
        Genera PDF desde un report
        
        Args:
            report_id: ID del report
            output_path: Ruta de salida (opcional)
            agents_stats: Estadísticas de agentes ejecutados (opcional)
        
        Returns:
            Ruta del PDF generado
        """
        start_time = time.time()
        
        with get_session() as session:
            # Obtener report
            report = session.query(Report).get(report_id)
            if not report:
                raise ValueError(f"Report {report_id} no encontrado")
            
            # Obtener categoría y mercado
            categoria = session.query(Categoria).get(report.categoria_id)
            mercado = session.query(Mercado).get(categoria.mercado_id)
            
            logger.info(
                "starting_pdf_generation",
                report_id=report_id,
                categoria=f"{mercado.nombre}/{categoria.nombre}",
                periodo=report.periodo
            )
            
            # Enriquecer contenido con resultados de agentes adicionales (pricing_power, customer_journey, scenarios)
            try:
                from src.database.models import AnalysisResult
                extra_agents = ['pricing_power', 'customer_journey', 'scenario_planning']
                contenido = report.contenido or {}
                for agent in extra_agents:
                    if agent not in contenido:
                        res = session.query(AnalysisResult).filter_by(
                            categoria_id=report.categoria_id,
                            periodo=report.periodo,
                            agente=agent
                        ).first()
                        if res and res.resultado:
                            contenido[agent] = res.resultado
                # Actualizar en memoria (no persistimos en BD aquí)
                report.contenido = contenido
            except Exception:
                pass

            # Preparar datos para template
            context = self._prepare_context(report, categoria, mercado)
            
            # Contar gráficos generados
            charts_generated = sum(1 for v in context.get('charts', {}).values() if v is not None)
            
            logger.info(
                "charts_generated",
                report_id=report_id,
                charts_count=charts_generated,
                charts_list=list(context.get('charts', {}).keys())
            )
            
            # Renderizar HTML
            template = self.env.get_template('base_template.html')
            html_content = template.render(**context)
            
            # Determinar ruta de salida
            if not output_path:
                filename = f"{mercado.nombre}_{categoria.nombre}_{report.periodo}.pdf"
                filename = filename.replace('/', '_').replace(' ', '_')
                output_path = self.output_dir / filename
            
            # Generar PDF (import diferido)
            HTML, CSS = _load_weasyprint()
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(filename=str(self.templates_dir / 'styles.css'))]
            )
            
            # Calcular tamaño del PDF
            pdf_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            # Actualizar report con ruta
            report.pdf_path = str(output_path)
            report.estado = 'published'
            session.commit()
            
            # Log detallado
            generation_time = time.time() - start_time
            log_report_generation(
                logger=logger,
                report_id=report_id,
                categoria_id=report.categoria_id,
                categoria_nombre=f"{mercado.nombre}/{categoria.nombre}",
                periodo=report.periodo,
                pdf_path=str(output_path),
                pdf_size_mb=pdf_size_mb,
                generation_time_seconds=generation_time,
                agents_executed=agents_stats.get('agents_executed', {}) if agents_stats else {},
                charts_generated=charts_generated
            )
            
            return str(output_path)
    
    def _prepare_context(self, report: Report, categoria: Categoria, mercado: Mercado) -> dict:
        """Prepara contexto para el template"""
        contenido = report.contenido
        
        # Generar gráficos
        logger.info("Generando visualizaciones...", report_id=report.id)
        # Cargar generador de gráficos de forma perezosa
        generate_all_charts = _lazy_import_charts()
        charts = generate_all_charts(contenido)
        
        return {
            'titulo': f"Análisis Competitivo - {categoria.nombre}",
            'mercado': mercado.nombre,
            'categoria': categoria.nombre,
            'periodo': report.periodo,
            'tipo_mercado': getattr(mercado, 'tipo_mercado', 'FMCG'),
            'fecha_generacion': datetime.now().strftime('%d de %B de %Y'),
            'resumen_ejecutivo': contenido.get('resumen_ejecutivo', {}),
            'mercado_section': contenido.get('mercado', {}),
            'panorama_mercado': contenido.get('panorama_mercado', {}),  # NUEVO narrativo
            'analisis_competitivo': contenido.get('analisis_competitivo', {}),  # NUEVO narrativo
            'competencia': contenido.get('competencia', {}),  # Mantener compatibilidad
            'actividad_marketing': contenido.get('analisis_competitivo', {}).get('actividad_marketing', {}),  # Mantener compatibilidad
            'estrategias_canal': contenido.get('analisis_competitivo', {}).get('estrategias_canal', {}),  # Mantener compatibilidad
            'analisis_campanas': contenido.get('analisis_campanas', {}),  # NUEVO narrativo
            'analisis_canales': contenido.get('analisis_canales', {}),  # NUEVO narrativo
            'analisis_sostenibilidad_packaging': contenido.get('analisis_sostenibilidad_packaging', {}),  # NUEVO narrativo
            'consumidor': contenido.get('consumidor', {}),  # NUEVO narrativo
            'sentimiento': contenido.get('sentimiento_reputacion', {}),  # Mantener compatibilidad
            'sentimiento_reputacion': contenido.get('sentimiento_reputacion', {}),  # NUEVO narrativo
            'oportunidades_riesgos': contenido.get('oportunidades_riesgos', {}),  # NUEVO narrativo
            'plan_90_dias': contenido.get('plan_90_dias', {}),  # NUEVO narrativo
            'buyer_personas': contenido.get('buyer_personas', []) or contenido.get('customer_journey', {}).get('buyer_personas', []),
            # NUEVOS BLOQUES: Escenarios / Customer Journey / Pricing Power
            'scenarios': contenido.get('scenario_planning', {}),
            'customer_journey': contenido.get('customer_journey', {}),
            'pricing_power': contenido.get('pricing_power', {}),
            'metricas_calidad': report.metricas_calidad or {},
            'charts': charts  # Gráficos en base64
        }
    
    def _format_percent(self, value: float) -> str:
        """Filtro para formatear porcentajes"""
        return f"{value:.1f}%"
    
    def _format_score(self, value: float) -> str:
        """Filtro para formatear scores"""
        return f"{value:.2f}"


def generate_pdf(report_id: int, output_path: Optional[str] = None, agents_stats: dict = None) -> str:
    """
    Helper function para generar PDF
    
    Args:
        report_id: ID del report
        output_path: Ruta de salida opcional
        agents_stats: Estadísticas de agentes ejecutados (opcional)
    
    Returns:
        Ruta del PDF generado
    """
    generator = PDFGenerator()
    return generator.generate(report_id, output_path, agents_stats)

