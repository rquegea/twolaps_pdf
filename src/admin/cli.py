"""
Admin CLI Commands
Comandos de administración para gestionar mercados, categorías, queries y marcas
"""

import click
import json
from datetime import datetime
from sqlalchemy import extract
from tabulate import tabulate
from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Query, Marca, QueryExecution, BrandCandidate, Embedding, AnalysisResult, Report
from src.utils.cost_tracker import cost_tracker
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@click.group()
def admin():
    """Comandos de administración del sistema"""
    pass


@admin.command()
@click.option('--name', '-n', required=True, help='Nombre del mercado (ej: FMCG)')
@click.option('--description', '-d', help='Descripción del mercado')
@click.option('--type', '-t', 'market_type', 
              type=click.Choice(['FMCG', 'Health_Digital', 'Digital_SaaS', 'Services']),
              default='FMCG', help='Tipo de mercado')
def add_market(name, description, market_type):
    """Añadir un nuevo mercado"""
    with get_session() as session:
        # Verificar si ya existe
        existing = session.query(Mercado).filter_by(nombre=name).first()
        if existing:
            click.echo(f"✗ El mercado '{name}' ya existe (ID: {existing.id})", err=True)
            return
        
        mercado = Mercado(
            nombre=name,
            descripcion=description,
            tipo_mercado=market_type,
            activo=True
        )
        session.add(mercado)
        session.commit()
        
        click.echo(f"✓ Mercado creado: {name} (ID: {mercado.id}) - tipo: {market_type}")
        logger.info("mercado_creado", mercado_id=mercado.id, nombre=name, tipo=market_type)


@admin.command()
@click.option('--market', '-m', required=True, help='Nombre del mercado')
@click.option('--name', '-n', required=True, help='Nombre de la categoría')
@click.option('--description', '-d', help='Descripción')
def add_category(market, name, description):
    """Añadir una nueva categoría a un mercado"""
    with get_session() as session:
        # Buscar mercado
        mercado = session.query(Mercado).filter_by(nombre=market).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market}' no encontrado", err=True)
            return
        
        # Verificar si ya existe
        existing = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=name
        ).first()
        if existing:
            click.echo(f"✗ La categoría '{name}' ya existe en '{market}'", err=True)
            return
        
        categoria = Categoria(
            mercado_id=mercado.id,
            nombre=name,
            descripcion=description,
            activo=True
        )
        session.add(categoria)
        session.commit()
        
        click.echo(f"✓ Categoría creada: {market}/{name} (ID: {categoria.id})")
        logger.info("categoria_creada", categoria_id=categoria.id, nombre=f"{market}/{name}")


@admin.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--question', '-q', required=True, help='Pregunta a hacer a las IAs')
@click.option('--frequency', '-f', default='weekly', 
              type=click.Choice(['daily', 'weekly', 'biweekly', 'monthly', 'quarterly']),
              help='Frecuencia de ejecución')
@click.option('--providers', '-p', default='openai,anthropic,google,perplexity', 
              help='Proveedores (separados por coma). Por defecto: openai,anthropic,google,perplexity')
@click.option('--active/--inactive', default=True, help='Query activa o inactiva')
def add_query(category, question, frequency, providers, active):
    """Añadir una nueva query a una categoría"""
    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato de categoría inválido. Usa: Mercado/Categoría", err=True)
            return
        
        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        
        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return
        
        # Parsear proveedores
        providers_list = [p.strip() for p in providers.split(',')]
        
        query = Query(
            categoria_id=categoria.id,
            pregunta=question,
            activa=active,
            frecuencia=frequency,
            proveedores_ia=providers_list,
            metadata={}
        )
        session.add(query)
        session.commit()
        
        click.echo(f"✓ Query creada (ID: {query.id})")
        click.echo(f"  Pregunta: {question}")
        click.echo(f"  Frecuencia: {frequency}")
        click.echo(f"  Proveedores: {', '.join(providers_list)}")
        click.echo(f"  Activa: {'Sí' if active else 'No'}")
        
        logger.info("query_creada", query_id=query.id, categoria=category)


@admin.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--name', '-n', required=True, help='Nombre de la marca')
@click.option('--type', '-t', 
              type=click.Choice(['lider', 'competidor', 'emergente']),
              default='competidor',
              help='Tipo de marca')
