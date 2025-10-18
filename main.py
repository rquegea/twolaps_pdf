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
        report_id = run_analysis(category, period)
        click.echo(f"  ✓ Análisis completado (report_id: {report_id})")
        
        # 2. Generar PDF
        click.echo("📄 Generando PDF...")
        pdf_path = generate_pdf(report_id, output_path=output)
        
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
            report_id = run_analysis(category_full, period)
            pdf_path = generate_pdf(report_id)
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
    """Ejecutar AHORA todas las queries activas ignorando el scheduler"""
    from src.database.connection import get_session
    from src.database.models import Mercado, Categoria
    from src.query_executor.poller import execute_category_queries

    with get_session() as session:
        mercados = session.query(Mercado).filter_by(activo=True).all()
        if market:
            mercados = [m for m in mercados if m.nombre == market]
            if not mercados:
                click.echo(f"✗ Mercado '{market}' no encontrado", err=True)
                raise click.Abort()

        total_stats = {
            'queries_executed': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_cost': 0.0
        }

        for m in mercados:
            categorias = session.query(Categoria).filter_by(mercado_id=m.id, activo=True).all()
            for c in categorias:
                category_path = f"{m.nombre}/{c.nombre}"
                click.echo(f"🔄 Ejecutando: {category_path}")
                try:
                    stats = execute_category_queries(category_path, providers=list(provider) if provider else None)
                    total_stats['queries_executed'] += stats['queries_executed']
                    total_stats['total_executions'] += stats['total_executions']
                    total_stats['successful_executions'] += stats['successful_executions']
                    total_stats['failed_executions'] += stats['failed_executions']
                    total_stats['total_cost'] += stats['total_cost']
                except Exception as e:
                    click.echo(f"  ✗ Error: {e}")
                click.echo("")

        click.echo("\n✅ Ejecución global completada")
        click.echo(f"  Queries ejecutadas: {total_stats['queries_executed']}")
        click.echo(f"  Respuestas:        {total_stats['total_executions']}")
        click.echo(f"  Éxitos:            {total_stats['successful_executions']}")
        click.echo(f"  Fallos:            {total_stats['failed_executions']}")
        click.echo(f"  Coste total:       ${total_stats['total_cost']:.4f}")


# Registrar grupo de comandos admin
cli.add_command(admin)


if __name__ == "__main__":
    cli()

