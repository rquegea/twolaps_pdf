"""
Script para generar embeddings para QueryExecution existentes (migración histórica)
Ejecutar tras limpieza o cuando se active RAG por primera vez.
"""

from src.database.connection import get_session
from src.database.models import QueryExecution, Query, Embedding
from src.query_executor.api_clients import OpenAIClient
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


def migrate_embeddings():
    with get_session() as session:
        # IDs de ejecuciones que ya tienen embedding
        existing_embeddings = session.query(Embedding.referencia_id).filter(
            Embedding.tipo == 'query_execution'
        ).all()
        existing_ids = {e[0] for e in existing_embeddings}

        # Ejecuciones candidatas sin embedding
        executions = session.query(QueryExecution).filter(
            QueryExecution.respuesta_texto.isnot(None)
        ).all()

        # Filtrar las ya migradas
        executions = [e for e in executions if e.id not in existing_ids]

        if not executions:
            print("✅ Todas las QueryExecution ya tienen embeddings!")
            return

        print(f"📊 Encontradas {len(executions)} QueryExecution sin embeddings")
        print("⏳ Generando embeddings... (esto puede tardar)")

        client = OpenAIClient()
        success = 0
        errors = 0

        for i, execution in enumerate(executions, 1):
            try:
                query = session.query(Query).get(execution.query_id)
                if not query:
                    continue

                text = execution.respuesta_texto or ""
                if len(text) > 8000:
                    text = text[:8000]

                vector = client.generate_embedding(text)
                periodo = execution.timestamp.strftime('%Y-%m')

                embedding = Embedding(
                    categoria_id=query.categoria_id,
                    periodo=periodo,
                    tipo='query_execution',
                    referencia_id=execution.id,
                    vector=vector,
                    metadata={
                        'query_id': query.id,
                        'proveedor_ia': execution.proveedor_ia,
                        'modelo': execution.modelo,
                        'migrated': True
                    }
                )
                session.add(embedding)
                success += 1

                if i % 10 == 0:
                    session.commit()
                    print(f"✓ Procesadas {i}/{len(executions)} (exitosas: {success})")

            except Exception as e:
                errors += 1
                logger.error(f"Error con execution {execution.id}: {e}")
                continue

        session.commit()

        print("\n🎉 Migración completada!")
        print(f"   ✅ Exitosas: {success}")
        print(f"   ❌ Errores: {errors}")


if __name__ == "__main__":
    migrate_embeddings()


