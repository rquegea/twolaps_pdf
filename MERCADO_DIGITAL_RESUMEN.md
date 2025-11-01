# 🌐 MERCADO DIGITAL - TELEFONÍA MÓVIL

## ✅ CREACIÓN EXITOSA

Se ha creado el nuevo mercado **Digital** con la categoría **Telefonía Móvil**.

---

## 📊 RESUMEN DE LA CONFIGURACIÓN

### **Mercado**
- **Nombre:** Digital
- **Tipo:** Services
- **Descripción:** Mercado de servicios digitales y telecomunicaciones

### **Categoría**
- **Nombre:** Telefonía Móvil
- **Descripción:** Operadores móviles (MNOs y OMVs), tarifas, convergencia, 5G

---

## 📱 OPERADORES CONFIGURADOS (11 total)

### **Operadores con Red Propia (MNOs) - 4**
| Operador | Tipo | Aliases |
|----------|------|---------|
| **Movistar** | Líder | Movistar, Telefónica, movistar |
| **Orange** | Líder | Orange, orange |
| **Vodafone** | Líder | Vodafone, vodafone |
| **Grupo MásMóvil** | Competidor | MásMóvil, Masmovil, Mas Movil, Yoigo, yoigo |

### **Operadores Móviles Virtuales (OMVs) y Segundas Marcas - 7**
| Operador | Tipo | Aliases |
|----------|------|---------|
| **Digi** | Emergente | Digi, digi, Digi Mobil |
| **O2** | Competidor | O2, o2 |
| **Lowi** | Competidor | Lowi, lowi |
| **Jazztel** | Competidor | Jazztel, jazztel |
| **Simyo** | Competidor | Simyo, simyo |
| **Pepephone** | Competidor | Pepephone, pepephone |
| **Finetwork** | Emergente | Finetwork, finetwork |

---

## 📋 QUERIES CONFIGURADAS (39 total)

Las queries cubren los siguientes aspectos estratégicos:

### **1. Posicionamiento y Percepción (5 queries)**
- Posicionamiento de operadores principales
- Popularidad de tarifas (OMV, ilimitadas, low cost)
- Diferenciación premium vs OMV
- Reputación de calidad de red
- Mejor experiencia global

### **2. Comportamiento del Consumidor (5 queries)**
- Elección de tarifas premium vs low cost
- Preferencias de jóvenes (millennials, Gen Z)
- Voz del cliente (palabras, emociones)
- Barreras de entrada (permanencia, coste)
- Influencia del terminal y app

### **3. Marketing y Campañas (4 queries)**
- Campañas y patrocinios memorables
- Uso de influencers y patrocinios
- Comunicación digital innovadora
- Percepción de ofertas exclusivas

### **4. Canales de Distribución (3 queries)**
- Experiencia online vs tiendas físicas
- Distribuidores de terminales de gama alta
- Quejas sobre disponibilidad y servicio

### **5. Tendencias e Innovación (3 queries)**
- Tendencias emergentes 2025-2026
- Sostenibilidad y responsabilidad social
- Innovaciones futuras (IA, 6G)

### **6. Datos de Mercado (4 queries)**
- Tamaño del mercado en España
- Tasa de crecimiento (CAGR)
- Cuota de mercado por operador
- ARPU (Ingreso Medio por Usuario)

### **7. Customer Journey (3 queries)**
- Fuentes de información pre-compra
- Tiempo de consideración
- Factores de recomendación

### **8. Segmentación (3 queries)**
- Heavy buyers (usuarios de alto valor)
- Segmentos de crecimiento
- Ticket promedio (ARPU)

### **9. Ventajas Competitivas (3 queries)**
- Barreras de entrada
- Lealtad y switching
- Procesos con ventajas exclusivas

### **10. Pricing Power (3 queries)**
- Justificación de precios premium
- Precio psicológico máximo
- Percepción de sobrevaloración

### **11. Amenazas y Riesgos (3 queries)**
- Amenazas futuras (regulación, consolidación)
- Competencia de WiFi, apps, satelital
- Impacto de inflación y costes

---

## 🚀 CONFIGURACIÓN

- **Frecuencia:** Mensual
- **Proveedores IA:** 4 (OpenAI, Anthropic, Google, Perplexity)
- **Total de ejecuciones por mes:** 39 queries × 4 proveedores = **156 ejecuciones/mes**

---

## 💡 SIGUIENTE PASOS

