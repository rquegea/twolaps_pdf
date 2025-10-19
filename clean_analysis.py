"""
Script para limpiar análisis antiguos y reports antes de reejecutar con nuevas estructuras
Uso: python clean_analysis.py [list|<cat_id> [periodo]|ALL]
"""
from src.database.connection import get_session
from src.database.models import AnalysisResult, Report, Categoria, Mercado

def clean_analysis_data(categoria_id: int = None, periodo: str = None):
    """
    Limpia datos de análisis y reports
    
    Args:
        categoria_id: ID de categoría específica (None = todas)
        periodo: Periodo específico YYYY-MM (None = todos)
    """
    with get_session() as session:
        if categoria_id and periodo:
            # Limpieza específica
            deleted_ar = session.query(AnalysisResult).filter_by(
                categoria_id=categoria_id,
                periodo=periodo
            ).delete()
            deleted_r = session.query(Report).filter_by(
                categoria_id=categoria_id,
                periodo=periodo
            ).delete()
            session.commit()
            print(f"✓ Borrados {deleted_ar} análisis y {deleted_r} reports")
            print(f"  Categoría: {categoria_id}, Periodo: {periodo}")
        
        elif categoria_id:
            # Solo categoría
            deleted_ar = session.query(AnalysisResult).filter_by(
                categoria_id=categoria_id
            ).delete()
            deleted_r = session.query(Report).filter_by(
                categoria_id=categoria_id
            ).delete()
            session.commit()
            print(f"✓ Borrados {deleted_ar} análisis y {deleted_r} reports")
            print(f"  Categoría: {categoria_id} (todos los periodos)")
        
        else:
            # Todo (¡CUIDADO!)
            deleted_ar = session.query(AnalysisResult).delete()
            deleted_r = session.query(Report).delete()
            session.commit()
            print(f"✓ Borrados {deleted_ar} análisis y {deleted_r} reports")
            print("  ⚠️  TODOS los datos de análisis")
        
        print("✅ Base de datos limpiada correctamente")

def list_categories():
    """Lista categorías disponibles con sus IDs"""
    with get_session() as session:
        categorias = session.query(Categoria).all()
        
        print("\n" + "="*60)
        print("📊 CATEGORÍAS DISPONIBLES")
        print("="*60 + "\n")
        
        for cat in categorias:
            mercado = session.query(Mercado).get(cat.mercado_id)
            
            # Contar análisis y reports
            num_analysis = session.query(AnalysisResult).filter_by(
                categoria_id=cat.id
            ).count()
            num_reports = session.query(Report).filter_by(
                categoria_id=cat.id
            ).count()
            
            print(f"  ID {cat.id}: {mercado.nombre}/{cat.nombre}")
            print(f"         └─ {num_analysis} análisis, {num_reports} reports")
        
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # Sin argumentos: mostrar ayuda
        print("="*60)
        print("🗑️  LIMPIADOR DE ANÁLISIS - TwoLaps Intelligence Platform")
        print("="*60)
        print("\n📖 USO:")
        print("  python clean_analysis.py list              # Ver categorías disponibles")
        print("  python clean_analysis.py <cat_id> <periodo> # Limpiar análisis específico")
        print("  python clean_analysis.py <cat_id>          # Limpiar toda la categoría")
        print("  python clean_analysis.py ALL               # Limpiar TODO (¡cuidado!)")
        
        print("\n✨ EJEMPLOS:")
        print("  python clean_analysis.py list")
        print("  python clean_analysis.py 1 2025-10         # Limpiar Categoría 1, periodo Oct 2025")
        print("  python clean_analysis.py 1                 # Limpiar toda la Categoría 1")
        print("  python clean_analysis.py ALL               # Limpiar todos los análisis")
        
        print("\n💡 RECOMENDACIÓN:")
        print("  1. Ejecuta 'list' para ver tus categorías")
        print("  2. Limpia solo el periodo que vas a regenerar")
        print("  3. Rejecuta el análisis con las nuevas estructuras")
        print()
    
    elif sys.argv[1].lower() == 'list':
        # Listar categorías
        list_categories()
    
    elif sys.argv[1].upper() == 'ALL':
        # Borrar todo con confirmación
        print("\n" + "⚠️ "*20)
        print("¡ADVERTENCIA! Esto borrará TODOS los análisis y reports de TODAS las categorías.")
        print("⚠️ "*20 + "\n")
        confirm = input("Escribe exactamente 'BORRAR TODO' para confirmar: ")
        if confirm == 'BORRAR TODO':
            clean_analysis_data()
        else:
            print("❌ Cancelado (no coincide la confirmación)")
    
    elif len(sys.argv) == 3:
        # python clean_analysis.py <cat_id> <periodo>
        try:
            cat_id = int(sys.argv[1])
            periodo = sys.argv[2]
            
            # Validar formato periodo
            if len(periodo) != 7 or periodo[4] != '-':
                print("❌ Formato de periodo incorrecto. Usa: YYYY-MM (ej: 2025-10)")
                sys.exit(1)
            
            print(f"\n🗑️  Limpiando análisis de Categoría {cat_id}, Periodo {periodo}...")
            clean_analysis_data(cat_id, periodo)
            
        except ValueError:
            print("❌ Error: El ID de categoría debe ser un número entero")
    
    elif len(sys.argv) == 2:
        # python clean_analysis.py <cat_id>
        try:
            cat_id = int(sys.argv[1])
            
            print(f"\n⚠️  Esto borrará TODOS los periodos de la Categoría {cat_id}")
            confirm = input("Escribe 'SI' para confirmar: ")
            
            if confirm == 'SI':
                clean_analysis_data(cat_id)
            else:
                print("❌ Cancelado")
                
        except ValueError:
            print("❌ Error: El ID de categoría debe ser un número entero")
    
    else:
        print("❌ Argumentos incorrectos.")
        print("Uso: python clean_analysis.py (sin argumentos para ver ayuda completa)")

