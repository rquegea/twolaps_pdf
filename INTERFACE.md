# Interfaz Web - TwoLaps Intelligence Platform

Guía completa de la interfaz web interactiva construida con Streamlit.

## 🚀 Inicio Rápido

```bash
# Opción 1: Comando directo
streamlit run app.py

# Opción 2: Script de inicio
./start_interface.sh      # Mac/Linux
start_interface.bat       # Windows
```

**URL**: http://localhost:8501

---

## 📱 Páginas y Funcionalidades

### 🏠 **Dashboard Principal**

**Qué muestra:**
- 4 métricas clave en cards:
  - Número de mercados activos
  - Número de categorías activas
  - Queries activas totales
  - Informes generados
- Estadísticas de ejecuciones del mes actual:
  - Total de ejecuciones
  - Distribución por proveedor (OpenAI, Anthropic, Google)
- Dashboard de costes:
  - Total gastado vs. presupuesto
  - Barra de progreso con alertas automáticas
- Últimas 10 ejecuciones con detalles
- Últimos 5 informes generados

**Uso típico:**
- Vista general del sistema al iniciar sesión
- Monitoreo rápido de costes
- Acceso rápido a informes recientes

---

### 📊 **Mercados & Categorías**

**Qué muestra:**
- Vista jerárquica expandible por mercado
- Para cada categoría:
  - Número de queries configuradas
  - Número de marcas monitoreadas
  - Número de informes generados

**Uso típico:**
- Entender la estructura completa del sistema
- Verificar qué categorías están configuradas
- Identificar categorías sin queries o marcas

**Ejemplo:**
```
📊 FMCG
  ├── Cervezas (8 queries, 10 marcas, 2 informes)
  ├── Refrescos (10 queries, 10 marcas, 1 informe)
  └── Rones (8 queries, 9 marcas, 0 informes)
```

---

### ❓ **Queries**

**Qué muestra:**
- Listado completo de todas las queries configuradas
- Filtros:
  - Por mercado (dropdown)
  - Por categoría (dropdown dinámico)
- Para cada query:
  - Texto de la pregunta
  - Frecuencia de ejecución (daily, weekly, monthly)
  - Proveedores configurados (openai, anthropic, google)
  - Última ejecución (fecha y hora)
  - Número total de ejecuciones históricas

**Uso típico:**
- Revisar qué preguntas están activas
- Verificar cuándo fue la última ejecución
- Identificar queries que nunca se han ejecutado
- Planificar nuevas queries basándose en las existentes

**Vista detallada:**
```
[FMCG/Cervezas] ¿Cuál es la mejor cerveza artesanal en 2025?
  Frecuencia: weekly
  Proveedores: openai, anthropic, google
  Última Ejecución: 2025-10-15 14:30
  Ejecuciones totales: 24
```

---

### 🏷️ **Marcas**

**Qué muestra:**
- Todas las marcas monitoreadas organizadas por categoría
- Clasificación en 3 tipos:
  - **Líderes**: Marcas dominantes del mercado
  - **Competidores**: Marcas establecidas
  - **Emergentes**: Marcas nuevas o en crecimiento
- Filtro por mercado

**Uso típico:**
- Verificar qué marcas se están monitoreando
- Asegurar que no falta ninguna marca importante
- Planificar adición de nuevas marcas

**Ejemplo visual:**
```
🏷️ FMCG/Cervezas
  Líderes:          Competidores:     Emergentes:
  • Heineken        • Amstel          • La Virgen
  • Corona          • Cruzcampo       • Moritz
  • Mahou           • San Miguel
```

---

### 🤖 **Ejecuciones**

**Qué muestra:**
- Historial completo de ejecuciones de queries
- **Filtros avanzados:**
  - Últimos: 1, 7, 30, 90 días
  - Por proveedor (Todos, openai, anthropic, google)
  - Límite de resultados (10-1000)
- **Estadísticas agregadas:**
  - Coste total del filtro seleccionado
  - Tokens totales (entrada + salida)
  - Latencia media en milisegundos
  - Número total de ejecuciones
- **Tabla detallada** con:
  - ID de ejecución
  - Texto de la query (truncado)
  - Proveedor y modelo usado
  - Timestamp
  - Tokens in/out
  - Coste individual
  - Latencia

**Uso típico:**
- Auditar ejecuciones recientes
- Identificar queries costosas
- Analizar rendimiento por proveedor
- Verificar que el sistema está ejecutando correctamente

**Métricas ejemplo:**
```
Últimos 30 días - OpenAI
Coste Total: $45.23
Tokens Totales: 1,234,567
Latencia Media: 2,340ms
Total: 234 ejecuciones
```

---

### 📈 **Análisis**

