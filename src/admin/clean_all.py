"""
Limpieza TOTAL de datos para reiniciar el pipeline desde cero.
CUIDADO: borra QueryExecution, AnalysisResult, Report y Embedding.
"""

from src.database.connection import get_session
from src.database.models import QueryExecution, AnalysisResult, Report, Embedding


def clean_all():
    with get_session() as session:
        # Borrar en orden por dependencias
        deleted_embeddings = session.query(Embedding).delete()
        deleted_reports = session.query(Report).delete()
        deleted_analysis = session.query(AnalysisResult).delete()
        deleted_executions = session.query(QueryExecution).delete()

        session.commit()

        print("✅ Limpieza TOTAL completada:")
        print(f"   - QueryExecution borradas: {deleted_executions}")
        print(f"   - Análisis borrados: {deleted_analysis}")
        print(f"   - Reportes borrados: {deleted_reports}")
        print(f"   - Embeddings borrados: {deleted_embeddings}")
        print("\n🚀 Ahora puedes reejecutar las queries desde cero!")


if __name__ == "__main__":
    try:
        confirm = input("⚠️  ¿Estás SEGURO de borrar TODO? (escribe 'SI' para confirmar): ")
    except Exception:
        confirm = "NO"
    if confirm == "SI":
        clean_all()
    else:
        print("❌ Operación cancelada")