### **1. Ejecutar Queries por Primera Vez**
```bash
cd /Users/macbook/Desktop/twolaps_informe

# Ejecutar queries para el mes actual (2025-10)
python main.py run-queries -c "Digital/Telefonía Móvil"
```

### **2. Generar Análisis**
```bash
# Ejecutar todos los agentes de análisis
python main.py analyze -c "Digital/Telefonía Móvil" -p "2025-10"
```

### **3. Generar Informe PDF**
```bash
# Generar informe completo con gráficos
python main.py generate-report -c "Digital/Telefonía Móvil" -p "2025-10"
```

### **4. Generar Solo Gráficos**
```bash
# Generar solo los gráficos sin PDF
python scripts/generate_charts_only.py -c "Digital/Telefonía Móvil" -p "2025-10"
```

### **5. Ver Análisis en JSON**
```bash
# Ver análisis de un agente específico
python main.py preview-agents -c "Digital/Telefonía Móvil" -p "2025-10" -a quantitative
python main.py preview-agents -c "Digital/Telefonía Móvil" -p "2025-10" -a strategic
```

---

## 📁 UBICACIÓN DE ARCHIVOS

### **Script de Seed**
```
src/admin/seed_digital.py
```

### **Reportes Generados**
```
data/reports/Digital_Telefonía_Móvil_YYYY-MM.pdf
```

### **Gráficos Generados**
```
data/reports/charts/Digital_Telefonía Móvil_YYYY-MM/
├── sov_chart.png
├── sov_pie_chart.png
├── sov_trend_chart.png
├── sentiment_chart.png
├── customer_journey.png
├── attribute_radar.png
├── competitive_positioning.png
├── perceptual_map.png
├── bcg_matrix.png
├── opportunity_matrix.png
├── scenario_waterfall.png
├── innovation_timeline.png
├── channel_comparison.png
└── esg_leadership.png
```

### **CSV de Competidores**
```
lista_competidores_actualizada.csv
```

---

## 🔧 COMANDOS ÚTILES

### **Listar Competidores**
```bash
# Ver resumen en terminal
python listar_competidores.py resumen | grep -A 15 "Digital"

# Exportar a CSV
python listar_competidores.py csv > operadores_moviles.csv
```

### **Verificar Queries**
```bash
python -c "
from src.database.connection import get_session
from src.database.models import Query, Categoria, Mercado

with get_session() as session:
    cat = session.query(Categoria).join(Mercado).filter(
        Mercado.nombre == 'Digital',
        Categoria.nombre == 'Telefonía Móvil'
    ).first()
    queries = session.query(Query).filter_by(categoria_id=cat.id).all()
    for i, q in enumerate(queries, 1):
        print(f'{i}. {q.pregunta}')
"
```

### **Ver Estado de Ejecuciones**
```bash
# Ver última ejecución de queries
python main.py preview-agents -c "Digital/Telefonía Móvil" -p "2025-10"
```

---

## 📈 ESTIMACIÓN DE COSTES

### **Por Ejecución Mensual**
- **Queries:** 39
- **Proveedores:** 4 (OpenAI, Anthropic, Google, Perplexity)
- **Total ejecuciones:** 156/mes

**Coste estimado:**
- OpenAI GPT-4: ~$0.02/query × 39 = ~$0.78
- Anthropic Claude: ~$0.015/query × 39 = ~$0.59
- Google Gemini: ~$0.01/query × 39 = ~$0.39
- Perplexity Sonar: ~$0.005/query × 39 = ~$0.20

**Total por mes:** ~$1.96 USD (~1.85 EUR)

**Con análisis + PDF:** ~$3-5 USD/mes (~2.80-4.70 EUR)

---

## ✅ VERIFICACIÓN

Para verificar que todo se creó correctamente:

```bash
# 1. Verificar mercado
python listar_competidores.py resumen | grep "Digital"

# 2. Verificar queries
python main.py preview-agents -c "Digital/Telefonía Móvil" -p "2025-10"

# 3. Listar todos los mercados
python -c "
from src.database.connection import get_session
from src.database.models import Mercado

with get_session() as session:
    mercados = session.query(Mercado).all()
    print('Mercados disponibles:')
    for m in mercados:
        print(f'  - {m.nombre} ({m.tipo_mercado})')
"
```

---

## 🎉 ¡LISTO PARA USAR!

El mercado **Digital** con la categoría **Telefonía Móvil** está completamente configurado y listo para ejecutar queries y generar análisis estratégicos de los operadores móviles en España.



