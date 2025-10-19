"""
RAG Manager
Sistema de Retrieval-Augmented Generation para contexto histórico
"""

from typing import List, Dict, Any
from sqlalchemy import text
from src.database.models import Embedding, Report, AnalysisResult, QueryExecution
from src.query_executor.api_clients import OpenAIClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGManager:
    """
    Gestor de RAG con embeddings y búsqueda vectorial
    """
    
    def __init__(self, session):
        """
        Initialize RAG manager
        
        Args:
            session: Sesión de SQLAlchemy
        """
        self.session = session
        self.client = OpenAIClient()
        self.embedding_dimension = 1536  # OpenAI text-embedding-3-small
    
    def create_embedding(
        self,
        categoria_id: int,
        periodo: str,
        tipo: str,
        referencia_id: int,
        texto: str,
        metadata: Dict = None
    ) -> int:
        """
        Crea un embedding y lo guarda en BD
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo
            tipo: Tipo (report, analysis_result, query_execution)
            referencia_id: ID del registro original
            texto: Texto a embedar
            metadata: Metadata adicional
        
        Returns:
            ID del embedding creado
        """
        try:
            # Generar embedding
            vector = self.client.generate_embedding(texto)
            
            # Guardar en BD
            embedding = Embedding(
                categoria_id=categoria_id,
                periodo=periodo,
                tipo=tipo,
                referencia_id=referencia_id,
                vector=vector,
                metadata=metadata or {}
            )
            
            self.session.add(embedding)
            self.session.commit()
            
            logger.info(
                "embedding_created",
                categoria_id=categoria_id,
                periodo=periodo,
                tipo=tipo,
                embedding_id=embedding.id
            )
            
            return embedding.id
        
        except Exception as e:
            logger.error(f"Error creando embedding: {e}", exc_info=True)
            return None
    
    def search_similar(
        self,
        categoria_id: int,
        query_text: str,
        top_k: int = 3,
        periodo_actual: str = None,
        tipo_filtro: str = None,
        incluir_periodo_actual: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca embeddings similares usando búsqueda vectorial
        
        Args:
            categoria_id: ID de categoría
            query_text: Texto de búsqueda
            top_k: Número de resultados a retornar
            periodo_actual: Periodo para filtrar
            tipo_filtro: Tipo de embedding a filtrar (query_execution, analysis_result, report)
            incluir_periodo_actual: Si True, incluye periodo_actual; si False, lo excluye
        
        Returns:
            Lista de embeddings similares con metadata
        """
        try:
            # Generar embedding de la query
            query_vector = self.client.generate_embedding(query_text)
            
            # Construir query SQL con pgvector
            # Usamos operador <=> para distancia coseno
            # Condicional para periodo según incluir_periodo_actual
            periodo_condition = ""
            if periodo_actual:
                if incluir_periodo_actual:
                    periodo_condition = "AND e.periodo = :periodo_actual"
                else:
                    periodo_condition = "AND e.periodo != :periodo_actual"
            
            tipo_condition = ""
            if tipo_filtro:
                tipo_condition = "AND e.tipo = :tipo_filtro"
            
            sql = text(f"""
                SELECT 
                    e.id,
                    e.categoria_id,
                    e.periodo,
                    e.tipo,
                    e.referencia_id,
                    e.metadata,
                    (e.vector <=> :query_vector) as distance
                FROM embeddings e
                WHERE e.categoria_id = :categoria_id
                    {periodo_condition}
                    {tipo_condition}
                ORDER BY e.vector <=> :query_vector
                LIMIT :top_k
            """)
            
            # Parámetros
            params = {
                'query_vector': str(query_vector),
                'categoria_id': categoria_id,
                'top_k': top_k
            }
            
            if periodo_actual:
                params['periodo_actual'] = periodo_actual
            
            if tipo_filtro:
                params['tipo_filtro'] = tipo_filtro
            
            # Ejecutar query
            result = self.session.execute(sql, params)
            
            # Procesar resultados
            similar_items = []
            for row in result:
                similar_items.append({
                    'embedding_id': row.id,
                    'periodo': row.periodo,
                    'tipo': row.tipo,
                    'referencia_id': row.referencia_id,
                    'distance': float(row.distance),
                    'similarity': 1 - float(row.distance),  # Convertir distancia a similaridad
                    'metadata': row.metadata
                })
            
            logger.info(
                "similarity_search_completed",
                categoria_id=categoria_id,
                tipo_filtro=tipo_filtro,
                periodo_actual=periodo_actual,
                incluir_periodo_actual=incluir_periodo_actual,
                results_found=len(similar_items)
            )
            
            return similar_items
        
        except Exception as e:
            logger.error(f"Error en búsqueda de similaridad: {e}", exc_info=True)
            return []
    
    def search_query_executions_for_question(
        self,
        categoria_id: int,
        periodo: str,
        analytical_question: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca los fragmentos de QueryExecution más relevantes para una pregunta analítica
        Específicamente diseñado para QualitativeExtractionAgent con RAG
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo actual (YYYY-MM) a analizar
            analytical_question: Pregunta analítica (ej: "¿Sentimiento sobre Marca X?")
            top_k: Número de fragmentos a recuperar
        
        Returns:
            Lista de dicts con {texto, execution_id, metadata, similarity}
        """
        try:
            # Buscar embeddings similares dentro del periodo actual
            similar_embeddings = self.search_similar(
                categoria_id=categoria_id,
                query_text=analytical_question,
                top_k=top_k,
                periodo_actual=periodo,
                tipo_filtro='query_execution',
                incluir_periodo_actual=True  # IMPORTANTE: incluir periodo actual
            )
            
            if not similar_embeddings:
                logger.warning(
                    "no_embeddings_found_for_question",
                    categoria_id=categoria_id,
                    periodo=periodo,
                    question=analytical_question[:50]
                )
                return []
            
            # Recuperar los textos completos de las QueryExecution
            results = []
            for emb in similar_embeddings:
                execution = self.session.query(QueryExecution).get(emb['referencia_id'])
                
                if execution and execution.respuesta_texto:
                    results.append({
                        'texto': execution.respuesta_texto,
                        'execution_id': execution.id,
                        'similarity': emb['similarity'],
                        'metadata': {
                            'proveedor_ia': execution.proveedor_ia,
                            'modelo': execution.modelo,
                            'timestamp': execution.timestamp.isoformat(),
                            'embedding_metadata': emb['metadata']
                        }
                    })
            
            logger.info(
                "query_executions_retrieved_for_question",
                categoria_id=categoria_id,
                periodo=periodo,
                question=analytical_question[:50],
                retrieved_count=len(results)
            )
            
            return results
        
        except Exception as e:
            logger.error(
                f"Error recuperando QueryExecution para pregunta: {e}",
                exc_info=True
            )
            return []
    
    def get_historical_context(
        self,
        categoria_id: int,
        periodo_actual: str,
        top_k: int = 3
    ) -> str:
        """
        Obtiene contexto histórico para un informe
        
        Args:
            categoria_id: ID de categoría
            periodo_actual: Periodo actual
            top_k: Número de periodos a recuperar
        
        Returns:
            Texto con contexto histórico
        """
        # Buscar periodos similares
        query_text = f"Análisis de mercado y competencia para periodo {periodo_actual}"
        similar_periods = self.search_similar(
            categoria_id,
            query_text,
            top_k,
            periodo_actual
        )
        
        if not similar_periods:
            return "No hay contexto histórico disponible."
        
        # Construir texto de contexto
        context_parts = []
        for i, period in enumerate(similar_periods, 1):
            # Obtener el contenido del periodo
            if period['tipo'] == 'report':
                report = self.session.query(Report).get(period['referencia_id'])
                if report:
                    resumen = report.contenido.get('resumen_ejecutivo', {}).get('contexto', '')
                    context_parts.append(f"Periodo {period['periodo']}: {resumen[:300]}")
        
        return "\n\n".join(context_parts) if context_parts else "Contexto histórico limitado."
    
    def create_report_embedding(self, report_id: int):
        """
        Crea embedding para un report completo
        
        Args:
            report_id: ID del report
        """
        report = self.session.query(Report).get(report_id)
        if not report:
            return
        
        # Extraer texto representativo del report
        contenido = report.contenido
        texto_embedding = ""
        
        if 'resumen_ejecutivo' in contenido:
            texto_embedding += " ".join(contenido['resumen_ejecutivo'].get('hallazgos_clave', []))
        
        if 'mercado' in contenido:
            texto_embedding += " " + contenido['mercado'].get('estado_general', '')
        
        # Crear embedding
        self.create_embedding(
            categoria_id=report.categoria_id,
            periodo=report.periodo,
            tipo='report',
            referencia_id=report.id,
            texto=texto_embedding,
            metadata={'report_estado': report.estado}
        )

