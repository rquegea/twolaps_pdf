# TwoLaps Intelligence Platform

Sistema automatizado de inteligencia competitiva que ejecuta queries a múltiples IAs (OpenAI, Anthropic, Google), analiza respuestas con agentes especializados y genera informes consultivos en PDF.

## 🚀 Características

- **Automatización completa**: Ejecuta queries periódicamente vía APIs
- **Multi-IA**: OpenAI GPT-4, Anthropic Claude, Google Gemini
- **Sistema multi-agente**: 7 agentes especializados de análisis
- **Share of Voice (SOV)**: Análisis cuantitativo de menciones
- **Análisis de sentimiento**: Con LLM para clasificación avanzada
- **RAG con contexto histórico**: Comparación entre periodos
- **Informes PDF profesionales**: Templates consultivos de alta calidad
- **Gestión de costes**: Tracking detallado de gastos por API

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 15+ con extensión pgvector
- API keys de OpenAI, Anthropic y/o Google

## 🔧 Instalación

### 1. Clonar y configurar entorno

```bash
cd twolaps_informe
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar PostgreSQL

```bash
# Crear base de datos
createdb twolaps

# Entrar a psql y habilitar pgvector
psql twolaps
CREATE EXTENSION vector;
\q
```

### 3. Configurar variables de entorno

```bash
cp env.example .env
```

Edita `.env` con tus credenciales:

```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/twolaps

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-7-sonnet-latest

GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-1.5-pro

MONTHLY_BUDGET_USD=500
```

### 4. Inicializar base de datos

```bash
# Crear tablas
python main.py init

# Verificar conexión
python main.py test-db
```

### 5. Poblar datos iniciales FMCG

```bash
# Crea mercado FMCG + 7 categorías + 60+ queries + 80+ marcas
python main.py admin seed-fmcg
```

Esto crea:
- **Mercado**: FMCG
- **Categorías**: Cervezas, Refrescos, Rones, Champagnes, Galletas, Cereales, Snacks
- **~60 queries** listas para ejecutar
- **~80 marcas** a monitorear

## 📖 Uso

### Ver estructura creada

```bash
python main.py admin list
```

Output:
```
📊 FMCG
  └── Cervezas (8 queries, 10 marcas)
  └── Refrescos (10 queries, 10 marcas)
  └── Rones (8 queries, 9 marcas)
  ...
```

### Ver queries de una categoría

```bash
python main.py admin show-queries -c "FMCG/Cervezas"
```

### Ejecutar queries manualmente

```bash
# Ejecutar todas las queries de Cervezas
python main.py execute-queries -c "FMCG/Cervezas"

# Output:
# ✓ Ejecución completada:
#   - Queries ejecutadas: 8
#   - Respuestas obtenidas: 24
#   - Coste total: $0.4521
```

### Generar informe

```bash
# Generar informe PDF para Octubre 2025
python main.py generate-report -c "FMCG/Cervezas" -p "2025-10"

# Output:
# 📊 Generando informe para: FMCG/Cervezas - 2025-10
# 🤖 Ejecutando análisis multi-agente...
#   ✓ Análisis completado (report_id: 1)
# 📄 Generando PDF...
# ✅ Informe generado exitosamente:
#   📁 data/reports/FMCG_Cervezas_2025-10.pdf
```

### Polling automático

```bash
# Ejecutar una vez
python main.py start-poller --once

# Ejecutar continuamente (corre indefinidamente)
python main.py start-poller
```

El poller:
- Revisa queries activas según su frecuencia (daily, weekly, monthly)
- Ejecuta solo las que toca según última ejecución
- Guarda todo en base de datos
- Tracking de costes automático

### Generar múltiples informes

```bash
# Generar informes para todas las categorías FMCG
python main.py generate-batch --all -p "2025-10"

# Generar solo para categorías específicas
python main.py generate-batch -c "FMCG/Cervezas" -c "FMCG/Refrescos" -p "2025-10"
```

## 🎯 Añadir Nueva Categoría

### Opción 1: Manualmente

```bash
# 1. Crear categoría
python main.py admin add-category --market "FMCG" --name "Vinos" --description "Vinos tintos y blancos"

# 2. Añadir marcas
python main.py admin add-brand -c "FMCG/Vinos" -n "Rioja" -t lider
python main.py admin add-brand -c "FMCG/Vinos" -n "Ribera del Duero" -t competidor

