#!/usr/bin/env python
"""
Seed del mercado Digital con categorías de telefonía móvil
"""

import sys
sys.path.insert(0, '/Users/macbook/Desktop/twolaps_informe')

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Marca, Query
from sqlalchemy import select


def seed_telefonia_movil(session, categoria):
    """Seed categoría Telefonía Móvil"""
    print("\n  📱 Seeding Telefonía Móvil...")
    
    # Marcas - Operadores con Red Propia (MNOs)
    marcas_mnos = [
        ("Movistar", "lider", ["Movistar", "Telefónica", "movistar"]),
        ("Orange", "lider", ["Orange", "orange"]),
        ("Vodafone", "lider", ["Vodafone", "vodafone"]),
        ("Grupo MásMóvil", "competidor", ["MásMóvil", "Masmovil", "Mas Movil", "Yoigo", "yoigo"]),
    ]
    
    # Operadores Móviles Virtuales (OMVs) y Segundas Marcas
    marcas_omvs = [
        ("Digi", "emergente", ["Digi", "digi", "Digi Mobil"]),
        ("O2", "competidor", ["O2", "o2"]),
        ("Lowi", "competidor", ["Lowi", "lowi"]),
        ("Jazztel", "competidor", ["Jazztel", "jazztel"]),
        ("Simyo", "competidor", ["Simyo", "simyo"]),
        ("Pepephone", "competidor", ["Pepephone", "pepephone"]),
        ("Finetwork", "emergente", ["Finetwork", "finetwork"]),
    ]
    
    marcas = marcas_mnos + marcas_omvs
    
    # Insertar marcas
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    preguntas = [
        # POSICIONAMIENTO Y PERCEPCIÓN
        "Describe el posicionamiento percibido de los principales operadores móviles en España en 2025. ¿Cuáles son sus fortalezas (cobertura 5G, gigas, precio, servicio al cliente, ecosistema) y debilidades clave según los usuarios?",
        "¿Qué operador o tipo de tarifa (ej. OMV como Digi, tarifa 'ilimitada', 'low cost') está ganando más popularidad o cuota de conversación recientemente y por qué?",
        "Más allá del precio, ¿qué diferencia realmente a un operador premium (Movistar, Orange) de un OMV (Digi, Lowi) o una marca digital (O2, Simyo)? (Calidad de red, servicio técnico, tiendas físicas, TV).",
        "¿Cómo se compara la reputación y percepción de calidad de red/servicio al cliente de los operadores tradicionales frente a los OMV en el segmento de alto valor (convergentes con fibra y TV)?",
        "¿Qué operador ofrece la mejor experiencia global (velocidad 5G, latencia, fiabilidad cobertura, app de gestión, servicio técnico, ecosistema de servicios) para un profesional o una familia?",
        
        # COMPORTAMIENTO DEL CONSUMIDOR
        "¿En qué ocasiones específicas los usuarios eligen tarifas premium convergentes en lugar de opciones 'solo móvil' o 'low cost'? ¿Qué impulsa esa decisión (fútbol, teletrabajo, gaming, financiación terminal)?",
        "¿Qué buscan los consumidores más jóvenes (millennials, Gen Z) cuando contratan una tarifa móvil? ¿Valoran más los gigas ilimitados (TikTok/Twitch), el precio bajo, la financiación de terminales o la eSIM?",
        "Describe la \"voz del cliente\" sobre telefonía móvil: ¿qué palabras (ej. gigas, cobertura, 5G, fibra, permanencia, precio final, \"me han subido el precio\", servicio técnico, IA), emociones o asociaciones son comunes al hablar de marcas líderes?",
        "¿Cuáles son las principales barreras (permanencia, coste de financiación del terminal, complejidad de tarifas, mala cobertura rural, mal servicio técnico, dificultad portabilidad) por los que un consumidor no elegiría un operador o tardaría en cambiarse?",
        "¿Cómo influye el diseño del terminal (iPhone vs. Android), la facilidad de la app de gestión, el unboxing de un nuevo terminal o la facilidad de (e)SIM en la decisión de compra o permanencia?",
        
        # MARKETING Y CAMPAÑAS
        "¿Qué campañas de marketing o patrocinios (fútbol, F1, música) recientes de los operadores móviles han sido más memorables o comentados? ¿Qué mensaje (gigas ilimitados, velocidad 5G, precio 'para siempre', familia) transmitían?",
        "¿Cómo utilizan los operadores a influencers (YouTubers tech, streamers) o patrocinios (equipos, festivales) en su marketing? ¿Es efectivo?",
        "¿Qué operador tiene la comunicación más innovadora en canales digitales (app de gestión, TikTok, web (comparador tarifas), asistentes virtuales con IA)?",
        "¿Cuál es la percepción sobre las tarifas \"exclusivas\" (Black Friday, Verano) o los terminales de gama \"Pro/Ultra\" financiados? ¿Aportan valor real o son solo marketing/gancho?",
        
        # CANALES DE DISTRIBUCIÓN
        "¿Cuál es la experiencia de contratar online (web, app, OMV) versus en tiendas físicas de operador? ¿Dónde prefieren contratar los usuarios y por qué (asesoramiento, servicio técnico, tocar el terminal)?",
        "¿Qué distribuidores (tiendas de operador, MediaMarkt, TPH, Amazon, web del fabricante) se asocian más con la venta de terminales de alta gama? ¿Ofrecen buena experiencia de financiación/asesoramiento?",
        "¿Hay quejas sobre la disponibilidad (roturas de stock de iPhone/Galaxy), problemas de portabilidad, o largas esperas en el servicio técnico en los puntos de venta/atención habituales?",
        
        # TENDENCIAS E INNOVACIÓN
        "¿Cuáles son las principales tendencias emergentes en telefonía móvil para 2025-2026? (ej. auge de OMV (Digi), 5G real, eSIM, tarifas flexibles, IA en terminales, terminales plegables, WiFi 7).",
        "¿Qué se dice sobre la sostenibilidad (terminales reacondicionados, huella de carbono de la red, terminales 'eco', derecho a reparar) en relación con los grandes operadores y fabricantes? ¿Es un factor de decisión importante?",
        "¿Qué innovaciones (IA generativa en terminales, 6G, servicios de salud/finanzas/TV integrados, redes privadas 5G) podrían transformar el mercado de la telefonía móvil en los próximos años?",
        
        # DATOS DE MERCADO
        "¿Cuál es el tamaño estimado del mercado de telefonía móvil en España en 2024? (en millones de euros y total de líneas móviles/fibra).",
        "¿Cuál es la tasa de crecimiento anual (CAGR) estimada del mercado móvil en España 2024-2028? ¿Crece más el segmento OMV o el tradicional, prepago o contrato? Cita fuentes si es posible.",
        "¿Cuál es la cuota de mercado real (aproximada) de Movistar vs Orange vs Vodafone vs MásMóvil+Digi en España según fuentes externas (CNMC)?",
        "¿Cuál es el ARPU (Ingreso Medio por Usuario) medio del sector y cómo varía por operador (premium vs low cost) y canal (convergente vs solo móvil)?",
        
        # CUSTOMER JOURNEY
        "¿Dónde buscan información los usuarios antes de contratar una nueva tarifa o comprar un terminal? (Comparadores (Selectra, Comparaiso), Xataka, Andro4all, YouTube Tech, web del operador).",
        "¿Cuánto tiempo pasa desde la consideración (comparar tarifas) hasta la ejecución de la portabilidad o la compra del terminal?",
        "¿Qué hace que recomienden un operador específico a amigos/familiares? (Precio final sin sorpresas, no tener problemas técnicos, buen servicio al cliente, cobertura estable).",
        
        # SEGMENTACIÓN
        "¿Quiénes son los heavy buyers (usuarios de alto valor) de telefonía móvil en España? (Perfil: familias (packs convergentes), jóvenes (datos ilimitados), autónomos/empresas).",
        "¿Qué segmento está creciendo más: OMV 'low cost' (Digi) vs. Segundas Marcas (O2/Lowi), packs convergentes (fibra+móvil+TV), o solo móvil?",
        "¿Cuál es el ticket promedio de gasto mensual (ARPU) por cliente? ¿Y el coste medio de adquisición de un terminal financiado?",
        
        # VENTAJAS COMPETITIVAS
        "¿Qué barreras de entrada existen para competir contra operadores consolidados? (Red propia (coste espectro), infraestructura de fibra, red de tiendas físicas, marca).",
        "¿Qué tan leales son los usuarios a un operador o ecosistema (Apple vs Android)? ¿Qué genera switching? (Precio, permanencia (financiación), pack convergente (TV/Fútbol), mal servicio técnico).",
        "¿Existen procesos (calidad de red y latencia 5G, despliegue de fibra, software (ecosistema Apple/Google), capilaridad del servicio técnico) que representen ventajas exclusivas?",
        
        # PRICING POWER
        "¿Los usuarios perciben que el precio de las tarifas premium (Movistar/Orange con TV) está justificado? ¿Por qué? (Cobertura superior, gigas ilimitados, servicio técnico, TV (Fútbol), ecosistema).",
        "¿Cuál es el precio psicológico máximo por una tarifa \"ilimitada\" convergente? ¿Y por un terminal de gama alta financiado?",
        "¿Se perciben las tarifas premium como \"sobrevaloradas\" frente a las opciones 'low cost' (OMVs) que usan la misma red?",
        
        # AMENAZAS Y RIESGOS
        "¿Qué amenazas enfrenta el mercado móvil en los próximos años? (Regulación (UE), impuestos, consolidación del mercado (fusión Orange/MásMóvil), entrada agresiva de nuevos players (Digi)).",
        "¿Están las redes WiFi (WLAN públicas/privadas), las apps de mensajería (WhatsApp vs SMS/llamada) o la conectividad satelital (Starlink) restando valor/uso a las redes móviles tradicionales?",
        "¿Cómo impacta la inflación y el poder adquisitivo en la búsqueda de tarifas 'low cost'? ¿Y el coste energético o de despliegue del 5G en los márgenes de los operadores?"
    ]
    
    # Deep-dive semanal para explicar picos de sentimiento (Pepephone vs low cost)
    preguntas_deepdive = [
        # Incidencias de red / calidad de servicio
        "¿Se han reportado caídas o degradación de red móvil/fibra/5G asociadas a Pepephone, Digi o Lowi en los últimos 7 días? Detalla fecha, zona, síntoma y magnitud; incluye citas.",
        "¿Qué problemas de cobertura/velocidad/latencia se mencionan esta semana para Pepephone frente a Digi y Lowi? ¿Dónde y con qué frecuencia?", 

        # Facturación y precios
        "¿Qué quejas sobre facturación, subidas de precio, cargos inesperados o 'precio final' afectan a Pepephone (y competidores low cost) esta semana? Clasifica por tipo e impacto; incluye citas.",
        "¿Ha habido cambios de tarifa o promociones relevantes en Pepephone/Digi/Lowi esta semana y cómo afectan al sentimiento?",

        # Portabilidad
        "Experiencia de portabilidad hacia/desde Pepephone en los últimos 7 días: tiempos, rechazos, causas y comparación con Digi/Lowi; evidencias.",

        # Atención al cliente
        "Tiempos de espera, resolución al primer contacto y tono percibido en soporte (teléfono/chat/app/redes) para Pepephone vs Digi/Lowi esta semana; ejemplos concretos.",

        # App/eSIM/procesos
        "Feedback sobre la app de gestión, alta/baja y eSIM (errores, fricciones, mejoras) esta semana para Pepephone; compara con Digi/Lowi.",

        # Viralidad/campañas/eventos
        "¿Qué hilos virales, reseñas de alto alcance o campañas/mensajes han podido disparar el sentimiento (positivo/negativo) de Pepephone esta semana? Indica fechas y aporta citas.",

        # Medios/foros/comparadores
        "Resumen semanal en comparadores/medios/foros (Selectra, Comparaiso, Xataka, Reddit, Forocoches): puntos a favor/en contra de Pepephone vs Digi/Lowi con citas.",

        # Valor percibido (precio vs servicio)
        "¿Cómo justifican los usuarios su elección entre Pepephone y Digi/Lowi esta semana? Pondera precio, calidad de red, servicio, transparencia de facturación y portabilidad; incluye citas.",

        # Instalación/soporte técnico en hogar (fibra)
        "Experiencias de instalación/averías de fibra y soporte técnico en el hogar para Pepephone esta semana; tiempos, profesionalidad y resolución; compara con Digi/Lowi.",

        # Meta-explicación de picos
        "Explica los picos de sentimiento de Pepephone en los últimos 7 días: ¿qué eventos (incidencias, precios, portabilidad, campañas, cobertura) los causaron? Prioriza por impacto y evidencia.",

        # Riesgos y quick wins
        "Top riesgos reputacionales y quick wins de Pepephone detectados esta semana (3–5), con evidencia (citas) y recomendación accionable.",

        # Benchmark low cost
        "Comparativa semanal low cost: Pepephone vs Digi vs Lowi en sentimiento y drivers (precio, red, servicio, facturación, portabilidad). ¿Quién lidera cada driver y por qué?"
    ]
    
    # Insertar queries base (mensuales)
    for pregunta in preguntas:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="monthly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    # Insertar queries deep-dive (diarias) para detección de picos/causas
    for pregunta in preguntas_deepdive:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="daily",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas) + len(preguntas_deepdive)} queries")


