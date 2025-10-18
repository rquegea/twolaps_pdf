"""
TwoLaps Intelligence Platform - Web Interface
Interfaz web con Streamlit para visualizar y gestionar el sistema
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from src.database.connection import get_session
from src.database.models import (
    Mercado, Categoria, Query, Marca, QueryExecution, 
    AnalysisResult, Report, BrandCandidate
)
from src.query_executor.poller import execute_category_queries
from src.analytics.orchestrator import run_analysis
from src.reporting.pdf_generator import generate_pdf
from src.utils.cost_tracker import cost_tracker

# Configuración de la página
st.set_page_config(
    page_title="TwoLaps Intelligence Platform",
    page_icon="📊",
    layout="wide"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0066cc;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/0066cc/ffffff?text=TwoLaps", width=200)
    st.markdown("---")
    
    page = st.radio(
        "Navegación",
        [
            "🏠 Dashboard",
            "📊 Mercados & Categorías",
            "❓ Queries",
            "🏷️ Marcas",
            "🧪 Candidatos",
            "🤖 Ejecuciones",
            "📈 Análisis",
            "📄 Informes",
            "💰 Costes",
            "⚙️ Ejecutar"
        ]
    )
    
    st.markdown("---")
    st.caption("TwoLaps Intelligence Platform v1.0")

# PÁGINA: DASHBOARD
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">Dashboard Principal</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            num_mercados = session.query(Mercado).filter_by(activo=True).count()
            st.metric("Mercados", num_mercados)
        
        with col2:
            num_categorias = session.query(Categoria).filter_by(activo=True).count()
            st.metric("Categorías", num_categorias)
        
        with col3:
            num_queries = session.query(Query).filter_by(activa=True).count()
            st.metric("Queries Activas", num_queries)
        
        with col4:
            num_reports = session.query(Report).count()
            st.metric("Informes Generados", num_reports)
        
        st.markdown("---")
        
        # Estadísticas de ejecuciones
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Ejecuciones del Mes")
            
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            executions_month = session.query(QueryExecution).filter(
                extract('month', QueryExecution.timestamp) == current_month,
                extract('year', QueryExecution.timestamp) == current_year
            ).count()
            
            st.metric("Total Ejecuciones", executions_month)
            
            # Por proveedor
            executions_by_provider = session.query(
                QueryExecution.proveedor_ia,
                func.count(QueryExecution.id)
            ).filter(
                extract('month', QueryExecution.timestamp) == current_month,
                extract('year', QueryExecution.timestamp) == current_year
            ).group_by(QueryExecution.proveedor_ia).all()
            
            if executions_by_provider:
                df = pd.DataFrame(executions_by_provider, columns=['Proveedor', 'Ejecuciones'])
                st.dataframe(df, use_container_width=True)
        
        with col2:
            st.subheader("💰 Costes del Mes")
            
            costs = cost_tracker.get_monthly_spend(session)
            
            st.metric("Total Gastado", f"${costs.get('total', 0):.2f}")
            st.metric("Presupuesto", f"${costs.get('budget', 0):.2f}")
            
            progress = costs.get('budget_used_percent', 0)
            st.progress(progress / 100)
            st.caption(f"Usado: {progress:.1f}%")
            
            if progress > 80:
                st.warning("⚠️ Presupuesto cerca del límite")
        
        st.markdown("---")
        
        # Últimas ejecuciones
        st.subheader("🕐 Últimas Ejecuciones")
        
        last_executions = session.query(QueryExecution).order_by(
            QueryExecution.timestamp.desc()
        ).limit(10).all()
        
        if last_executions:
            data = []
            for exe in last_executions:
                data.append({
                    'ID': exe.id,
                    'Query': exe.query.pregunta[:50] + '...',
                    'Proveedor': exe.proveedor_ia,
                    'Modelo': exe.modelo,
                    'Timestamp': exe.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'Coste': f"${exe.coste_usd:.4f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay ejecuciones registradas todavía")
        
        # Últimos informes
        st.subheader("📄 Últimos Informes Generados")
        
        last_reports = session.query(Report).order_by(
            Report.timestamp.desc()
        ).limit(5).all()
        
        if last_reports:
            for report in last_reports:
                categoria = session.query(Categoria).get(report.categoria_id)
                mercado = session.query(Mercado).get(categoria.mercado_id)
                
                with st.expander(f"{mercado.nombre}/{categoria.nombre} - {report.periodo}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.caption("Estado")
                        st.write(report.estado)
                    
                    with col2:
                        st.caption("Generado")
                        st.write(report.timestamp.strftime('%Y-%m-%d %H:%M'))
                    
                    with col3:
                        st.caption("PDF")
                        if report.pdf_path:
                            st.write("✅ Disponible")
                        else:
                            st.write("❌ No generado")
        else:
            st.info("No hay informes generados todavía")

# PÁGINA: MERCADOS & CATEGORÍAS
elif page == "📊 Mercados & Categorías":
    st.markdown('<p class="main-header">Mercados & Categorías</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        mercados = session.query(Mercado).filter_by(activo=True).all()
        
        for mercado in mercados:
            with st.expander(f"📊 {mercado.nombre}", expanded=True):
                if mercado.descripcion:
                    st.caption(mercado.descripcion)
                
                categorias = session.query(Categoria).filter_by(
                    mercado_id=mercado.id,
                    activo=True
                ).all()
                
                if categorias:
                    data = []
                    for cat in categorias:
                        num_queries = session.query(Query).filter_by(
                            categoria_id=cat.id,
                            activa=True
                        ).count()
                        
                        num_marcas = session.query(Marca).filter_by(
                            categoria_id=cat.id
                        ).count()
                        
                        num_reports = session.query(Report).filter_by(
                            categoria_id=cat.id
                        ).count()
                        
                        data.append({
                            'Categoría': cat.nombre,
                            'Queries': num_queries,
                            'Marcas': num_marcas,
                            'Informes': num_reports
                        })
                    
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No hay categorías en este mercado")

# PÁGINA: QUERIES
elif page == "❓ Queries":
    st.markdown('<p class="main-header">Queries Configuradas</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            mercados = session.query(Mercado).filter_by(activo=True).all()
            mercado_names = ["Todos"] + [m.nombre for m in mercados]
            selected_mercado = st.selectbox("Mercado", mercado_names)
        
        with col2:
            if selected_mercado != "Todos":
                mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
                categorias = session.query(Categoria).filter_by(
                    mercado_id=mercado.id,
                    activo=True
                ).all()
                cat_names = ["Todas"] + [c.nombre for c in categorias]
            else:
                cat_names = ["Todas"]
            
            selected_categoria = st.selectbox("Categoría", cat_names)
        
        st.markdown("---")
        
        # Obtener queries según filtros
        query_filter = {'activa': True}
        
        if selected_mercado != "Todos" and selected_categoria != "Todas":
            mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
            categoria = session.query(Categoria).filter_by(
                mercado_id=mercado.id,
                nombre=selected_categoria
            ).first()
            if categoria:
                query_filter['categoria_id'] = categoria.id
        
        queries = session.query(Query).filter_by(**query_filter).all()
        
        st.subheader(f"📋 Total: {len(queries)} queries")
        
        if queries:
            for q in queries:
                categoria = session.query(Categoria).get(q.categoria_id)
                mercado = session.query(Mercado).get(categoria.mercado_id)
                
                with st.expander(f"[{mercado.nombre}/{categoria.nombre}] {q.pregunta[:80]}..."):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.caption("Frecuencia")
                        st.write(q.frecuencia)
                    
                    with col2:
                        st.caption("Proveedores")
                        st.write(", ".join(q.proveedores_ia))
                    
                    with col3:
                        st.caption("Última Ejecución")
                        if q.ultima_ejecucion:
                            st.write(q.ultima_ejecucion.strftime('%Y-%m-%d %H:%M'))
                        else:
                            st.write("Nunca ejecutada")
                    
                    # Estadísticas
                    num_exec = session.query(QueryExecution).filter_by(query_id=q.id).count()
                    st.metric("Ejecuciones totales", num_exec)
        else:
            st.info("No hay queries configuradas con estos filtros")

# PÁGINA: MARCAS
elif page == "🏷️ Marcas":
    st.markdown('<p class="main-header">Marcas Monitoreadas</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Filtros
        mercados = session.query(Mercado).filter_by(activo=True).all()
        mercado_names = ["Todos"] + [m.nombre for m in mercados]
        selected_mercado = st.selectbox("Mercado", mercado_names)
        
        if selected_mercado != "Todos":
            mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
            categorias = session.query(Categoria).filter_by(
                mercado_id=mercado.id,
                activo=True
            ).all()
        else:
            categorias = session.query(Categoria).filter_by(activo=True).all()
        
        for cat in categorias:
            mercado = session.query(Mercado).get(cat.mercado_id)
            
            with st.expander(f"🏷️ {mercado.nombre}/{cat.nombre}"):
                marcas = session.query(Marca).filter_by(categoria_id=cat.id).all()
                
                if marcas:
                    # Agrupar por tipo
                    lideres = [m for m in marcas if m.tipo == 'lider']
                    competidores = [m for m in marcas if m.tipo == 'competidor']
                    emergentes = [m for m in marcas if m.tipo == 'emergente']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Líderes**")
                        for m in lideres:
                            st.write(f"• {m.nombre}")
                    
                    with col2:
                        st.markdown("**Competidores**")
                        for m in competidores:
                            st.write(f"• {m.nombre}")
                    
                    with col3:
                        st.markdown("**Emergentes**")
                        for m in emergentes:
                            st.write(f"• {m.nombre}")
                else:
                    st.info("No hay marcas configuradas")

# PÁGINA: CANDIDATOS
elif page == "🧪 Candidatos":
    st.markdown('<p class="main-header">Candidatos de Marcas Detectados</p>', unsafe_allow_html=True)
    with get_session() as session:
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            mercados = session.query(Mercado).filter_by(activo=True).all()
            mercado_names = [m.nombre for m in mercados]
            selected_mercado = st.selectbox("Mercado", mercado_names) if mercado_names else None
        with col2:
            categorias = []
            if selected_mercado:
                mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
                categorias = session.query(Categoria).filter_by(mercado_id=mercado.id, activo=True).all()
            cat_names = [c.nombre for c in categorias]
            selected_categoria = st.selectbox("Categoría", cat_names) if cat_names else None
        with col3:
            status = st.selectbox("Estado", ["pending", "approved", "rejected"], index=0)

        st.markdown("---")

        if selected_mercado and selected_categoria:
            categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=selected_categoria).first()
            rows = session.query(BrandCandidate).filter_by(categoria_id=categoria.id, estado=status).order_by(BrandCandidate.ocurrencias.desc()).all()

            st.subheader(f"{len(rows)} candidatos ({status})")

            if not rows:
                st.info("No hay candidatos con estos filtros")
            else:
                for bc in rows:
                    with st.expander(f"{bc.nombre_detectado}  (conf: {bc.confianza or 0:.2f}, occ: {bc.ocurrencias})", expanded=False):
                        st.caption(f"Aliases: {', '.join(bc.aliases_detectados or []) if bc.aliases_detectados else '—'}")
                        cols = st.columns(3)

                        # Aprobar
                        with cols[0]:
                            tipo = st.selectbox("Tipo", ["lider", "competidor", "emergente"], index=1, key=f"tipo_{bc.id}")
                            if st.button("✅ Aprobar y crear marca", key=f"approve_{bc.id}"):
                                # Crear marca si no existe
                                existing = session.query(Marca).filter_by(categoria_id=categoria.id, nombre=bc.nombre_detectado).first()
                                if not existing:
                                    marca = Marca(
                                        categoria_id=categoria.id,
                                        nombre=bc.nombre_detectado,
                                        tipo=tipo,
                                        aliases=list(set([bc.nombre_detectado] + (bc.aliases_detectados or [])))
                                    )
                                    session.add(marca)
                                    session.flush()
                                bc.estado = 'approved'
                                session.commit()
                                st.success("Candidato aprobado y marca creada")

                        # Rechazar
                        with cols[1]:
                            if st.button("❌ Rechazar", key=f"reject_{bc.id}"):
                                bc.estado = 'rejected'
                                session.commit()
                                st.warning("Candidato rechazado")

                        # Metadata
                        with cols[2]:
                            st.caption(f"Visto por primera vez: {bc.first_seen.strftime('%Y-%m-%d %H:%M')}")
                            st.caption(f"Última vez: {bc.last_seen.strftime('%Y-%m-%d %H:%M')}")

# PÁGINA: EJECUCIONES
elif page == "🤖 Ejecuciones":
    st.markdown('<p class="main-header">Historial de Ejecuciones</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dias = st.selectbox("Últimos", [1, 7, 30, 90], index=2)
        
        with col2:
            proveedores = ['Todos', 'openai', 'anthropic', 'google', 'perplexity']
            proveedor_filter = st.selectbox("Proveedor", proveedores)
        
        with col3:
            limit = st.number_input("Mostrar", min_value=10, max_value=1000, value=50, step=10)
        
        st.markdown("---")
        
        # Query
        fecha_limite = datetime.now() - timedelta(days=dias)
        query_executions = session.query(QueryExecution).filter(
            QueryExecution.timestamp >= fecha_limite
        )
        
        if proveedor_filter != 'Todos':
            query_executions = query_executions.filter_by(proveedor_ia=proveedor_filter)
        
        executions = query_executions.order_by(
            QueryExecution.timestamp.desc()
        ).limit(limit).all()
        
        st.subheader(f"📊 Encontradas: {len(executions)} ejecuciones")
        
        if executions:
            # Estadísticas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_cost = sum(e.coste_usd or 0 for e in executions)
                st.metric("Coste Total", f"${total_cost:.2f}")
            
            with col2:
                total_tokens = sum((e.tokens_input or 0) + (e.tokens_output or 0) for e in executions)
                st.metric("Tokens Totales", f"{total_tokens:,}")
            
            with col3:
                avg_latency = sum(e.latencia_ms or 0 for e in executions) / len(executions)
                st.metric("Latencia Media", f"{avg_latency:.0f}ms")
            
            with col4:
                st.metric("Total", len(executions))
            
            st.markdown("---")
            
            # Tabla
            data = []
            for exe in executions:
                data.append({
                    'ID': exe.id,
                    'Query': exe.query.pregunta[:60] + '...',
                    'Proveedor': exe.proveedor_ia,
                    'Modelo': exe.modelo,
                    'Timestamp': exe.timestamp,
                    'Tokens In': exe.tokens_input,
                    'Tokens Out': exe.tokens_output,
                    'Coste': f"${exe.coste_usd:.4f}",
                    'Latencia': f"{exe.latencia_ms}ms"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("No hay ejecuciones en el periodo seleccionado")

# PÁGINA: ANÁLISIS
elif page == "📈 Análisis":
    st.markdown('<p class="main-header">Resultados de Análisis</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            mercados = session.query(Mercado).filter_by(activo=True).all()
            mercado_names = [m.nombre for m in mercados]
            if mercado_names:
                selected_mercado = st.selectbox("Mercado", mercado_names)
        
        with col2:
            if mercado_names:
                mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
                categorias = session.query(Categoria).filter_by(
                    mercado_id=mercado.id,
                    activo=True
                ).all()
                cat_names = [c.nombre for c in categorias]
                if cat_names:
                    selected_categoria = st.selectbox("Categoría", cat_names)
        
        st.markdown("---")
        
        if mercado_names and cat_names:
            categoria = session.query(Categoria).filter_by(
                mercado_id=mercado.id,
                nombre=selected_categoria
            ).first()
            
            # Obtener análisis
            analysis = session.query(AnalysisResult).filter_by(
                categoria_id=categoria.id
            ).order_by(AnalysisResult.periodo.desc()).all()
            
            if analysis:
                # Agrupar por periodo
                periodos = {}
                for a in analysis:
                    if a.periodo not in periodos:
                        periodos[a.periodo] = {}
                    periodos[a.periodo][a.agente] = a
                
                for periodo, agentes in periodos.items():
                    with st.expander(f"📅 {periodo}", expanded=False):
                        st.caption(f"Agentes ejecutados: {len(agentes)}")
                        
                        # Mostrar resumen de cada agente
                        for agente_name, result in agentes.items():
                            st.markdown(f"**{agente_name.capitalize()}**")
                            
                            # Mostrar métricas clave según agente
                            if agente_name == 'quantitative':
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Menciones", result.resultado.get('total_menciones', 0))
                                with col2:
                                    st.metric("Marcas Mencionadas", result.resultado.get('num_marcas_mencionadas', 0))
                                with col3:
                                    st.metric("Ejecuciones", result.resultado.get('total_executions', 0))
                                
                                # SOV
                                if 'sov_percent' in result.resultado:
                                    st.caption("Share of Voice:")
                                    sov_df = pd.DataFrame(
                                        list(result.resultado['sov_percent'].items()),
                                        columns=['Marca', 'SOV %']
                                    ).sort_values('SOV %', ascending=False)
                                    st.dataframe(sov_df, use_container_width=True)
                            
                            elif agente_name == 'sentiment':
                                st.metric("Sentimiento Global", f"{result.resultado.get('sentimiento_global', 0):.2f}")
                            
                            elif agente_name == 'competitive':
                                st.write(f"Líder: **{result.resultado.get('lider_mercado', 'N/A')}**")
                            
                            elif agente_name == 'strategic':
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Oportunidades", len(result.resultado.get('oportunidades', [])))
                                with col2:
                                    st.metric("Riesgos", len(result.resultado.get('riesgos', [])))
                            
                            st.markdown("---")
            else:
                st.info(f"No hay análisis para {selected_mercado}/{selected_categoria}")

# PÁGINA: INFORMES
elif page == "📄 Informes":
    st.markdown('<p class="main-header">Informes Generados</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        reports = session.query(Report).order_by(Report.timestamp.desc()).all()
        
        if reports:
            for report in reports:
                categoria = session.query(Categoria).get(report.categoria_id)
                mercado = session.query(Mercado).get(categoria.mercado_id)
                
                with st.expander(f"📄 {mercado.nombre}/{categoria.nombre} - {report.periodo}"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.caption("Estado")
                        if report.estado == 'published':
                            st.success("✅ Publicado")
                        elif report.estado == 'draft':
                            st.warning("📝 Borrador")
                        else:
                            st.info(report.estado)
                    
                    with col2:
                        st.caption("Generado")
                        st.write(report.timestamp.strftime('%Y-%m-%d %H:%M'))
                    
                    with col3:
                        st.caption("PDF")
                        if report.pdf_path:
                            st.success("✅ Disponible")
                        else:
                            st.error("❌ No generado")
                    
                    with col4:
                        st.caption("Generado por")
                        st.write(report.generado_por)
                    
                    # Métricas de calidad
                    if report.metricas_calidad:
                        st.markdown("**Métricas de Calidad:**")
                        cols = st.columns(4)
                        metrics = report.metricas_calidad
                        
                        with cols[0]:
                            st.metric("Hallazgos", metrics.get('hallazgos', 0))
                        with cols[1]:
                            st.metric("Oportunidades", metrics.get('oportunidades', 0))
                        with cols[2]:
                            st.metric("Riesgos", metrics.get('riesgos', 0))
                        with cols[3]:
                            st.metric("Plan Acciones", metrics.get('plan_acciones', 0))
                    
                    # Mostrar resumen ejecutivo si existe
                    if 'resumen_ejecutivo' in report.contenido:
                        st.markdown("**Resumen Ejecutivo:**")
                        resumen = report.contenido['resumen_ejecutivo']
                        if 'hallazgos_clave' in resumen:
                            for hallazgo in resumen['hallazgos_clave']:
                                st.write(f"• {hallazgo}")
        else:
            st.info("No hay informes generados todavía")

# PÁGINA: COSTES
elif page == "💰 Costes":
    st.markdown('<p class="main-header">Gestión de Costes</p>', unsafe_allow_html=True)
    
    with get_session() as session:
        # Costes del mes actual
        st.subheader("📅 Mes Actual")
        
        costs = cost_tracker.get_monthly_spend(session)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Gastado", f"${costs.get('total', 0):.2f}")
        
        with col2:
            st.metric("Presupuesto", f"${costs.get('budget', 0):.2f}")
        
        with col3:
            st.metric("Usado", f"{costs.get('budget_used_percent', 0):.1f}%")
        
        with col4:
            st.metric("Restante", f"${costs.get('budget_remaining', 0):.2f}")
        
        # Progress bar
        progress = costs.get('budget_used_percent', 0)
        st.progress(progress / 100)
        
        if progress > 80:
            st.error("⚠️ ALERTA: Presupuesto cerca del límite")
        elif progress > 60:
            st.warning("⚠️ Cuidado: Más del 60% del presupuesto usado")
        else:
            st.success("✅ Presupuesto bajo control")
        
        st.markdown("---")
        
        # Costes por proveedor
        st.subheader("📊 Por Proveedor")
        
        provider_data = []
        for provider in ['openai', 'anthropic', 'google']:
            if provider in costs:
                provider_data.append({
                    'Proveedor': provider.upper(),
                    'Coste': costs[provider],
                    'Porcentaje': (costs[provider] / costs['total'] * 100) if costs['total'] > 0 else 0
                })
        
        if provider_data:
            df = pd.DataFrame(provider_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(df, use_container_width=True)
            
            with col2:
                st.bar_chart(df.set_index('Proveedor')['Coste'])

# PÁGINA: EJECUTAR
elif page == "⚙️ Ejecutar":
    st.markdown('<p class="main-header">Ejecutar Acciones</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🤖 Ejecutar Queries", "📄 Generar Informe"])
    
    with tab1:
        st.subheader("Ejecutar Queries de una Categoría")
        
        with get_session() as session:
            mercados = session.query(Mercado).filter_by(activo=True).all()
            mercado_names = [m.nombre for m in mercados]
            
            if mercado_names:
                selected_mercado = st.selectbox("Mercado", mercado_names, key="exec_mercado")
                
                mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
                categorias = session.query(Categoria).filter_by(
                    mercado_id=mercado.id,
                    activo=True
                ).all()
                cat_names = [c.nombre for c in categorias]
                
                if cat_names:
                    selected_categoria = st.selectbox("Categoría", cat_names, key="exec_cat")
                    
                    category_path = f"{selected_mercado}/{selected_categoria}"
                    
                    st.info(f"Se ejecutarán las queries activas de: **{category_path}**")
                    
                    if st.button("🚀 Ejecutar Queries", type="primary"):
                        with st.spinner("Ejecutando queries..."):
                            try:
                                result = execute_category_queries(category_path)
                                
                                st.success("✅ Ejecución completada!")
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Queries Ejecutadas", result['queries_executed'])
                                with col2:
                                    st.metric("Respuestas Obtenidas", result['total_executions'])
                                with col3:
                                    st.metric("Coste Total", f"${result['total_cost']:.4f}")
                            
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("No hay categorías en este mercado")
            else:
                st.warning("No hay mercados configurados")
    
    with tab2:
        st.subheader("Generar Informe PDF")
        
        with get_session() as session:
            mercados = session.query(Mercado).filter_by(activo=True).all()
            mercado_names = [m.nombre for m in mercados]
            
            if mercado_names:
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_mercado = st.selectbox("Mercado", mercado_names, key="report_mercado")
                    
                    mercado = session.query(Mercado).filter_by(nombre=selected_mercado).first()
                    categorias = session.query(Categoria).filter_by(
                        mercado_id=mercado.id,
                        activo=True
                    ).all()
                    cat_names = [c.nombre for c in categorias]
                    
                    if cat_names:
                        selected_categoria = st.selectbox("Categoría", cat_names, key="report_cat")
                
                with col2:
                    # Periodo
                    periodo = st.text_input("Periodo (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
                
                if cat_names:
                    category_path = f"{selected_mercado}/{selected_categoria}"
                    
                    st.info(f"Se generará informe para: **{category_path} - {periodo}**")
                    
                    if st.button("📄 Generar Informe", type="primary"):
                        with st.spinner("Generando informe... Esto puede tardar varios minutos"):
                            try:
                                # Ejecutar análisis
                                report_id = run_analysis(category_path, periodo)
                                
                                st.success(f"✅ Análisis completado (Report ID: {report_id})")
                                
                                # Generar PDF
                                with st.spinner("Generando PDF..."):
                                    pdf_path = generate_pdf(report_id)
                                
                                st.success(f"✅ Informe generado exitosamente!")
                                st.info(f"📁 {pdf_path}")
                                
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                st.exception(e)
                else:
                    st.warning("No hay categorías en este mercado")
            else:
                st.warning("No hay mercados configurados")