# 3. Añadir queries
python main.py admin add-query -c "FMCG/Vinos" -q "¿Cuál es el mejor vino tinto español?" -f weekly
python main.py admin add-query -c "FMCG/Vinos" -q "¿Rioja o Ribera? ¿Cuál es mejor?" -f weekly
```

### Opción 2: Programáticamente

Edita `src/admin/seed_fmcg.py` y añade tu función:

```python
def seed_vinos(session, categoria):
    marcas = [
        ("Rioja", "lider", ["Rioja", "rioja"]),
        ("Ribera del Duero", "competidor", ["Ribera", "ribera"]),
        # ...
    ]
    
    queries = [
        "¿Cuál es el mejor vino tinto español?",
        "¿Qué vino recomendarías para una cena?",
        # ...
    ]
    # ... (ver seed_cervezas como ejemplo)
```

## 📊 Estructura del Informe PDF

Los PDFs generados incluyen:

1. **Portada**: Título, categoría, periodo
2. **Resumen Ejecutivo**: 3-5 hallazgos clave
3. **Estado del Mercado**: Volumen, tendencias, temas
4. **Análisis Competitivo**: SOV, líder, comparativas
5. **Sentimiento y Reputación**: Análisis por marca
6. **Oportunidades y Riesgos**: 3-5 de cada con priorización
7. **Plan de Acción 90 Días**: Iniciativas priorizadas con QUÉ/POR QUÉ/CÓMO/CUÁNDO
8. **Anexos**: Metodología y métricas de calidad

## 💰 Gestión de Costes

### Ver costes del mes actual

```bash
python main.py admin costs
```

Output:
```
==================================================
REPORTE DE COSTES
==================================================

Total gastado: $245.30
Presupuesto: $500.00
Usado: 49.1%
Restante: $254.70

Por proveedor:
  openai: $120.45
  anthropic: $95.20
  google: $29.65
==================================================
```

### Ver costes de periodo específico

```bash
python main.py admin costs -p "2025-10" -c "FMCG/Cervezas"
```

## 🏗️ Arquitectura

### Flujo de Datos

```
1. INGESTA
   ├── Queries definidas en BD
   └── Poller ejecuta vía APIs → QueryExecution

2. ANÁLISIS (7 agentes en secuencia)
   ├── Quantitative: SOV, menciones, co-ocurrencias
   ├── Sentiment: Análisis con LLM
   ├── Attributes: Atributos FMCG
   ├── Competitive: Posicionamiento
   ├── Trends: Comparación histórica
   ├── Strategic: Oportunidades y riesgos
   └── Executive: Síntesis final → Report

3. GENERACIÓN PDF
   └── Report → Template HTML/CSS → PDF
```

### Stack Tecnológico

- **Backend**: Python 3.11+
- **Base de datos**: PostgreSQL 15+ con pgvector
- **ORM**: SQLAlchemy 2.0
- **LLMs**: OpenAI, Anthropic, Google SDKs
- **PDF**: WeasyPrint
- **CLI**: Click

## 🔍 Comandos Útiles

```bash
# Ver todas las categorías
python main.py admin list

# Ver queries de una categoría
python main.py admin show-queries -c "FMCG/Cervezas"

# Ver marcas de una categoría
python main.py admin show-brands -c "FMCG/Cervezas"

# Desactivar una query
python main.py admin toggle-query --id 42 --inactive

# Ver costes
python main.py admin costs

# Ejecutar queries manualmente
python main.py execute-queries -c "FMCG/Cervezas"

# Generar informe
python main.py generate-report -c "FMCG/Cervezas" -p "2025-10"

# Polling automático
python main.py start-poller --once  # Una vez
python main.py start-poller         # Continuo
```

## 📁 Estructura del Proyecto

```
twolaps_informe/
├── config/                    # Configuración
│   ├── settings.yaml
│   ├── prompts/
│   └── query_templates/
├── src/
│   ├── admin/                # CLI de administración
│   ├── analytics/            # Agentes de análisis
│   │   └── agents/          # 7 agentes especializados
│   ├── database/            # Modelos y conexión
│   ├── query_executor/      # Clientes API y poller
│   ├── reporting/           # Generador PDF
│   └── utils/               # Logger, cost tracker
├── data/
│   └── reports/             # PDFs generados
├── main.py                  # CLI principal
├── requirements.txt
└── README.md
```

## 🐛 Troubleshooting

### Error: "relation does not exist"

```bash
# Recrear tablas
python main.py init
```

### Error: "extension vector does not exist"

```bash
psql twolaps
CREATE EXTENSION vector;
```

### Error: API key inválida

Verifica tu archivo `.env` y asegúrate de que las API keys son correctas.

### Poller no ejecuta queries

Verifica que:
1. Las queries estén activas: `python main.py admin show-queries -c "..."`
2. Hayan pasado suficientes días desde última ejecución
3. Las API keys sean válidas

## 🌐 Interfaz Web

El sistema incluye una **interfaz web interactiva** con Streamlit para visualizar y gestionar todo desde el navegador.

### Iniciar la interfaz

```bash
# Forma simple
streamlit run app.py