@click.option('--aliases', '-a', help='Aliases separados por coma (ej: "Heineken,heineken,Heineken®")')
def add_brand(category, name, type, aliases):
    """Añadir una nueva marca a monitorear"""
    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato de categoría inválido. Usa: Mercado/Categoría", err=True)
            return
        
        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        
        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return
        
        # Verificar si ya existe
        existing = session.query(Marca).filter_by(
            categoria_id=categoria.id,
            nombre=name
        ).first()
        if existing:
            click.echo(f"✗ La marca '{name}' ya existe en '{category}'", err=True)
            return
        
        # Parsear aliases
        aliases_list = [name]  # Siempre incluir el nombre principal
        if aliases:
            aliases_list.extend([a.strip() for a in aliases.split(',')])
        aliases_list = list(set(aliases_list))  # Eliminar duplicados
        
        marca = Marca(
            categoria_id=categoria.id,
            nombre=name,
            tipo=type,
            aliases=aliases_list,
            metadata={}
        )
        session.add(marca)
        session.commit()
        
        click.echo(f"✓ Marca creada: {name} (ID: {marca.id})")
        click.echo(f"  Tipo: {type}")
        click.echo(f"  Aliases: {', '.join(aliases_list)}")
        
        logger.info("marca_creada", marca_id=marca.id, nombre=name, categoria=category)


@admin.command()
@click.option('--market', '-m', help='Filtrar por mercado')
def list(market):
    """Listar jerarquía de mercados y categorías"""
    with get_session() as session:
        if market:
            mercados = session.query(Mercado).filter_by(nombre=market).all()
            if not mercados:
                click.echo(f"✗ Mercado '{market}' no encontrado", err=True)
                return
        else:
            mercados = session.query(Mercado).filter_by(activo=True).all()
        
        if not mercados:
            click.echo("No hay mercados configurados")
            return
        
        for mercado in mercados:
            click.echo(f"\n📊 {mercado.nombre}")
            if mercado.descripcion:
                click.echo(f"   {mercado.descripcion}")
            
            categorias = session.query(Categoria).filter_by(
                mercado_id=mercado.id,
                activo=True
            ).all()
            
            for cat in categorias:
                num_queries = session.query(Query).filter_by(
                    categoria_id=cat.id,
                    activa=True
                ).count()
                
                num_marcas = session.query(Marca).filter_by(
                    categoria_id=cat.id
                ).count()
                
                click.echo(f"  └── {cat.nombre} ({num_queries} queries, {num_marcas} marcas)")


@admin.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--all', 'show_all', is_flag=True, help='Mostrar queries inactivas también')
def show_queries(category, show_all):
    """Mostrar queries de una categoría"""
    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato de categoría inválido. Usa: Mercado/Categoría", err=True)
            return
        
        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        
        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return
        
        # Obtener queries
        query_filter = {'categoria_id': categoria.id}
        if not show_all:
            query_filter['activa'] = True
        
        queries = session.query(Query).filter_by(**query_filter).all()
        
        if not queries:
            click.echo(f"No hay queries configuradas para '{category}'")
            return
        
        click.echo(f"\n📋 Queries de {category}\n")
        
        for q in queries:
            status = "✓" if q.activa else "✗"
            click.echo(f"{status} ID: {q.id}")
            click.echo(f"  Pregunta: {q.pregunta}")
            click.echo(f"  Frecuencia: {q.frecuencia}")
            click.echo(f"  Proveedores: {', '.join(q.proveedores_ia)}")
            
            if q.ultima_ejecucion:
                click.echo(f"  Última ejecución: {q.ultima_ejecucion.strftime('%Y-%m-%d %H:%M')}")
                
                # Contar ejecuciones totales
                num_exec = session.query(QueryExecution).filter_by(query_id=q.id).count()
                click.echo(f"  Ejecuciones totales: {num_exec}")
            else:
                click.echo(f"  Nunca ejecutada")
            
            click.echo("")


