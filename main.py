#!/usr/bin/env python3
"""
TwoLaps Intelligence Platform - CLI Principal
Punto de entrada del sistema
"""

import click
from src.database.connection import init_db, test_connection
from src.admin.cli import admin
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    TwoLaps Intelligence Platform
    
    Sistema de inteligencia competitiva automatizada que ejecuta queries
    a múltiples IAs, analiza respuestas y genera informes consultivos en PDF.
    """
    pass


@cli.command()
def init():
    """Inicializar base de datos (crear tablas)"""
    click.echo("🚀 Inicializando base de datos...")
    try:
        init_db()
        click.echo("✓ Base de datos inicializada correctamente")
    except Exception as e:
        click.echo(f"✗ Error al inicializar base de datos: {e}", err=True)
        raise click.Abort()


@cli.command()
def test_db():
    """Test de conexión a base de datos"""
    click.echo("🔍 Probando conexión a base de datos...")
    if test_connection():
        click.echo("✓ Conexión exitosa")
    else:
        click.echo("✗ Conexión fallida", err=True)
        raise click.Abort()


@cli.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--all-providers', is_flag=True, help='Ejecutar en todos los proveedores configurados')
@click.option('--provider', '-p', multiple=True, help='Proveedor específico (openai, anthropic, google, perplexity)')
def execute_queries(category, all_providers, provider):
    """
    Ejecutar queries de una categoría manualmente
    
    Ejemplo: python main.py execute-queries -c "FMCG/Cervezas"
    """
    from src.query_executor.poller import execute_category_queries
    
    click.echo(f"📊 Ejecutando queries para: {category}")
    
    try:
        providers = None
        if provider:
            providers = list(provider)
        elif not all_providers:
            # Por defecto usar todos
            all_providers = True
            
        result = execute_category_queries(category, providers=providers)
        
        click.echo(f"\n✓ Ejecución completada:")
        click.echo(f"  - Queries ejecutadas: {result['queries_executed']}")
        click.echo(f"  - Respuestas obtenidas: {result['total_executions']}")
        click.echo(f"  - Coste total: ${result['total_cost']:.4f}")
        
    except Exception as e:
        click.echo(f"✗ Error al ejecutar queries: {e}", err=True)
        logger.error(f"Error en execute_queries: {e}", exc_info=True)
        raise click.Abort()


@cli.command()
@click.option('--interval', default='weekly', help='Intervalo de polling (daily, weekly, monthly)')
@click.option('--once', is_flag=True, help='Ejecutar una sola vez y salir')
def start_poller(interval, once):
    """
    Iniciar poller automático de queries
    
    El poller ejecuta queries activas según su frecuencia configurada.
    Corre indefinidamente a menos que se use --once
    """
    from src.query_executor.poller import start_polling
    
    if once:
        click.echo("📊 Ejecutando polling una vez...")
    else:
        click.echo(f"🤖 Iniciando poller automático (intervalo: {interval})")
        click.echo("   Presiona Ctrl+C para detener")
    
    try:
        start_polling(interval=interval, run_once=once)
    except KeyboardInterrupt:
        click.echo("\n⏹  Poller detenido por el usuario")
    except Exception as e:
        click.echo(f"\n✗ Error en poller: {e}", err=True)
        logger.error(f"Error en start_poller: {e}", exc_info=True)
        raise click.Abort()


@cli.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--period', '-p', required=True, help='Periodo (formato: YYYY-MM)')
@click.option('--output', '-o', help='Ruta de salida del PDF (opcional)')
def generate_report(category, period, output):
    """
    Generar informe consultivo en PDF
    
    Ejemplo: python main.py generate-report -c "FMCG/Cervezas" -p "2025-10"
    """
    from src.analytics.orchestrator import run_analysis
    from src.reporting.pdf_generator import generate_pdf
    
    click.echo(f"📊 Generando informe para: {category} - {period}")
    
    try:
        # 1. Ejecutar análisis multi-agente
        click.echo("🤖 Ejecutando análisis multi-agente...")
        report_id, agents_stats = run_analysis(category, period)
        click.echo(f"  ✓ Análisis completado (report_id: {report_id})")
        click.echo(f"  ✓ Agentes ejecutados: {agents_stats['agents_executed']['successful']}/{agents_stats['agents_executed']['total']}")
        
        # 2. Generar PDF
        click.echo("📄 Generando PDF...")
        pdf_path = generate_pdf(report_id, output_path=output, agents_stats=agents_stats)
        
        click.echo(f"\n✅ Informe generado exitosamente:")
        click.echo(f"  📁 {pdf_path}")
        
    except Exception as e:
        click.echo(f"✗ Error al generar informe: {e}", err=True)
        logger.error(f"Error en generate_report: {e}", exc_info=True)
        raise click.Abort()


@cli.command()
@click.option('--categories', '-c', multiple=True, help='Categorías específicas')
@click.option('--all', 'all_categories', is_flag=True, help='Todas las categorías activas')
@click.option('--period', '-p', required=True, help='Periodo (formato: YYYY-MM)')
def generate_batch(categories, all_categories, period):
    """
    Generar informes en lote para múltiples categorías
    
    Ejemplo: python main.py generate-batch --all -p "2025-10"
    """
    from src.analytics.orchestrator import run_analysis
    from src.reporting.pdf_generator import generate_pdf
    from src.database.connection import get_session
    from src.database.models import Categoria
    
    if not categories and not all_categories:
        click.echo("✗ Debes especificar categorías (-c) o usar --all", err=True)
        raise click.Abort()
    
    # Obtener categorías a procesar
    with get_session() as session:
        if all_categories:
            cats = session.query(Categoria).filter_by(activo=True).all()
            categories_to_process = [(c.mercado.nombre, c.nombre) for c in cats]
        else:
            categories_to_process = [tuple(c.split('/')) for c in categories]
    
    click.echo(f"📊 Generando {len(categories_to_process)} informes para periodo: {period}\n")
    
    results = []
    for mercado, categoria in categories_to_process:
        category_full = f"{mercado}/{categoria}"
        try:
            click.echo(f"🔄 Procesando: {category_full}")
            report_id, agents_stats = run_analysis(category_full, period)
            pdf_path = generate_pdf(report_id, agents_stats=agents_stats)
            results.append({'category': category_full, 'status': 'success', 'path': pdf_path})
            click.echo(f"  ✓ {pdf_path}\n")
        except Exception as e:
            results.append({'category': category_full, 'status': 'error', 'error': str(e)})
            click.echo(f"  ✗ Error: {e}\n")
    
    # Resumen
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    click.echo(f"\n📊 Resumen:")
    click.echo(f"  ✓ Exitosos: {successful}")
    if failed:
        click.echo(f"  ✗ Fallidos: {failed}")


@cli.command()
@click.option('--provider', '-p', multiple=True, help='Proveedor específico (openai, anthropic, google, perplexity). Por defecto usa los de cada query')
@click.option('--market', '-m', help='Limitar a un mercado (opcional)')
def execute_all(provider, market):
    """Ejecutar AHORA todas las queries activas en paralelo (usa max_concurrent_queries)."""
    import yaml
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime
    from src.database.connection import get_session
    from src.database.models import Mercado, Categoria, Query
    from src.query_executor.poller import execute_query

    def _get_max_concurrency(default: int = 12) -> int:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return int((cfg.get("polling") or {}).get("max_concurrent_queries", default))
        except Exception:
            return default

    with get_session() as session:
        # Construir lista de queries activas (opcionalmente por mercado)
        if market:
            mercados = session.query(Mercado).filter_by(nombre=market).all()
            if not mercados:
                click.echo(f"✗ Mercado '{market}' no encontrado", err=True)
                raise click.Abort()
            cats = session.query(Categoria).filter(Categoria.mercado_id.in_([m.id for m in mercados]), Categoria.activo == True).all()
            qlist = session.query(Query).filter(Query.activa == True, Query.categoria_id.in_([c.id for c in cats])).all()
        else:
            qlist = session.query(Query).filter_by(activa=True).all()

        if not qlist:
            click.echo("No hay queries activas")
            return

        # Preparar trabajos (query_id, provider)
        work_items = []
        for q in qlist:
            provs = list(provider) if provider else (q.proveedores_ia or [])
            for prov in provs:
                work_items.append((q.id, prov))

        if not work_items:
            click.echo("No hay ejecuciones para lanzar (sin proveedores)")
            return

        max_workers = _get_max_concurrency()
        click.echo(f"🚀 Lanzando {len(work_items)} ejecuciones con concurrencia={max_workers}")

        stats = {
            'queries_executed': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_cost': 0.0
        }
        total_cost = 0.0
        executed_query_ids = set()

        def _worker(qid: int, prov: str):
            from src.database.connection import get_session
            from src.database.models import Query
            with get_session() as s:
                qi = s.query(Query).get(qid)
                if not qi:
                    return {'success': False, 'error': f'query_not_found:{qid}'}
                return execute_query(qi, prov, s)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_worker, qid, prov): (qid, prov) for (qid, prov) in work_items}
            for fut in as_completed(futures):
                qid, prov = futures[fut]
                executed_query_ids.add(qid)
                try:
                    result = fut.result()
                except Exception as e:
                    result = {'success': False, 'error': str(e)}

                stats['total_executions'] += 1
                if result.get('success'):
                    stats['successful_executions'] += 1
                    total_cost += float(result.get('cost_usd', 0.0) or 0.0)
                else:
                    stats['failed_executions'] += 1

        # Marcar última ejecución de las queries tocadas
        now_ts = datetime.utcnow()
        for qid in executed_query_ids:
            qobj = session.query(Query).get(qid)
            if qobj:
                qobj.ultima_ejecucion = now_ts
        session.commit()

        stats['queries_executed'] = len(executed_query_ids)
        stats['total_cost'] = total_cost

        click.echo("\n✅ Ejecución global completada")
        click.echo(f"  Queries ejecutadas: {stats['queries_executed']}")
        click.echo(f"  Respuestas:        {stats['total_executions']}")
        click.echo(f"  Éxitos:            {stats['successful_executions']}")
        click.echo(f"  Fallos:            {stats['failed_executions']}")
        click.echo(f"  Coste total:       ${stats['total_cost']:.4f}")


# Registrar grupo de comandos admin
cli.add_command(admin)


# =============================
# Preview de agentes en terminal
# =============================
@cli.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--period', '-p', required=True, help='Periodo (YYYY-MM, YYYY-Www o rango YYYY-MM-DD..YYYY-MM-DD)')
@click.option('--agents', '-a', multiple=True, help='Agentes a previsualizar (ej: quantitative, qualitative, competitive, trends, channel_analysis, esg_analysis, packaging_analysis, pricing_power, customer_journey, scenario_planning, roi, strategic)')
@click.option('--run-missing', is_flag=True, help='Ejecuta el agente si no hay resultado previo')
@click.option('--rerun', is_flag=True, help='Fuerza re-ejecución del agente (ignora resultados previos)')
def preview_agents(category, period, agents, run_missing, rerun):
    """Previsualiza en terminal la salida por agente sin generar el PDF."""
    import json
    from src.database.connection import get_session
    from src.database.models import Mercado, Categoria, AnalysisResult
    # Import lazy de agentes para evitar coste cuando solo se lee
    from src.analytics.agents import (
        QuantitativeAgent,
        QualitativeExtractionAgent,
        CompetitiveAgent,
        TrendsAgent,
        CampaignAnalysisAgent,
        ChannelAnalysisAgent,
        ESGAnalysisAgent,
        PackagingAnalysisAgent,
        CustomerJourneyAgent,
        ScenarioPlanningAgent,
        PricingPowerAgent,
        ROIAgent,
        StrategicAgent,
    )

    AGENT_MAP = {
        'quantitative': QuantitativeAgent,
        'qualitative': QualitativeExtractionAgent,  # guardaremos como 'qualitativeextraction'
        'competitive': CompetitiveAgent,
        'trends': TrendsAgent,
        'campaign_analysis': CampaignAnalysisAgent,
        'channel_analysis': ChannelAnalysisAgent,
        'esg_analysis': ESGAnalysisAgent,
        'packaging_analysis': PackagingAnalysisAgent,
        'customer_journey': CustomerJourneyAgent,
        'scenario_planning': ScenarioPlanningAgent,
        'pricing_power': PricingPowerAgent,
        'roi': ROIAgent,
        'strategic': StrategicAgent,
    }

    DEFAULT_ORDER = [
        'quantitative', 'competitive', 'trends', 'channel_analysis', 'campaign_analysis',
        'esg_analysis', 'packaging_analysis', 'pricing_power', 'customer_journey',
        'scenario_planning', 'roi', 'strategic'
    ]

    selected = list(agents) if agents else DEFAULT_ORDER

    # Resolver categoría
    try:
        market_name, cat_name = category.split('/')
    except ValueError:
        click.echo("✗ Formato de categoría inválido. Usa Mercado/Categoría", err=True)
        raise click.Abort()

    with get_session() as session:
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            raise click.Abort()
        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=cat_name).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            raise click.Abort()

        click.echo(f"👀 Preview de agentes | {category} | {period}\n")

        def _load_result(agent_key: str):
            keys = [agent_key]
            # compat: qualitative puede estar como 'qualitative' o 'qualitativeextraction'
            if agent_key == 'qualitative':
                keys = ['qualitative', 'qualitativeextraction']
            for k in keys:
                r = session.query(AnalysisResult).filter_by(
                    categoria_id=categoria.id,
                    periodo=period,
                    agente=k
                ).first()
                if r:
                    return r.resultado
            return None

        def _run_agent(agent_key: str):
            AgentClass = AGENT_MAP.get(agent_key)
            if not AgentClass:
                return {'error': f'agente_desconocido:{agent_key}'}
            agent = AgentClass(session)
            return agent.analyze(categoria.id, period)

        def _ensure_result(agent_key: str):
            if rerun:
                return _run_agent(agent_key)
            existing = _load_result(agent_key)
            if existing:
                return existing
            if run_missing:
                return _run_agent(agent_key)
            return {'info': 'no_data', 'detail': 'No hay resultado previo. Usa --run-missing o --rerun para ejecutarlo.'}

        def _print_quantitative(res: dict):
            click.echo("— Quantitative")
            if 'error' in res:
                click.echo(f"  ✗ {res['error']}")
                return
            ranking = res.get('ranking', [])[:5]
            out = res.get('outliers', {}) or {}
            click.echo("  Top 5 (SOV %):")
            for r in ranking:
                click.echo(f"   · {r['marca']}: {r.get('sov', 0):.1f}% ({r.get('menciones', 0)} menciones)")
            if out:
                highs = ', '.join([f"{x['marca']} ({x['sov']:.1f}%)" for x in out.get('sov_altos', [])])
                lows = ', '.join([f"{x['marca']} ({x['sov']:.1f}%)" for x in out.get('sov_bajos', [])])
                changes = ', '.join([f"{x['marca']} ({x['cambio_puntos']:+.1f} pp)" for x in out.get('cambios_bruscos', [])[:5]])
                if highs:
                    click.echo(f"  Outliers altos: {highs}")
                if lows:
                    click.echo(f"  Outliers bajos: {lows}")
                if changes:
                    click.echo(f"  Cambios bruscos: {changes}")

        def _print_competitive(res: dict):
            click.echo("— Competitive")
            if 'error' in res:
                click.echo(f"  ✗ {res['error']}")
                return
            lider = res.get('lider_mercado') or 'N/A'
            click.echo(f"  Líder de mercado: {lider}")
            insights = res.get('insights', [])
            if insights:
                click.echo("  Insights (primeros 3, con profundidad):")
                for it in insights[:3]:
                    ev = len((it.get('evidencia') or []))
                    kpi = len((it.get('kpis_seguimiento') or []))
                    conf = it.get('confianza', 'N/A')
                    ca = 'sí' if it.get('contraargumento') else 'no'
                    tit = (it.get('titulo','(sin título)') or '')[:90]
                    click.echo(f"   · {tit} | ev:{ev} kpi:{kpi} conf:{conf} contra:{ca}")
            else:
                ranking = res.get('ranking_sov', [])[:5]
                if ranking:
                    click.echo("  Ranking SOV: " + ", ".join(ranking))

        def _print_trends(res: dict):
            click.echo("— Trends")
            if 'error' in res:
                click.echo(f"  ✗ {res['error']}")
                return
            resumen = res.get('resumen') or ''
            if not resumen and res.get('tendencias'):
                up = sum(1 for t in res['tendencias'] if t.get('direccion') == '↑')
                down = sum(1 for t in res['tendencias'] if t.get('direccion') == '↓')
                resumen = f"{up} marcas en crecimiento, {down} en decrecimiento"
            click.echo(f"  Resumen: {resumen or '(sin resumen)'}")

            tlist = res.get('tendencias', [])[:5]
            for t in tlist:
                # Formato nuevo (intra-rango o comparación simple con campos de cambio)
                if 'marca' in t:
                    cambios = f"{t.get('cambio_puntos', 0):+,.2f} pp"
                    if t.get('cambio_rel_pct') is not None:
                        cambios += f" ({t.get('cambio_rel_pct', 0):+,.1f}%)"
                    pi = t.get('periodo_inicio') or ''
                    pf = t.get('periodo_fin') or ''
                    tramo = f" {pi}→{pf}" if (pi or pf) else ""
                    sig = t.get('significancia', '')
                    pico = ' pico' if t.get('pico') else ''
                    drivers = ", ".join(t.get('posibles_drivers', [])[:3]) if t.get('posibles_drivers') else ''
                    extra = f" | drivers: {drivers}" if drivers else ''
                    click.echo(f"   · {t.get('marca','')} {t.get('direccion','')} {cambios}{tramo} [{sig}{pico}]{extra}")
                else:
                    # Formato antiguo (tipo/titulo/datos_cuantitativos)
                    dirc = (t.get('datos_cuantitativos', {}) or {}).get('direccion', '')
                    click.echo(f"   · [{t.get('tipo','')}] {t.get('titulo','')} ({dirc})")

        def _print_qualitative(res: dict):
            click.echo("— Qualitative")
            if 'error' in res:
                click.echo(f"  ✗ {res['error']}")
                return
            sent = res.get('sentimiento_por_marca', {}) or {}
            if not sent:
                click.echo("  (sin sentimiento_por_marca)")
                return
            # Mostrar hasta 5 marcas con su score
            shown = 0
            for marca, data in sent.items():
                score = 0.0
                if isinstance(data, dict):
                    score = float(data.get('score_medio') or data.get('score') or 0)
                elif isinstance(data, (int, float)):
                    score = float(data)
                click.echo(f"   · {marca}: {score:.2f}")
                shown += 1
                if shown >= 5:
                    break

        PRINTERS = {
            'quantitative': _print_quantitative,
            'competitive': _print_competitive,
            'trends': _print_trends,
            'qualitative': _print_qualitative,
        }

        for key in selected:
            click.echo("")
            res = _ensure_result(key)
            printer = PRINTERS.get(key)
            if printer:
                printer(res)
            else:
                # Para agentes sin impresor específico, volcar un resumen corto JSON
                txt = json.dumps(res if isinstance(res, dict) else {'result': res}, ensure_ascii=False)[:2000]
                click.echo(f"— {key}")
                click.echo(f"  {txt}")

if __name__ == "__main__":
    cli()