# O usar el script de inicio
./start_interface.sh      # Mac/Linux
start_interface.bat       # Windows
```

La interfaz se abrirá automáticamente en: **http://localhost:8501**

### Funcionalidades de la Interfaz

#### 🏠 **Dashboard Principal**
- Métricas globales (mercados, categorías, queries, informes)
- Ejecuciones del mes actual
- Costes y presupuesto con alertas
- Últimas ejecuciones y informes generados

#### 📊 **Mercados & Categorías**
- Vista jerárquica de toda la estructura
- Estadísticas por categoría (queries, marcas, informes)

#### ❓ **Queries**
- Listado completo de queries configuradas
- Filtros por mercado y categoría
- Estado de ejecución de cada query
- Proveedores y frecuencia configurada

#### 🏷️ **Marcas**
- Todas las marcas monitoreadas por categoría
- Clasificación: Líderes, Competidores, Emergentes

#### 🤖 **Ejecuciones**
- Historial completo de ejecuciones
- Filtros por fecha, proveedor, límite
- Estadísticas de costes, tokens y latencia
- Vista detallada con tabla navegable

#### 📈 **Análisis**
- Resultados de análisis por periodo
- Vista de KPIs por agente
- SOV, sentimiento, oportunidades, riesgos
- Navegación por mercado y categoría

#### 📄 **Informes**
- Listado de informes generados
- Estado (publicado, borrador)
- Métricas de calidad
- Resumen ejecutivo

#### 💰 **Costes**
- Dashboard de costes del mes
- Progreso vs. presupuesto con alertas
- Desglose por proveedor
- Gráficos de distribución

#### ⚙️ **Ejecutar**
- **Ejecutar Queries**: Lanza queries de una categoría desde la interfaz
- **Generar Informe**: Crea informes PDF completos
- Todo con un solo clic

### Screenshots Conceptuales

**Dashboard:**
- 4 métricas principales en cards
- Tabla de últimas ejecuciones
- Lista de informes generados

**Ejecutar Queries:**
- Seleccionar mercado y categoría con dropdowns
- Botón "Ejecutar" con spinner
- Resultados con métricas en tiempo real

**Generar Informe:**
- Selección de categoría y periodo
- Botón para generar
- Progress bar durante generación
- Link al PDF generado

## 📈 Próximos Pasos

### Opción A: Usar la Interfaz Web (Recomendado)

1. **Iniciar la interfaz**:
   ```bash
   streamlit run app.py
   ```

2. **Navegar a "⚙️ Ejecutar" → "Ejecutar Queries"**
   - Seleccionar FMCG/Cervezas
   - Hacer clic en "Ejecutar Queries"

3. **Navegar a "⚙️ Ejecutar" → "Generar Informe"**
   - Seleccionar FMCG/Cervezas
   - Periodo: 2025-10
   - Hacer clic en "Generar Informe"

4. **Ver resultados en "📄 Informes"**

### Opción B: Usar la CLI

1. **Ejecutar primera ronda de queries**:
   ```bash
   python main.py execute-queries -c "FMCG/Cervezas"
   ```

2. **Generar primer informe**:
   ```bash
   python main.py generate-report -c "FMCG/Cervezas" -p "2025-10"
   ```

3. **Configurar polling automático** (cron, systemd, etc.)

4. **Revisar y ajustar queries** según resultados

5. **Añadir más categorías** según necesidad

## 🤝 Soporte

Para soporte o consultas, contacta al equipo de TwoLaps.

## 📄 Licencia

Propietario - TwoLaps Intelligence Platform

---

**Versión**: 1.0.0  
**Fecha**: Octubre 2025