@admin.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
@click.option('--period', '-p', required=True, help='Periodo específico (YYYY-MM)')
def clean_period(category, period):
    """Borrar datos de UN período: ejecuciones, embeddings, análisis y reportes"""
    # Validar periodo
    try:
        if len(period) != 7 or period[4] != '-':
            raise ValueError
        year, month = map(int, period.split('-'))
    except Exception:
        click.echo("✗ Formato de periodo incorrecto. Usa: YYYY-MM (ej: 2025-10)", err=True)
        return

    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato de categoría inválido. Usa: Mercado/Categoría", err=True)
            return

        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return

        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return

        click.echo(f"🧹 Limpiando periodo {period} de {category} ...")

        # 1) Borrar embeddings del periodo (cualquier tipo)
        deleted_embeddings = session.query(Embedding).filter_by(
            categoria_id=categoria.id,
            periodo=period
        ).delete(synchronize_session=False)

        # 2) Borrar AnalysisResult y Report del periodo
        deleted_analysis = session.query(AnalysisResult).filter_by(
            categoria_id=categoria.id,
            periodo=period
        ).delete(synchronize_session=False)

        deleted_reports = session.query(Report).filter_by(
            categoria_id=categoria.id,
            periodo=period
        ).delete(synchronize_session=False)

        # 3) Borrar QueryExecutions del periodo
        exec_ids = [row.id for row in session.query(QueryExecution.id)
                    .join(Query, QueryExecution.query_id == Query.id)
                    .filter(
                        Query.categoria_id == categoria.id,
                        extract('year', QueryExecution.timestamp) == year,
                        extract('month', QueryExecution.timestamp) == month
                    ).all()]

        deleted_executions = 0
        if exec_ids:
            deleted_executions = session.query(QueryExecution).filter(
                QueryExecution.id.in_(exec_ids)
            ).delete(synchronize_session=False)

        session.commit()

        click.echo("✅ Limpieza de periodo completada:")
        click.echo(f"   - Embeddings borrados: {deleted_embeddings}")
        click.echo(f"   - Análisis borrados:  {deleted_analysis}")
        click.echo(f"   - Reportes borrados:  {deleted_reports}")
        click.echo(f"   - Ejecuciones borradas: {deleted_executions}")


@admin.command()
@click.option('--category', '-c', required=True, help='Categoría (formato: Mercado/Categoría)')
def show_brands(category):
    """Mostrar marcas de una categoría"""
    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato de categoría inválido. Usa: Mercado/Categoría", err=True)
            return
        
        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        
        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return
        
        # Obtener marcas
        marcas = session.query(Marca).filter_by(categoria_id=categoria.id).all()
        
        if not marcas:
            click.echo(f"No hay marcas configuradas para '{category}'")
            return
        
        click.echo(f"\n🏷️  Marcas de {category}\n")
        
        # Agrupar por tipo
        for tipo in ['lider', 'competidor', 'emergente']:
            marcas_tipo = [m for m in marcas if m.tipo == tipo]
            if marcas_tipo:
                click.echo(f"{tipo.upper()}:")
                for marca in marcas_tipo:
                    click.echo(f"  • {marca.nombre} (ID: {marca.id})")
                    if len(marca.aliases) > 1:
                        otros = [a for a in marca.aliases if a != marca.nombre]
                        click.echo(f"    Aliases: {', '.join(otros)}")
                click.echo("")


@admin.command()
@click.option('--id', '-i', required=True, type=int, help='ID de la query')
@click.option('--active/--inactive', default=None, help='Activar o desactivar')
def toggle_query(id, active):
    """Activar o desactivar una query"""
    with get_session() as session:
        query = session.query(Query).get(id)
        if not query:
            click.echo(f"✗ Query con ID {id} no encontrada", err=True)
            return
        
        if active is not None:
            query.activa = active
            session.commit()
            
            status = "activada" if active else "desactivada"
            click.echo(f"✓ Query {id} {status}")
        else:
            # Toggle
            query.activa = not query.activa
            session.commit()
            
            status = "activada" if query.activa else "desactivada"
            click.echo(f"✓ Query {id} {status}")


@admin.command()
@click.option('--period', '-p', help='Periodo específico (YYYY-MM)')
@click.option('--category', '-c', help='Categoría específica (Mercado/Categoría)')
def costs(period, category):
    """Mostrar estadísticas de costes"""
    with get_session() as session:
        if period and category:
            # Costes de un periodo y categoría específicos
            try:
                market_name, cat_name = category.split('/')
            except ValueError:
                click.echo("✗ Formato de categoría inválido", err=True)
                return
            
            mercado = session.query(Mercado).filter_by(nombre=market_name).first()
            if not mercado:
                click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
                return
            
            categoria = session.query(Categoria).filter_by(
                mercado_id=mercado.id,
                nombre=cat_name
            ).first()
            if not categoria:
                click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
                return
            
            costs_data = cost_tracker.get_period_costs(session, categoria.id, period)
            report = cost_tracker.format_cost_report(costs_data)
            click.echo(f"\n{category} - {period}")
            click.echo(report)
        
        else:
            # Costes del mes actual
            costs_data = cost_tracker.get_monthly_spend(session)
            report = cost_tracker.format_cost_report(costs_data)
            click.echo(f"\nMes actual ({datetime.now().strftime('%Y-%m')})")
            click.echo(report)
            
            # Verificar alertas
            alert = cost_tracker.check_budget_alert(session)
            if alert:
                click.echo(f"\n{alert['message']}")