**Qué muestra:**
- Resultados de los 7 agentes de análisis por periodo
- Filtros por mercado y categoría
- Agrupación por periodo (YYYY-MM)
- **Para cada periodo:**
  - Lista de agentes ejecutados
  - Métricas clave por agente:
    
    **Quantitative:**
    - Total de menciones
    - Marcas mencionadas
    - Tabla de SOV (Share of Voice) por marca
    
    **Sentiment:**
    - Sentimiento global (-1 a 1)
    
    **Competitive:**
    - Marca líder identificada
    
    **Strategic:**
    - Número de oportunidades detectadas
    - Número de riesgos identificados

**Uso típico:**
- Revisar análisis antes de generar informe
- Verificar que todos los agentes ejecutaron correctamente
- Comparar métricas entre periodos
- Entender el SOV actual

**Ejemplo visual:**
```
📅 2025-10 (Agentes ejecutados: 7)

Quantitative:
  Total Menciones: 247
  Marcas Mencionadas: 8
  
  Share of Voice:
  Heineken    35.2%
  Corona      28.3%
  Mahou       15.1%
  ...

Sentiment:
  Sentimiento Global: 0.72

Strategic:
  Oportunidades: 5
  Riesgos: 3
```

---

### 📄 **Informes**

**Qué muestra:**
- Listado de todos los informes generados
- Ordenados por fecha (más reciente primero)
- **Para cada informe:**
  - Mercado/Categoría
  - Periodo (YYYY-MM)
  - Estado:
    - ✅ Publicado
    - 📝 Borrador
  - Timestamp de generación
  - Disponibilidad de PDF
  - Generado por (versión del agente ejecutivo)
  - **Métricas de calidad:**
    - Número de hallazgos
    - Número de oportunidades
    - Número de riesgos
    - Número de acciones en plan 90 días
  - **Preview del resumen ejecutivo:**
    - Hallazgos clave (bullets)

**Uso típico:**
- Revisar informes generados
- Verificar calidad de los informes
- Acceder a PDFs generados
- Identificar informes que necesitan regeneración

**Ejemplo:**
```
📄 FMCG/Cervezas - 2025-10
  Estado: ✅ Publicado
  Generado: 2025-10-17 15:45
  PDF: ✅ Disponible
  Generado por: executive_agent_v1.0
  
  Métricas de Calidad:
  Hallazgos: 5  Oportunidades: 4  Riesgos: 3  Plan Acciones: 5
  
  Resumen Ejecutivo:
  • Heineken mantiene liderazgo con 35% SOV
  • Corona muestra tendencia positiva (+5% vs mes anterior)
  • Detectada oportunidad en segmento premium
  ...
```

---

### 💰 **Costes**

**Qué muestra:**
- **Dashboard del mes actual:**
  - Total gastado (USD)
  - Presupuesto configurado (USD)
  - Porcentaje usado
  - Restante
  - Barra de progreso visual
  - **Alertas automáticas:**
    - Verde: < 60% usado ✅
    - Amarillo: 60-80% usado ⚠️
    - Rojo: > 80% usado 🚨

- **Desglose por proveedor:**
  - Tabla con costes individuales
  - Porcentaje del total por proveedor
  - Gráfico de barras comparativo

**Uso típico:**
- Monitorear gastos mensuales
- Prevenir sobrecostes
- Optimizar uso de proveedores
- Justificar presupuesto

**Ejemplo visual:**
```
💰 Mes Actual (2025-10)

Total Gastado: $245.30
Presupuesto: $500.00
Usado: 49.1%
Restante: $254.70

[===============>                ] 49.1%

✅ Presupuesto bajo control

Por Proveedor:
OpenAI      $120.45   49%
Anthropic   $95.20    39%
Google      $29.65    12%
```

---

### ⚙️ **Ejecutar**

**Funcionalidad principal**: Lanzar acciones directamente desde la interfaz.

#### **Tab 1: Ejecutar Queries** 🤖

**Qué hace:**
- Ejecuta todas las queries activas de una categoría
- Contra todos los proveedores configurados
- Guarda respuestas en base de datos
- Calcula y registra costes

**Pasos:**
1. Seleccionar Mercado (dropdown)
2. Seleccionar Categoría (dropdown)
3. Hacer clic en "🚀 Ejecutar Queries"
4. **Resultado:**
   - Spinner mientras ejecuta
   - Mensaje de éxito
   - 3 métricas:
     - Queries ejecutadas
     - Respuestas obtenidas (queries × proveedores)
     - Coste total

**Ejemplo de uso:**
```
Mercado: FMCG
Categoría: Cervezas

[🚀 Ejecutar Queries]

⏳ Ejecutando queries...

✅ Ejecución completada!
  Queries Ejecutadas: 8
  Respuestas Obtenidas: 24
  Coste Total: $0.4521
```

