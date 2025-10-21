"""
Seed Data - Mercado Salud
Mercado de Salud con varias categorías: Hospitales, Farmacéuticas, Seguros, Dispositivos, Telemedicina, Clínicas, Laboratorios
"""

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Query, Marca


def seed_health_market():
    """Recrea el mercado Salud enfocándolo en Programas Online de Pérdida de Peso"""
    with get_session() as session:
        # 1) Si ya existe el mercado Salud, eliminarlo para reemplazar su contenido
        existing = session.query(Mercado).filter_by(nombre="Salud").first()
        if existing:
            print(f"↻ Reemplazando mercado Salud (ID: {existing.id})")
            session.delete(existing)
            session.flush()

        # 2) Crear mercado Salud enfocado en pérdida de peso online
        mercado = Mercado(
            nombre="Salud",
            descripcion="Programas médicos online para pérdida de peso (GLP-1, seguimiento multidisciplinar)",
            tipo_mercado="Health_Digital",
            activo=True,
        )
        session.add(mercado)
        session.flush()
        print(f"✓ Mercado Salud creado (ID: {mercado.id})")

        # 3) Crear única categoría enfocada
        categoria = Categoria(
            mercado_id=mercado.id,
            nombre="Pérdida de Peso Online",
            descripcion="Programas y clínicas médicas digitales para adelgazar con seguimiento",
            activo=True,
        )
        session.add(categoria)
        session.flush()
        print(f"  ✓ Categoría {categoria.nombre} creada (ID: {categoria.id})")

        # 4) Marcas específicas proporcionadas por el usuario
        marcas = [
            # Líderes
            ("Drop by Sanitas", "lider", [
                "Drop by Sanitas", "Drop", "Sanitas Drop", "Drop Sanitas"
            ]),

            # Competidores
            ("OBEcentro (TAMO)", "competidor", [
                "OBEcentro", "OBE centro", "TAMO", "OBECentro TAMO"
            ]),
            ("Clínica Pérdida de peso by mediQuo", "competidor", [
                "mediQuo", "mediQuo pérdida de peso", "clinica perdida de peso mediquo"
            ]),
            ("Nutriclinic", "competidor", [
                "Nutriclinic", "Nutri Clinic", "nutriclinic"
            ]),

            # Emergentes
            ("Beyondbmi", "emergente", [
                "Beyondbmi", "Beyond BMI", "beyond bmi"
            ]),
            ("InMuv", "emergente", [
                "InMuv", "In Muv", "inmuv"
            ]),
            ("Endocrinos Online (Doctoralia)", "emergente", [
                "Endocrinos Online", "Doctoralia Endocrino", "Endocrino online Doctoralia", "Doctoralia"
            ]),
        ]
        for n, t, a in marcas:
            session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))

        # 5) Queries proporcionadas por el usuario
        queries = [
            "tratamiento médico para bajar de peso online",
            "programa médico para adelgazar con seguimiento online",
            "aplicaciones o programa para adelgazar con control médico sin ir a consulta",
            "programa digital para tratar la obesidad",
            "unidad médica de obesidad online",
            "adelgazar con endocrino online",
            "tratamiento con semaglutida o GLP-1 en España online",
            "clínicas o programas online que recetan Ozempic o Wegovy",
            "programa online con médico, nutricionista y psicólogo para perder peso",
            "mejor clínica médica para perder peso en España con programas online",
        ]
        for q in queries:
            session.add(
                Query(
                    categoria_id=categoria.id,
                    pregunta=q,
                    activa=True,
                    frecuencia="weekly",
                    proveedores_ia=["openai", "anthropic", "google", "perplexity"],
                )
            )
        print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")
        session.commit()
        print("\n✅ Seed Salud (Pérdida de Peso Online) completado exitosamente")


if __name__ == "__main__":
    seed_health_market()