@admin.command()
def seed_fmcg():
    """Poblar base de datos con datos FMCG iniciales"""
    from src.admin.seed_fmcg import seed_all_fmcg
    
    click.echo("🌱 Poblando base de datos con datos FMCG...")
    try:
        seed_all_fmcg()
        click.echo("✓ Datos FMCG creados exitosamente")
    except Exception as e:
        click.echo(f"✗ Error al crear datos: {e}", err=True)
        logger.error("Error en seed_fmcg", exc_info=True)


@admin.command()
def seed_fmcg_incremental():
    """Poblar/actualizar FMCG sin borrar datos previos (incremental)"""
    from src.admin.seed_fmcg import (
        _get_or_create_market, _get_or_create_category, _incremental_populate,
        seed_champagnes, seed_chocolates_premium, seed_bolleria_tortitas,
        seed_turrones_mazapanes, seed_ginebras, seed_galletas_saludables,
        seed_galletas_caramelizadas, seed_embutidos_curados, seed_rones_extendido,
        seed_geles_ducha, _data_puros_premium
    )

    click.echo("🌱 Seeding FMCG (incremental, sin borrar nada)...")
    try:
        with get_session() as session:
            mercado = _get_or_create_market(session, "FMCG", "Fast Moving Consumer Goods - Productos de gran consumo", "FMCG")

            categorias_def = [
                ("Champagnes", "Champagnes y vinos espumosos"),
                ("Puros Premium", "Puros y cigarros premium"),
                ("Chocolates Premium", "Chocolates gourmet/premium para regalo y disfrute"),
                ("Bollería y Tortitas", "Bollería industrial envasada y tortitas de arroz/maíz"),
                ("Turrones y Mazapanes", "Confitería tradicional navideña"),
                ("Ginebras", "Ginebras estándar y premium"),
                ("Galletas Saludables", "Galletas con claims de salud: sin azúcar, fibra, integral"),
                ("Galletas Caramelizadas", "Galletas de café/speculoos y derivados"),
                ("Embutidos Curados", "Jamón serrano/blanco y embutidos curados"),
                ("Rones", "Rones y bebidas espirituosas"),
                ("Geles de Ducha", "Higiene personal - geles clásicos y alternativas"),
            ]

            # Para mantener una única fuente de verdad, reutilizamos las funciones de seed para obtener datos de marcas/preguntas
            # sin ejecutar su inserción directa (usaremos incremental). Extraemos datos recreando listas locales.

            # Construimos un diccionario {nombre_categoria: (marcas, preguntas, frecuencia)}
            # Para ello, llamamos a las funciones de seed originales en un contexto controlado sería complejo.
            # Solución: replicar parte del contenido reutilizando el mismo módulo (importado) y accediendo a estructuras ya escritas.
            # Dado que aquí no tenemos acceso directo, invocamos helpers específicos por categoría definidos abajo.

            from src.admin.seed_fmcg import (
                _data_chocolates_premium, _data_bolleria_tortitas, _data_turrones_mazapanes,
                _data_ginebras, _data_galletas_caramelizadas, _data_embutidos_curados,
                _data_rones_extendido, _data_geles_ducha, _data_champagnes, _data_puros_premium
            )

            # Nota: delegamos en helpers de datos por categoría y aplicamos inserción incremental

            # Implementación sencilla y robusta:
            for nombre, descripcion in categorias_def:
                categoria = _get_or_create_category(session, mercado.id, nombre, descripcion)
                # Llamar a la función específica de la categoría pero en modo incremental
                if nombre == "Champagnes":
                    marcas, preguntas = _data_champagnes()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Puros Premium":
                    marcas, preguntas = _data_puros_premium()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Chocolates Premium":
                    marcas, preguntas = _data_chocolates_premium()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Bollería y Tortitas":
                    marcas, preguntas = _data_bolleria_tortitas()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Turrones y Mazapanes":
                    marcas, preguntas = _data_turrones_mazapanes()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Ginebras":
                    marcas, preguntas = _data_ginebras()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Galletas Saludables":
                    # OJO: el usuario quiere foco saludable; mantenemos dataset de galletas saludables
                    from src.admin.seed_fmcg import _data_galletas_saludables
                    marcas, preguntas = _data_galletas_saludables()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Galletas Caramelizadas":
                    marcas, preguntas = _data_galletas_caramelizadas()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Embutidos Curados":
                    marcas, preguntas = _data_embutidos_curados()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Rones":
                    marcas, preguntas = _data_rones_extendido()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")
                elif nombre == "Geles de Ducha":
                    marcas, preguntas = _data_geles_ducha()
                    _incremental_populate(session, categoria, marcas, preguntas, frecuencia="monthly")

            session.commit()
        click.echo("✓ Seed FMCG incremental completado")
    except Exception as e:
        click.echo(f"✗ Error en seed_fmcg_incremental: {e}", err=True)
        logger.error("Error en seed_fmcg_incremental", exc_info=True)


