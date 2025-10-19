"""
Chart Generator
Genera gráficos y visualizaciones para reportes PDF
"""

import base64
from io import BytesIO
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Configuración de estilo
plt.style.use('seaborn-v0_8-darkgrid')
BRAND_COLOR = '#0066cc'
SUCCESS_COLOR = '#28a745'
WARNING_COLOR = '#ffc107'
DANGER_COLOR = '#dc3545'
NEUTRAL_COLOR = '#6c757d'


class ChartGenerator:
    """Genera gráficos en formato base64 para embeber en HTML"""
    
    def __init__(self):
        self.dpi = 100
        self.fig_width = 10
        self.fig_height = 6
    
    def generate_sov_chart(self, sov_data: Dict[str, float]) -> str:
        """
        Genera gráfico de barras para Share of Voice
        
        Args:
            sov_data: Dict con marcas y porcentajes. Ej: {"Heineken": 25.5, "Corona": 20.3}
        
        Returns:
            String base64 del gráfico
        """
        if not sov_data:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        # Ordenar por valor descendente
        sorted_data = dict(sorted(sov_data.items(), key=lambda x: x[1], reverse=True))
        marcas = list(sorted_data.keys())
        valores = list(sorted_data.values())
        
        # Colores: líder en azul, resto en degradado
        colors = []
        for i in range(len(marcas)):
            if i == 0:
                colors.append(BRAND_COLOR)
            else:
                # Generar colores en degradado azul
                r = min(102 + i * 20, 200)
                g = min(102 + i * 20, 200)
                b = 204
                colors.append(f'#{r:02x}{g:02x}{b:02x}')
        
        # Crear barras horizontales
        bars = ax.barh(marcas, valores, color=colors, edgecolor='white', linewidth=1.5)
        
        # Añadir valores en las barras
        for i, (bar, valor) in enumerate(zip(bars, valores)):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                   f'{valor:.1f}%', 
                   ha='left', va='center', fontweight='bold', fontsize=10)
        
        # Estilo
        ax.set_xlabel('Share of Voice (%)', fontsize=12, fontweight='bold')
        ax.set_title('Distribución del Share of Voice', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(0, max(valores) * 1.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_sentiment_chart(self, sentiment_data: Dict[str, Dict[str, float]]) -> str:
        """
        Genera gráfico de barras apiladas para sentimiento por marca
        
        Args:
            sentiment_data: Dict con marcas y sentimientos. 
                Ej: {"Heineken": {"positivo": 60, "neutral": 30, "negativo": 10}}
        
        Returns:
            String base64 del gráfico
        """
        if not sentiment_data:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        marcas = list(sentiment_data.keys())
        positivo = [sentiment_data[m].get('positivo', 0) for m in marcas]
        neutral = [sentiment_data[m].get('neutral', 0) for m in marcas]
        negativo = [sentiment_data[m].get('negativo', 0) for m in marcas]
        
        # Barras apiladas
        x = np.arange(len(marcas))
        width = 0.6
        
        p1 = ax.bar(x, positivo, width, label='Positivo', color=SUCCESS_COLOR)
        p2 = ax.bar(x, neutral, width, bottom=positivo, label='Neutral', color=NEUTRAL_COLOR)
        p3 = ax.bar(x, negativo, width, bottom=np.array(positivo) + np.array(neutral), 
                    label='Negativo', color=DANGER_COLOR)
        
        # Añadir porcentajes
        for i, (pos, neu, neg) in enumerate(zip(positivo, neutral, negativo)):
            if pos > 5:
                ax.text(i, pos/2, f'{pos:.0f}%', ha='center', va='center', 
                       fontweight='bold', color='white', fontsize=9)
            if neu > 5:
                ax.text(i, pos + neu/2, f'{neu:.0f}%', ha='center', va='center', 
                       fontweight='bold', color='white', fontsize=9)
            if neg > 5:
                ax.text(i, pos + neu + neg/2, f'{neg:.0f}%', ha='center', va='center', 
                       fontweight='bold', color='white', fontsize=9)
        
        # Estilo
        ax.set_ylabel('Porcentaje (%)', fontsize=12, fontweight='bold')
        ax.set_title('Análisis de Sentimiento por Marca', fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(marcas, rotation=45, ha='right')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.set_ylim(0, 105)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_opportunity_matrix(self, opportunities: List[Dict[str, Any]]) -> str:
        """
        Genera matriz 2x2 de oportunidades (Impacto vs Esfuerzo)
        
        Args:
            opportunities: Lista de oportunidades con campos:
                - titulo: str
                - impacto: str (alto/medio/bajo)
                - esfuerzo: str (alto/medio/bajo)
        
        Returns:
            String base64 del gráfico
        """
        if not opportunities:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        # Mapeo de valores
        impact_map = {'alto': 3, 'media': 2, 'medio': 2, 'bajo': 1, 'baja': 1}
        effort_map = {'alto': 3, 'media': 2, 'medio': 2, 'bajo': 1, 'baja': 1}
        
        # Procesar oportunidades
        for i, opp in enumerate(opportunities[:10]):  # Máximo 10 para no saturar
            titulo = opp.get('titulo', f'Oportunidad {i+1}')[:30]
            impacto = impact_map.get(str(opp.get('impacto', 'medio')).lower(), 2)
            esfuerzo = effort_map.get(str(opp.get('esfuerzo', 'medio')).lower(), 2)
            
            # Añadir ruido para evitar superposición
            impacto += np.random.uniform(-0.15, 0.15)
            esfuerzo += np.random.uniform(-0.15, 0.15)
            
            # Color según cuadrante
            if impacto >= 2.5 and esfuerzo <= 1.5:
                color = SUCCESS_COLOR  # Quick wins
                marker = 'o'
                size = 300
            elif impacto >= 2.5:
                color = BRAND_COLOR  # Major projects
                marker = 's'
                size = 250
            elif esfuerzo <= 1.5:
                color = WARNING_COLOR  # Fill-ins
                marker = '^'
                size = 200
            else:
                color = NEUTRAL_COLOR  # Thankless tasks
                marker = 'D'
                size = 150
            
            ax.scatter(esfuerzo, impacto, s=size, c=color, alpha=0.6, 
                      edgecolors='white', linewidth=2, marker=marker)
            ax.annotate(titulo, (esfuerzo, impacto), fontsize=8, 
                       ha='center', va='bottom', fontweight='bold')
        
        # Líneas divisoras
        ax.axhline(y=2, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(x=2, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        # Cuadrantes
        ax.text(1, 2.7, 'QUICK WINS', fontsize=11, ha='center', 
               fontweight='bold', color=SUCCESS_COLOR, alpha=0.7)
        ax.text(2.7, 2.7, 'MAJOR PROJECTS', fontsize=11, ha='center', 
               fontweight='bold', color=BRAND_COLOR, alpha=0.7)
        ax.text(1, 1.3, 'FILL-INS', fontsize=11, ha='center', 
               fontweight='bold', color=WARNING_COLOR, alpha=0.7)
        ax.text(2.7, 1.3, 'THANKLESS TASKS', fontsize=11, ha='center', 
               fontweight='bold', color=NEUTRAL_COLOR, alpha=0.7)
        
        # Estilo
        ax.set_xlabel('Esfuerzo →', fontsize=12, fontweight='bold')
        ax.set_ylabel('Impacto →', fontsize=12, fontweight='bold')
        ax.set_title('Matriz de Priorización de Oportunidades', fontsize=14, 
                    fontweight='bold', pad=20)
        ax.set_xlim(0.5, 3.5)
        ax.set_ylim(0.5, 3.5)
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(['Bajo', 'Medio', 'Alto'])
        ax.set_yticks([1, 2, 3])
        ax.set_yticklabels(['Bajo', 'Medio', 'Alto'])
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_risk_matrix(self, risks: List[Dict[str, Any]]) -> str:
        """
        Genera matriz 2x2 de riesgos (Probabilidad vs Severidad)
        
        Args:
            risks: Lista de riesgos con campos:
                - titulo: str
                - probabilidad: str (alta/media/baja)
                - severidad: str (alta/media/baja)
        
        Returns:
            String base64 del gráfico
        """
        if not risks:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        # Mapeo de valores
        prob_map = {'alta': 3, 'media': 2, 'baja': 1}
        sev_map = {'alta': 3, 'media': 2, 'baja': 1}
        
        # Procesar riesgos
        for i, risk in enumerate(risks[:10]):
            titulo = risk.get('titulo', f'Riesgo {i+1}')[:30]
            probabilidad = prob_map.get(str(risk.get('probabilidad', 'media')).lower(), 2)
            severidad = sev_map.get(str(risk.get('severidad', 'media')).lower(), 2)
            
            # Añadir ruido
            probabilidad += np.random.uniform(-0.15, 0.15)
            severidad += np.random.uniform(-0.15, 0.15)
            
            # Color según nivel de riesgo
            risk_level = probabilidad * severidad
            if risk_level >= 6:
                color = DANGER_COLOR
                size = 300
            elif risk_level >= 4:
                color = WARNING_COLOR
                size = 250
            else:
                color = NEUTRAL_COLOR
                size = 200
            
            ax.scatter(probabilidad, severidad, s=size, c=color, alpha=0.6, 
                      edgecolors='white', linewidth=2)
            ax.annotate(titulo, (probabilidad, severidad), fontsize=8, 
                       ha='center', va='bottom', fontweight='bold')
        
        # Líneas divisoras
        ax.axhline(y=2, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(x=2, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        # Zonas de riesgo
        ax.text(2.7, 2.7, 'CRÍTICO', fontsize=12, ha='center', 
               fontweight='bold', color=DANGER_COLOR, alpha=0.7)
        ax.text(1, 2.7, 'ALTO', fontsize=12, ha='center', 
               fontweight='bold', color=WARNING_COLOR, alpha=0.7)
        ax.text(2.7, 1, 'MODERADO', fontsize=12, ha='center', 
               fontweight='bold', color=WARNING_COLOR, alpha=0.7)
        ax.text(1, 1, 'BAJO', fontsize=12, ha='center', 
               fontweight='bold', color=NEUTRAL_COLOR, alpha=0.7)
        
        # Estilo
        ax.set_xlabel('Probabilidad →', fontsize=12, fontweight='bold')
        ax.set_ylabel('Severidad →', fontsize=12, fontweight='bold')
        ax.set_title('Matriz de Evaluación de Riesgos', fontsize=14, 
                    fontweight='bold', pad=20)
        ax.set_xlim(0.5, 3.5)
        ax.set_ylim(0.5, 3.5)
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(['Baja', 'Media', 'Alta'])
        ax.set_yticks([1, 2, 3])
        ax.set_yticklabels(['Baja', 'Media', 'Alta'])
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_timeline_chart(self, initiatives: List[Dict[str, Any]]) -> str:
        """
        Genera timeline visual para el plan de 90 días
        
        Args:
            initiatives: Lista de iniciativas con campos:
                - titulo: str
                - timeline: str (ej: "0-30 días", "Q1", etc.)
                - prioridad: str (alta/media/baja)
        
        Returns:
            String base64 del gráfico
        """
        if not initiatives:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, 6))
        
        # Procesar iniciativas
        timeline_map = {
            '0-30': (0, 30), 'mes 1': (0, 30), 'q1': (0, 30),
            '30-60': (30, 60), 'mes 2': (30, 60), 'q2': (30, 60),
            '60-90': (60, 90), 'mes 3': (60, 90), 'q3': (60, 90)
        }
        
        priority_colors = {
            'alta': DANGER_COLOR,
            'media': WARNING_COLOR,
            'baja': NEUTRAL_COLOR
        }
        
        y_pos = 0
        for i, init in enumerate(initiatives[:8]):  # Máximo 8
            titulo = init.get('titulo', f'Iniciativa {i+1}')
            timeline_str = str(init.get('timeline', '0-30 días')).lower()
            prioridad = str(init.get('prioridad', 'media')).lower()
            
            # Detectar periodo
            start, end = (0, 30)  # Default
            for key, (s, e) in timeline_map.items():
                if key in timeline_str:
                    start, end = s, e
                    break
            
            # Color según prioridad
            color = priority_colors.get(prioridad, NEUTRAL_COLOR)
            
            # Dibujar barra
            ax.barh(y_pos, end - start, left=start, height=0.8, 
                   color=color, alpha=0.7, edgecolor='white', linewidth=2)
            
            # Etiqueta
            ax.text(start + (end - start) / 2, y_pos, titulo[:40], 
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')
            
            y_pos += 1
        
        # Estilo
        ax.set_xlabel('Días', fontsize=12, fontweight='bold')
        ax.set_title('Timeline del Plan de Acción 90 Días', fontsize=14, 
                    fontweight='bold', pad=20)
        ax.set_xlim(0, 90)
        ax.set_ylim(-0.5, y_pos - 0.5)
        ax.set_yticks([])
        ax.set_xticks([0, 30, 60, 90])
        ax.set_xticklabels(['Inicio', 'Día 30', 'Día 60', 'Día 90'])
        
        # Líneas divisoras de meses
        ax.axvline(x=30, color='gray', linestyle='--', linewidth=1, alpha=0.3)
        ax.axvline(x=60, color='gray', linestyle='--', linewidth=1, alpha=0.3)
        
        ax.spines['left'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Leyenda
        handles = [mpatches.Patch(color=DANGER_COLOR, label='Prioridad Alta', alpha=0.7),
                  mpatches.Patch(color=WARNING_COLOR, label='Prioridad Media', alpha=0.7),
                  mpatches.Patch(color=NEUTRAL_COLOR, label='Prioridad Baja', alpha=0.7)]
        ax.legend(handles=handles, loc='upper right')
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convierte figura matplotlib a string base64"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f'data:image/png;base64,{image_base64}'


# Helper function
def generate_all_charts(report_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Genera todos los gráficos para un reporte
    
    Args:
        report_data: Datos del reporte con estructura completa
    
    Returns:
        Dict con gráficos en base64
    """
    generator = ChartGenerator()
    charts = {}
    
    # SOV Chart
    competencia = report_data.get('competencia', {})
    if competencia.get('sov_data'):
        charts['sov_chart'] = generator.generate_sov_chart(competencia['sov_data'])
    
    # Sentiment Chart
    sentimiento = report_data.get('sentimiento_reputacion', {})
    if sentimiento.get('sentiment_data'):
        charts['sentiment_chart'] = generator.generate_sentiment_chart(sentimiento['sentiment_data'])
    
    # Opportunity Matrix
    opp_riesgos = report_data.get('oportunidades_riesgos', {})
    if opp_riesgos.get('oportunidades'):
        charts['opportunity_matrix'] = generator.generate_opportunity_matrix(opp_riesgos['oportunidades'])
    
    # Risk Matrix
    if opp_riesgos.get('riesgos'):
        charts['risk_matrix'] = generator.generate_risk_matrix(opp_riesgos['riesgos'])
    
    # Timeline
    plan = report_data.get('plan_90_dias', {})
    if plan.get('iniciativas'):
        charts['timeline_chart'] = generator.generate_timeline_chart(plan['iniciativas'])
    
    return charts

