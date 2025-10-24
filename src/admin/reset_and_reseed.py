"""
Script para resetear y re-seed la base de datos
- Borra todas las ejecuciones, análisis, reportes y embeddings
- Borra todos los mercados, categorías, queries y marcas
- Re-seed completo con datos actualizados
"""

from src.admin.clean_all import clean_all
from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Query, Marca
from src.admin.seed_fmcg import seed_all_fmcg
from src.admin.seed_health import seed_health_market


def borrar_mercados_y_categorias():
    """Borra mercados, categorías, queries y marcas (en cascada)"""
    with get_session() as session:
        deleted_mercados = session.query(Mercado).delete()
        session.commit()
        print(f"✅ Mercados borrados: {deleted_mercados} (categorías, queries y marcas borradas en cascada)")


def reset_and_reseed():
    """Reseteo completo y re-seed"""
    print("=" * 80)
    print("🔄 RESET Y RE-SEED COMPLETO")
    print("=" * 80)
    
    # Paso 1: Limpiar todos los datos de ejecución
    print("\n📦 Paso 1: Limpiando datos de ejecución...")
    clean_all()
    
    # Paso 2: Borrar mercados y categorías
    print("\n🗑️  Paso 2: Borrando mercados, categorías y queries...")
    borrar_mercados_y_categorias()
    
    # Paso 3: Re-seed FMCG (con nuevas queries de champagne)
    print("\n🌱 Paso 3: Re-seed mercado FMCG...")
    seed_all_fmcg()
    
    # Paso 4: (desactivado) Re-seed mercado Salud
    # print("\n🌱 Paso 4: Re-seed mercado Salud...")
    # seed_health_market()
    
    print("\n" + "=" * 80)
    print("✅ RESET Y RE-SEED COMPLETADO EXITOSAMENTE")
    print("=" * 80)
    print("\n📊 Estado actual:")
    print("   ✓ Todos los mercados y categorías recreados")
    print("   ✓ Champagnes y categorías FMCG específicas con queries cargadas")
    print("   ✓ Listo para ejecutar queries desde cero (solo Champagne + nuevas categorías)")
    print("\n🚀 Siguiente paso: Ejecutar las queries con main.py o la interfaz")


if __name__ == "__main__":
    try:
        confirm = input("\n⚠️  ¿Estás SEGURO de resetear TODA la base de datos? (escribe 'SI' para confirmar): ")
    except Exception:
        confirm = "NO"
    
    if confirm == "SI":
        reset_and_reseed()
    else:
        print("❌ Operación cancelada")