#### **Tab 2: Generar Informe** 📄

**Qué hace:**
- Ejecuta los 7 agentes de análisis en secuencia
- Lee las respuestas de la BD del periodo seleccionado
- Genera síntesis consultiva con el agente ejecutivo
- Crea PDF profesional de 15-20 páginas
- Guarda todo en base de datos

**Pasos:**
1. Seleccionar Mercado
2. Seleccionar Categoría
3. Ingresar Periodo (YYYY-MM)
4. Hacer clic en "📄 Generar Informe"
5. **Proceso (varios minutos):**
   - Análisis cuantitativo
   - Análisis de sentimiento (con LLM)
   - Análisis de atributos
   - Análisis competitivo
   - Detección de tendencias
   - Análisis estratégico
   - Síntesis ejecutiva
   - Generación de PDF
6. **Resultado:**
   - Report ID
   - Ruta del PDF generado

**Tiempo estimado:**
- Análisis: 2-3 minutos
- Generación PDF: 10-30 segundos
- **Total: 3-4 minutos**

**Ejemplo de uso:**
```
Mercado: FMCG
Categoría: Cervezas
Periodo: 2025-10

[📄 Generar Informe]

⏳ Generando informe... Esto puede tardar varios minutos

  Ejecutando análisis multi-agente...
  ✓ Quantitative
  ✓ Sentiment
  ✓ Attributes
  ✓ Competitive
  ✓ Trends
  ✓ Strategic
  ✓ Executive

  Generando PDF...

✅ Análisis completado (Report ID: 123)
✅ Informe generado exitosamente!
📁 data/reports/FMCG_Cervezas_2025-10.pdf
```

---

## 🎨 Características de UX

### **Estilos Visuales**
- Gradient cards para métricas importantes
- Color coding:
  - Verde: Éxito, valores positivos
  - Amarillo: Advertencias
  - Rojo: Errores, alertas críticas
  - Azul: Acciones primarias
- Iconos emoji para mejor navegación
- Cards expandibles para información detallada

### **Responsividad**
- Layout de columnas que se adapta
- Tablas con scroll horizontal
- Métricas en grids responsivos

### **Interactividad**
- Filtros dinámicos en tiempo real
- Dropdowns dependientes (mercado → categoría)
- Botones con spinners durante procesamiento
- Progress bars para operaciones largas
- Expandables para detalles bajo demanda

---

## 💡 Tips de Uso

### **Para Monitoreo Diario:**
1. Ir a 🏠 Dashboard
2. Revisar costes del mes
3. Ver últimas ejecuciones
4. Verificar alertas

### **Para Análisis de Datos:**
1. Ir a 📈 Análisis
2. Seleccionar categoría
3. Revisar métricas por agente
4. Comparar periodos

### **Para Generar Informes:**
1. Primero ejecutar queries en ⚙️ Ejecutar
2. Esperar a que terminen (ver en 🤖 Ejecuciones)
3. Luego generar informe en ⚙️ Ejecutar
4. Revisar resultado en 📄 Informes

### **Para Gestión de Costes:**
1. Ir a 💰 Costes
2. Revisar progreso vs presupuesto
3. Analizar distribución por proveedor
4. Ajustar frecuencias si es necesario

---

## ⚙️ Configuración Avanzada

### **Puerto Personalizado**
```bash
streamlit run app.py --server.port=8502
```

### **Acceso Remoto**
```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

### **Sin Auto-Abrir Navegador**
```bash
streamlit run app.py --server.headless=true
```

---

## 🐛 Troubleshooting

### **Error: "No module named streamlit"**
```bash
pip install streamlit plotly
```

### **Puerto 8501 ocupado**
```bash
streamlit run app.py --server.port=8502
```

### **Base de datos no conecta**
- Verificar que PostgreSQL está corriendo
- Verificar `DATABASE_URL` en `.env`
- Probar: `python main.py test-db`

### **No se ven datos**
- Verificar que has ejecutado: `python main.py admin seed-fmcg`
- Verificar que hay ejecuciones de queries
- Refrescar la página (F5)

---

## 🚀 Ventajas de la Interfaz

✅ **No necesitas memorizar comandos CLI**  
✅ **Visualización inmediata de datos**  
✅ **Ejecución de tareas con un clic**  
✅ **Monitoreo de costes en tiempo real**  
✅ **Filtros y búsquedas interactivas**  
✅ **No requiere conocimientos técnicos**  
✅ **Ideal para presentaciones y demos**  

---

**¿Listo para explorar?** 🎉

```bash
streamlit run app.py
```