@admin.command()
def seed_health():
    """Poblar base de datos con datos del mercado Salud"""
    from src.admin.seed_health import seed_health_market
    
    click.echo("🌱 Poblando base de datos con datos de Salud...")
    try:
        seed_health_market()
        click.echo("✓ Datos de Salud creados exitosamente")
    except Exception as e:
        click.echo(f"✗ Error al crear datos de Salud: {e}", err=True)
        logger.error("Error en seed_health", exc_info=True)


@admin.group()
def candidates():
    """Gestionar candidatos de marcas detectados automáticamente"""
    pass


@candidates.command("list")
@click.option('--category', '-c', required=True, help='Categoría (Mercado/Categoría)')
@click.option('--status', '-s', type=click.Choice(['pending', 'approved', 'rejected']), default='pending')
def list_candidates(category, status):
    """Listar candidatos de una categoría por estado"""
    with get_session() as session:
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato inválido. Usa Mercado/Categoría", err=True)
            return

        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=cat_name).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return

        rows = session.query(BrandCandidate).filter_by(categoria_id=categoria.id, estado=status).order_by(BrandCandidate.ocurrencias.desc()).all()
        if not rows:
            click.echo("(sin candidatos)")
            return
        click.echo(f"\nCandidatos ({status}) en {category}\n")
        for bc in rows:
            click.echo(f"- {bc.nombre_detectado}  (conf: {bc.confianza or 0:.2f}, occ: {bc.ocurrencias})")


@candidates.command("approve")
@click.option('--category', '-c', required=True, help='Categoría (Mercado/Categoría)')
@click.option('--name', '-n', required=True, help='Nombre del candidato a aprobar')
@click.option('--type', '-t', type=click.Choice(['lider', 'competidor', 'emergente']), default='competidor')
def approve_candidate(category, name, type):
    """Aprueba un candidato y lo promueve a `Marca`"""
    with get_session() as session:
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato inválido. Usa Mercado/Categoría", err=True)
            return

        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=cat_name).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return

        bc = session.query(BrandCandidate).filter_by(categoria_id=categoria.id, nombre_detectado=name).first()
        if not bc:
            click.echo(f"✗ Candidato '{name}' no encontrado", err=True)
            return

        # Crear marca si no existe
        existing = session.query(Marca).filter_by(categoria_id=categoria.id, nombre=bc.nombre_detectado).first()
        if existing:
            click.echo(f"✓ Ya existe marca '{bc.nombre_detectado}' (ID: {existing.id})")
        else:
            marca = Marca(
                categoria_id=categoria.id,
                nombre=bc.nombre_detectado,
                tipo=type,
                aliases=list(set([bc.nombre_detectado] + (bc.aliases_detectados or [])))
            )
            session.add(marca)
            session.flush()
            click.echo(f"✓ Marca creada: {marca.nombre} (ID: {marca.id})")

        # Actualizar candidato
        bc.estado = 'approved'
        session.commit()
        click.echo("✓ Candidato aprobado")


@candidates.command("reject")
@click.option('--category', '-c', required=True, help='Categoría (Mercado/Categoría)')
@click.option('--name', '-n', required=True, help='Nombre del candidato a rechazar')
def reject_candidate(category, name):
    """Rechaza un candidato"""
    with get_session() as session:
        try:
            market_name, cat_name = category.split('/')
        except ValueError:
            click.echo("✗ Formato inválido. Usa Mercado/Categoría", err=True)
            return

        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            click.echo(f"✗ Mercado '{market_name}' no encontrado", err=True)
            return
        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=cat_name).first()
        if not categoria:
            click.echo(f"✗ Categoría '{category}' no encontrada", err=True)
            return

        bc = session.query(BrandCandidate).filter_by(categoria_id=categoria.id, nombre_detectado=name).first()
        if not bc:
            click.echo(f"✗ Candidato '{name}' no encontrado", err=True)
            return
        bc.estado = 'rejected'
        session.commit()
        click.echo("✓ Candidato rechazado")