def seed_mercado_digital():
    """Crea el mercado Digital con sus categorías"""
    print("\n" + "="*80)
    print("🌐 SEEDING MERCADO DIGITAL")
    print("="*80)
    
    with get_session() as session:
        # Verificar si ya existe el mercado Digital
        mercado = session.query(Mercado).filter_by(nombre="Digital").first()
        
        if mercado:
            print("\n⚠️  El mercado 'Digital' ya existe.")
            respuesta = input("¿Deseas recrearlo? (Se borrarán todos los datos existentes) [s/N]: ")
            if respuesta.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            # Borrar el mercado existente (cascade borrará categorías, marcas, queries)
            session.delete(mercado)
            session.commit()
            print("✓ Mercado anterior eliminado")
        
        # Crear mercado Digital
        mercado = Mercado(
            nombre="Digital",
            descripcion="Mercado de servicios digitales y telecomunicaciones",
            tipo_mercado="Services"
        )
        session.add(mercado)
        session.flush()  # Para obtener el ID
        
        print(f"\n✓ Mercado creado: {mercado.nombre} (ID: {mercado.id})")
        
        # Crear categoría Telefonía Móvil
        categoria = Categoria(
            mercado_id=mercado.id,
            nombre="Telefonía Móvil",
            descripcion="Operadores móviles (MNOs y OMVs), tarifas, convergencia, 5G"
        )
        session.add(categoria)
        session.flush()
        
        print(f"  ✓ Categoría creada: {categoria.nombre} (ID: {categoria.id})")
        
        # Seed la categoría
        seed_telefonia_movil(session, categoria)
        
        # Commit final
        session.commit()
        
        print("\n" + "="*80)
        print("✅ MERCADO DIGITAL CREADO EXITOSAMENTE")
        print("="*80)
        print(f"\n📊 Resumen:")
        print(f"   - Mercado: Digital")
        print(f"   - Categorías: 1 (Telefonía Móvil)")
        print(f"   - Operadores: 11 (4 MNOs, 7 OMVs/segundas marcas)")
        print(f"   - Queries: 38 (frecuencia mensual)")
        print(f"\n💡 Siguiente paso:")
        print(f"   python main.py run-queries -c \"Digital/Telefonía Móvil\"")
        print()


if __name__ == "__main__":
    seed_mercado_digital()

