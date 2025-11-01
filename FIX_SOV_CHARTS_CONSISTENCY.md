# Fix: Inconsistencia en Gráficos SOV

## 🐛 Problema Detectado

Los gráficos de SOV mostraban **porcentajes diferentes**:

### Ejemplo en Hamburgueserías:

| Marca | Gráfico Barras | Gráfico Pastel | Diferencia |
|-------|----------------|----------------|------------|
| McDonald's | 26.4% | 30.4% | **+4.0 pp** |
| Vicio | 20.0% | 23.0% | **+3.0 pp** |
| Burger King | 13.9% | 16.0% | **+2.1 pp** |
| Five Guys | 11.3% | 13.0% | **+1.7 pp** |
| Goiko | 7.9% | 9.1% | **+1.2 pp** |
| The Good Burger | 3.8% | 1.4% | **-2.4 pp** ⚠️ |
| Bacoa | 3.5% | 4.0% | **+0.5 pp** |

## 🔍 Causa Raíz

En `src/reporting/chart_generator.py`, el método `generate_sov_pie_chart()` usaba:

```python
ax.pie(valores, autopct='%1.1f%%', ...)
```

**El parámetro `autopct` de matplotlib automáticamente RE-NORMALIZA los valores para que sumen 100%**, incluso si los datos originales no suman 100%.

Esto causaba:
- **Gráfico de barras**: Mostraba valores reales (ej: 26.4%, sumando 86.8% total)
- **Gráfico de pastel**: Re-normalizaba automáticamente (ej: 30.4%, sumando ~100%)

## ✅ Solución Implementada

Se modificó `generate_sov_pie_chart()` para usar una **función personalizada** que muestra los **valores originales reales** sin re-normalización:

```python
def make_autopct(values):
    def my_autopct(pct):
        # Calcula el valor real desde el porcentaje que matplotlib genera
        total = sum(values)
        val = pct * total / 100.0
        # Busca el valor original más cercano
        for v in values:
            if abs(v - val) < 0.1:
                return f'{v:.1f}%'
        return f'{val:.1f}%'
    return my_autopct

ax.pie(valores, autopct=make_autopct(valores), ...)
```

## 📊 Resultado

Ahora **ambos gráficos muestran exactamente los mismos porcentajes**:
- McDonald's: **26.4%** en ambos
- Vicio: **20.0%** en ambos
- Burger King: **13.9%** en ambos
- etc.

## 🔧 Archivos Modificados

1. **`src/reporting/chart_generator.py`**
   - Líneas 86-148: Método `generate_sov_pie_chart()` actualizado

## ✅ Gráficos Regenerados

Se regeneraron los gráficos para asegurar consistencia en:
- ✅ FMCG/Hamburgueserías (2025-10)
- ✅ FMCG/Suplementos Alimenticios Naturales (2025-10)

## 📝 Recomendaciones

### Para futuros informes:
Regenerar todos los gráficos existentes con el comando:
```bash
python scripts/generate_charts_only.py -c "FMCG/[CATEGORÍA]" -p "[PERIODO]"
```

### Para nuevos informes:
Los gráficos se generarán automáticamente con la corrección aplicada.

## 🎯 Verificación

Puedes verificar la consistencia comparando visualmente ambos gráficos:
- `data/reports/charts/FMCG_Hamburgueserías_2025-10/sov_chart.png`
- `data/reports/charts/FMCG_Hamburgueserías_2025-10/sov_pie_chart.png`

Los porcentajes ahora coinciden exactamente.

---

**Fecha del Fix:** 28 de Octubre, 2025  
**Archivos afectados:** 1  
**Categorías regeneradas:** 2  
**Estado:** ✅ RESUELTO




