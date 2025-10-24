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
        # Máximo de marcas a visualizar en gráficos
        self.max_brands = 7
    
    def generate_sov_chart(self, sov_data: Dict[str, float]) -> Optional[str]:
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
    
    def generate_sov_pie_chart(self, sov_data: Dict[str, float]) -> Optional[str]:
        """
        Genera gráfico de pastel (pie chart) para Share of Voice
        
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
        
        # Colores vibrantes
        colors = ['#0066cc', '#28a745', '#ffc107', '#dc3545', '#6c757d', 
                 '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
        
        # Crear pie chart
        _, _, autotexts = ax.pie(
            valores, 
            labels=marcas, 
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(marcas)],
            explode=[0.05 if i == 0 else 0 for i in range(len(marcas))],  # Explotar el líder
            shadow=True,
            textprops={'fontweight': 'bold', 'fontsize': 10}
        )
        
        # Mejorar estilo de textos
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        # Título
        ax.set_title('Distribución del Share of Voice', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_sentiment_chart(self, sentiment_data: Dict[str, Dict[str, float]]) -> Optional[str]:
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
        
        ax.bar(x, positivo, width, label='Positivo', color=SUCCESS_COLOR)
        ax.bar(x, neutral, width, bottom=positivo, label='Neutral', color=NEUTRAL_COLOR)
        ax.bar(x, negativo, width, bottom=np.array(positivo) + np.array(neutral), 
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
    
    def generate_opportunity_matrix(self, opportunities: List[Dict[str, Any]]) -> Optional[str]:
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
            rng = np.random.default_rng(42)
            impacto += rng.uniform(-0.15, 0.15)
            esfuerzo += rng.uniform(-0.15, 0.15)
            
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
    
    def generate_risk_matrix(self, risks: List[Dict[str, Any]]) -> Optional[str]:
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
            rng = np.random.default_rng(42)
            probabilidad += rng.uniform(-0.15, 0.15)
            severidad += rng.uniform(-0.15, 0.15)
            
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
    
    def generate_sov_trend_chart(self, sov_trend_data: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """
        Genera gráfico de líneas con tendencias de SOV por marca a lo largo del tiempo
        FUNCIONA INCLUSO CON UN SOLO PUNTO DE DATOS (muestra como barra en ese caso)
        
        Args:
            sov_trend_data: Dict con marcas y sus datos temporales
                Ej: {"Heineken": [{"periodo": "2025-09", "sov": 25.5}, {"periodo": "2025-10", "sov": 27.3}]}
        
        Returns:
            String base64 del gráfico
        """
        if not sov_trend_data:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        # Colores para diferentes marcas
        colors = [BRAND_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, NEUTRAL_COLOR, 
                 '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
        
        # Verificar si todos tienen un solo punto
        all_single_point = all(len(datos) == 1 for datos in sov_trend_data.values() if datos)
        
        for idx, (marca, datos) in enumerate(sov_trend_data.items()):
            if not datos:
                continue
            
            periodos = [d['periodo'] for d in datos]
            valores = [d['sov'] for d in datos]
            
            color = colors[idx % len(colors)]
            
            if len(datos) == 1 and all_single_point:
                # Si solo hay 1 punto y todos tienen 1 punto, mostrar como barra
                ax.bar(idx, valores[0], color=color, alpha=0.8, label=marca, edgecolor='white', linewidth=2)
                ax.text(idx, valores[0] + 1, f'{valores[0]:.1f}%', 
                       ha='center', va='bottom', fontweight='bold', fontsize=10)
            else:
                # Múltiples puntos o modo mixto: usar línea
                ax.plot(range(len(periodos)), valores, marker='o', linewidth=2.5, 
                       markersize=10, label=marca, color=color, alpha=0.8)
                
                # Añadir valor en el último punto
                if valores:
                    ax.text(len(periodos)-1, valores[-1], f'{valores[-1]:.1f}%', 
                           fontsize=9, fontweight='bold', 
                           ha='left', va='bottom', color=color)
        
        # Estilo
        ax.set_ylabel('Share of Voice (%)', fontsize=12, fontweight='bold')
        
        if all_single_point:
            ax.set_title('Share of Voice por Marca (Snapshot)', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Marcas', fontsize=12, fontweight='bold')
            ax.set_xticks(range(len(sov_trend_data)))
            ax.set_xticklabels(list(sov_trend_data.keys()), rotation=45, ha='right')
        else:
            ax.set_title('Evolución del Share of Voice por Marca', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Período', fontsize=12, fontweight='bold')
            # Usar periodos como etiquetas
            all_periodos = []
            for datos in sov_trend_data.values():
                if datos:
                    all_periodos.extend([d['periodo'] for d in datos])
            unique_periodos = sorted(set(all_periodos))
            if len(unique_periodos) > 1:
                ax.set_xticks(range(len(unique_periodos)))
                ax.set_xticklabels(unique_periodos, rotation=45, ha='right')
        
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_sentiment_trend_chart(self, sentiment_trend_data: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """
        Genera gráfico de líneas con evolución del sentimiento por marca
        FUNCIONA INCLUSO CON UN SOLO PUNTO DE DATOS (muestra como barra en ese caso)
        
        Args:
            sentiment_trend_data: Dict con marcas y scores temporales
                Ej: {"Heineken": [{"periodo": "2025-09", "score": 0.65}, {"periodo": "2025-10", "score": 0.72}]}
        
        Returns:
            String base64 del gráfico
        """
        if not sentiment_trend_data:
            return None
        
        fig, ax = plt.subplots(figsize=(self.fig_width, self.fig_height))
        
        # Colores para diferentes marcas
        colors = [BRAND_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, NEUTRAL_COLOR, 
                 '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
        
        # Verificar si todos tienen un solo punto
        all_single_point = all(len(datos) == 1 for datos in sentiment_trend_data.values() if datos)
        
        # Zonas de sentimiento (fondo)
        ax.axhspan(-1, 0, alpha=0.05, color='red')
        ax.axhspan(0, 1, alpha=0.05, color='green')
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        for idx, (marca, datos) in enumerate(sentiment_trend_data.items()):
            if not datos:
                continue
            
            periodos = [d['periodo'] for d in datos]
            scores = [d['score'] for d in datos]
            
            color = colors[idx % len(colors)]
            
            if len(datos) == 1 and all_single_point:
                # Si solo hay 1 punto y todos tienen 1 punto, mostrar como barra
                ax.bar(idx, scores[0], color=color, alpha=0.8, label=marca, edgecolor='white', linewidth=2, bottom=0)
                ax.text(idx, scores[0] + 0.05, f'{scores[0]:.2f}', 
                       ha='center', va='bottom', fontweight='bold', fontsize=10)
            else:
                # Múltiples puntos: usar línea
                ax.plot(range(len(periodos)), scores, marker='o', linewidth=2.5, 
                       markersize=10, label=marca, color=color, alpha=0.8)
                
                # Añadir valor en el último punto
                if scores:
                    ax.text(len(periodos)-1, scores[-1], f'{scores[-1]:.2f}', 
                           fontsize=9, fontweight='bold', 
                           ha='left', va='bottom', color=color)
        
        # Estilo
        ax.set_ylabel('Score de Sentimiento (-1 a 1)', fontsize=12, fontweight='bold')
        ax.set_ylim(-1, 1)
        
        if all_single_point:
            ax.set_title('Sentimiento por Marca (Snapshot)', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Marcas', fontsize=12, fontweight='bold')
            ax.set_xticks(range(len(sentiment_trend_data)))
            ax.set_xticklabels(list(sentiment_trend_data.keys()), rotation=45, ha='right')
        else:
            ax.set_title('Evolución del Sentimiento por Marca', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Período', fontsize=12, fontweight='bold')
            # Usar periodos como etiquetas
            all_periodos = []
            for datos in sentiment_trend_data.values():
                if datos:
                    all_periodos.extend([d['periodo'] for d in datos])
            unique_periodos = sorted(set(all_periodos))
            if len(unique_periodos) > 1:
                ax.set_xticks(range(len(unique_periodos)))
                ax.set_xticklabels(unique_periodos, rotation=45, ha='right')
        
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_attribute_radar_chart(self, attributes_by_brand: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Genera gráfico radar (telaraña) comparando atributos percibidos por marca
        
        Args:
            attributes_by_brand: Dict con marcas y sus atributos
                Ej: {"Heineken": {"calidad": 4.5, "precio": 3.2, "innovacion": 4.0, ...}, ...}
        
        Returns:
            String base64 del gráfico
        """
        if not attributes_by_brand or len(attributes_by_brand) == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
        
        # Atributos clave a visualizar (máximo 8 para legibilidad)
        key_attributes = ['calidad', 'precio', 'innovacion', 'confiabilidad', 
                         'servicio', 'reputacion', 'experiencia', 'disponibilidad']
        
        # Filtrar marcas (máximo self.max_brands para no saturar)
        brands_to_plot = list(attributes_by_brand.keys())[: self.max_brands]
        
        # Colores para diferentes marcas
        colors = [BRAND_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, NEUTRAL_COLOR]
        
        # Número de atributos
        num_attributes = len(key_attributes)
        angles = np.linspace(0, 2 * np.pi, num_attributes, endpoint=False).tolist()
        angles += angles[:1]  # Cerrar el polígono
        
        for idx, brand in enumerate(brands_to_plot):
            brand_data = attributes_by_brand[brand]
            
            # Extraer valores (normalizar a escala 0-5 si es necesario)
            values = []
            for attr in key_attributes:
                attr_data = brand_data.get(attr, [])
                if isinstance(attr_data, (int, float)):
                    values.append(attr_data)
                elif isinstance(attr_data, list) and len(attr_data) > 0:
                    # Si es lista, contar menciones como proxy de fuerza
                    values.append(min(len(attr_data), 5))
                else:
                    values.append(0)
            
            values += values[:1]  # Cerrar el polígono
            
            color = colors[idx % len(colors)]
            ax.plot(angles, values, 'o-', linewidth=2, label=brand, color=color, alpha=0.8)
            ax.fill(angles, values, alpha=0.15, color=color)
        
        # Configurar ejes
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([attr.capitalize() for attr in key_attributes], fontsize=10)
        ax.set_ylim(0, 5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=8, alpha=0.5)
        ax.grid(True, alpha=0.3)
        
        # Título y leyenda
        ax.set_title('Radar de Atributos Percibidos por Marca', fontsize=14, 
                    fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def generate_channel_penetration_chart(self, channel_data: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Genera gráfico de barras agrupadas de penetración por canal y marca
        
        Args:
            channel_data: Dict con marcas y presencia por canal
                Ej: {"Heineken": {"supermercados": 5, "ecommerce": 3, "conveniencia": 4}, ...}
        
        Returns:
            String base64 del gráfico
        """
        if not channel_data or len(channel_data) == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Canales clave
        key_channels = ['supermercados', 'ecommerce', 'conveniencia', 'especializado', 
                       'd2c', 'delivery', 'otros']
        
        # Filtrar marcas (máximo self.max_brands para legibilidad)
        brands = list(channel_data.keys())[: self.max_brands]
        
        # Preparar datos
        channel_scores = {channel: [] for channel in key_channels}
        for brand in brands:
            brand_channels = channel_data[brand]
            for channel in key_channels:
                # Obtener score de presencia (0-5)
                if channel in brand_channels:
                    val = brand_channels[channel]
                    if isinstance(val, (int, float)):
                        channel_scores[channel].append(val)
                    elif isinstance(val, list):
                        channel_scores[channel].append(min(len(val), 5))
                    elif isinstance(val, dict):
                        # Si es dict con "presencia", "menciones", etc.
                        channel_scores[channel].append(val.get('score', val.get('presencia', 0)))
                    else:
                        channel_scores[channel].append(0)
                else:
                    channel_scores[channel].append(0)
        
        # Filtrar canales con al menos 1 mención
        active_channels = [ch for ch in key_channels if sum(channel_scores[ch]) > 0]
        
        if not active_channels:
            return None
        
        # Crear barras agrupadas
        x = np.arange(len(active_channels))
        width = 0.8 / len(brands)
        
        colors = [BRAND_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, 
                 NEUTRAL_COLOR, '#ff6b6b', '#4ecdc4']
        
        for i, brand in enumerate(brands):
            values = [channel_scores[ch][i] for ch in active_channels]
            offset = (i - len(brands) / 2) * width + width / 2
            bars = ax.bar(x + offset, values, width, label=brand, 
                         color=colors[i % len(colors)], alpha=0.8, edgecolor='white')
            
            # Añadir valores si son significativos
            for j, (bar, val) in enumerate(zip(bars, values)):
                if val > 0.5:
                    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.1, 
                           f'{val:.1f}', ha='center', va='bottom', 
                           fontsize=8, fontweight='bold')
        
        # Configurar ejes
        ax.set_xlabel('Canales de Distribución', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score de Penetración (0-5)', fontsize=12, fontweight='bold')
        ax.set_title('Penetración por Canal de Distribución', fontsize=14, 
                    fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([ch.replace('_', ' ').capitalize() for ch in active_channels], 
                          rotation=45, ha='right')
        ax.set_ylim(0, max(5, max([max(channel_scores[ch]) for ch in active_channels]) * 1.2))
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, alpha=0.3, axis='y')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)

    def generate_perceptual_map(self, brands: List[Dict[str, Any]]) -> Optional[str]:
        """
        Genera mapa perceptual 2D: Eje X (Precio), Eje Y (Calidad percibida)
        Cada marca como burbuja con tamaño = SOV (%), color por cuadrante.

        Args:
            brands: Lista de dicts con claves: marca, precio (0-100), calidad (0-100), sov (0-100)

        Returns:
            String base64 del gráfico
        """
        if not brands:
            return None

        fig, ax = plt.subplots(figsize=(12, 8))

        nombres = [b.get('marca', '') for b in brands]
        precios = [float(b.get('precio', 0)) for b in brands]
        calidades = [float(b.get('calidad', 0)) for b in brands]
        sovs = [max(float(b.get('sov', 0)), 0.1) for b in brands]

        # Tamaño proporcional al SOV (escala 50-1200)
        sizes = [50 + (sov / max(max(sovs), 1)) * 1150 for sov in sovs]

        # Líneas medianas para cuadrantes
        x_med = np.median(precios) if precios else 50
        y_med = np.median(calidades) if calidades else 50

        colors = []
        for x, y in zip(precios, calidades):
            if x >= x_med and y >= y_med:
                colors.append(SUCCESS_COLOR)  # Premium percibido alto, precio alto
            elif x < x_med and y >= y_med:
                colors.append(BRAND_COLOR)    # Valor superior (calidad alta, precio bajo)
            elif x >= x_med and y < y_med:
                colors.append(DANGER_COLOR)   # Riesgo (precio alto, calidad baja)
            else:
                colors.append(NEUTRAL_COLOR)  # Económico (precio bajo, calidad baja)

        ax.scatter(precios, calidades, s=sizes, c=colors, alpha=0.6, edgecolors='white', linewidth=2)

        for i, name in enumerate(nombres):
            ax.annotate(name, (precios[i], calidades[i]), fontsize=10, fontweight='bold', ha='center', va='bottom')

        # Cuadrantes
        ax.axvline(x=x_med, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline(y=y_med, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax.text(x_med + (100 - x_med) * 0.5, y_med + (100 - y_med) * 0.7, 'PREMIUM',
                fontsize=11, ha='center', fontweight='bold', color=SUCCESS_COLOR, alpha=0.7)
        ax.text(x_med * 0.5, y_med + (100 - y_med) * 0.7, 'VALOR',
                fontsize=11, ha='center', fontweight='bold', color=BRAND_COLOR, alpha=0.7)
        ax.text(x_med + (100 - x_med) * 0.5, y_med * 0.5, 'RIESGO',
                fontsize=11, ha='center', fontweight='bold', color=DANGER_COLOR, alpha=0.7)
        ax.text(x_med * 0.5, y_med * 0.5, 'ECONÓMICO',
                fontsize=11, ha='center', fontweight='bold', color=NEUTRAL_COLOR, alpha=0.7)

        ax.set_xlabel('Precio percibido (0-100)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Calidad percibida (0-100)', fontsize=12, fontweight='bold')
        ax.set_title('Mapa Perceptual: Precio vs Calidad (Tamaño = SOV)', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Leyenda de tamaños
        legend_sizes = [min(max(sovs), 5), max(np.median(sovs), 10), max(sovs)]
        legend_sizes = [max(ls, 1) for ls in legend_sizes]
        legend_markers = [plt.scatter([], [], s=50 + (ls / max(max(sovs), 1)) * 1150, c='gray', alpha=0.5, edgecolors='white', linewidth=2)
                          for ls in legend_sizes]
        legend_labels = [f'SOV {ls:.0f}%' for ls in legend_sizes]
        ax.legend(legend_markers, legend_labels, title='Tamaño burbuja', loc='upper left', framealpha=0.9, fontsize=9)

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def generate_waterfall_chart(self, steps: List[Dict[str, Any]]) -> Optional[str]:
        """
        Genera un Waterfall Chart para explicar cambios en SOV entre periodos.

        Args:
            steps: lista de pasos [{label: str, value: float, type: 'start'|'delta'|'end'}]
                   Ej: [{"label": "Q3", "value": 35, "type": "start"},
                        {"label": "Campaña +TV", "value": +3, "type": "delta"},
                        {"label": "Pérdida retail", "value": -1, "type": "delta"},
                        {"label": "Q4", "value": 37, "type": "end"}]

        Returns:
            String base64 del gráfico
        """
        if not steps or not isinstance(steps, list):
            return None

        fig, ax = plt.subplots(figsize=(12, 6))

        labels = [s.get('label', '') for s in steps]
        types = [s.get('type', 'delta') for s in steps]
        values = [float(s.get('value', 0)) for s in steps]

        # Calcular posiciones y alturas
        running = []
        total = 0.0
        start_val = None
        for t, v in zip(types, values):
            if t == 'start':
                start_val = v
                total = v
                running.append(total)
            elif t == 'delta':
                total += v
                running.append(total)
            else:
                # end: aseguramos coherencia si no coincide
                if start_val is not None and abs(total - v) > 0.01:
                    total = v
                running.append(total)

        bars = []
        cumulative = start_val if start_val is not None else 0.0
        for idx, (t, v) in enumerate(zip(types, values)):
            if t == 'start':
                bars.append((cumulative, v - 0))
                cumulative = v
            elif t == 'delta':
                bars.append((min(cumulative, cumulative + v), abs(v)))
                cumulative += v
            else:  # end
                bars.append((0, cumulative))

        colors = []
        for t, v in zip(types, values):
            if t == 'start' or t == 'end':
                colors.append(NEUTRAL_COLOR)
            else:
                colors.append(SUCCESS_COLOR if v >= 0 else DANGER_COLOR)

        x = np.arange(len(steps))
        for i, ((y0, height), color) in enumerate(zip(bars, colors)):
            ax.bar(x[i], height, bottom=y0, width=0.6, color=color, edgecolor='white', linewidth=1.5)
            # etiqueta de valor
            val = values[i] if types[i] == 'delta' else bars[i][0] + bars[i][1]
            ax.text(x[i], y0 + height + 0.8, f"{val:+.1f}%" if types[i] == 'delta' else f"{val:.1f}%",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.set_ylabel('Share of Voice (%)', fontsize=12, fontweight='bold')
        ax.set_title('Waterfall de cambios en SOV', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, axis='y', alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def generate_bcg_matrix(self, brands_metrics: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Genera BCG Matrix: Market Share (X) vs Growth Rate (Y)

        Args:
            brands_metrics: { marca: {market_share: float, growth_rate: float, size: float?} }

        Returns:
            String base64 del gráfico
        """
        if not brands_metrics:
            return None

        fig, ax = plt.subplots(figsize=(12, 8))

        marcas = list(brands_metrics.keys())
        shares = [float(brands_metrics[m].get('market_share', 0)) for m in marcas]
        growths = [float(brands_metrics[m].get('growth_rate', 0)) for m in marcas]
        sizes = [float(brands_metrics[m].get('size', max(shares))) for m in marcas]

        # Escalar tamaños (50-1200)
        max_size = max(sizes) if sizes else 1
        bubble_sizes = [50 + (s / max_size) * 1150 for s in sizes]

        # Medianas para cuadrantes
        x_med = np.median(shares) if shares else 10
        y_med = np.median(growths) if growths else 0

        colors = []
        for s, g in zip(shares, growths):
            if s >= x_med and g >= y_med:
                colors.append(SUCCESS_COLOR)  # Stars
            elif s >= x_med and g < y_med:
                colors.append(BRAND_COLOR)    # Cash Cows
            elif s < x_med and g >= y_med:
                colors.append(WARNING_COLOR)  # Question Marks
            else:
                colors.append(NEUTRAL_COLOR)  # Dogs

        ax.scatter(shares, growths, s=bubble_sizes, c=colors, alpha=0.6, edgecolors='white', linewidth=2)

        for i, m in enumerate(marcas):
            ax.annotate(m, (shares[i], growths[i]), fontsize=10, fontweight='bold', ha='center', va='bottom')

        # Cuadrantes
        ax.axvline(x=x_med, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline(y=y_med, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        max_x = max(shares) if shares else 50
        max_y = max(growths) if growths else 20
        ax.text(x_med + (max_x - x_med) * 0.5, y_med + (max_y - y_med) * 0.8, 'STARS', fontsize=11, ha='center', fontweight='bold', color=SUCCESS_COLOR, alpha=0.7)
        ax.text(x_med + (max_x - x_med) * 0.5, y_med * 0.6, 'CASH COWS', fontsize=11, ha='center', fontweight='bold', color=BRAND_COLOR, alpha=0.7)
        ax.text(x_med * 0.5, y_med + (max_y - y_med) * 0.8, 'QUESTION MARKS', fontsize=11, ha='center', fontweight='bold', color=WARNING_COLOR, alpha=0.7)
        ax.text(x_med * 0.5, y_med * 0.6, 'DOGS', fontsize=11, ha='center', fontweight='bold', color=NEUTRAL_COLOR, alpha=0.7)

        ax.set_xlabel('Cuota (Share) %', fontsize=12, fontweight='bold')
        ax.set_ylabel('Crecimiento (%)', fontsize=12, fontweight='bold')
        ax.set_title('Matriz BCG (Share vs Growth)', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_esg_leadership_scatter(self, esg_data: Dict[str, Dict[str, Any]]) -> str:
        """
        Genera scatter plot de liderazgo ESG (SOV vs Score ESG, tamaño = Sentimiento)
        
        Args:
            esg_data: Dict con marcas y sus métricas
                Ej: {"Heineken": {"sov": 25.5, "esg_score": 3.5, "sentiment": 0.65}, ...}
        
        Returns:
            String base64 del gráfico
        """
        if not esg_data or len(esg_data) == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Extraer datos
        brands = []
        sov_values = []
        esg_scores = []
        sentiment_scores = []
        
        for brand, data in esg_data.items():
            brands.append(brand)
            sov_values.append(data.get('sov', 0))
            # Manejar nulos/ceros: visualmente usar mínimo 0.1 si score=0 para visibilidad, pero mostrar etiqueta real
            raw_esg = data.get('esg_score', 0)
            esg_scores.append(raw_esg if raw_esg is not None else 0)
            sentiment_scores.append(data.get('sentiment', 0))
        
        # Convertir sentimiento (-1 a 1) a tamaño de burbuja (100-800)
        sizes = [(sent + 1) * 350 + 100 for sent in sentiment_scores]
        
        # Colores según cuadrante estratégico
        colors = []
        for sov, esg in zip(sov_values, esg_scores):
            if sov >= 20 and esg >= 3:
                colors.append(SUCCESS_COLOR)  # Líderes sostenibles
            elif sov >= 20 and esg < 3:
                colors.append(DANGER_COLOR)  # Riesgo crítico (alto SOV, bajo ESG)
            elif sov < 20 and esg >= 3:
                colors.append(BRAND_COLOR)  # Oportunidad (bajo SOV, alto ESG)
            else:
                colors.append(NEUTRAL_COLOR)  # Rezagados
        
        # Crear scatter
        # Aplicar un mínimo visual para scores 0 sin alterar el dato real
        esg_visual = [0.1 if (v is not None and float(v) == 0.0) else (v or 0.0) for v in esg_scores]

        ax.scatter(sov_values, esg_visual, s=sizes, c=colors, 
                  alpha=0.6, edgecolors='white', linewidth=2)
        
        # Añadir etiquetas
        for i, brand in enumerate(brands):
            ax.annotate(brand, (sov_values[i], esg_visual[i]), 
                       fontsize=10, fontweight='bold', ha='center', va='bottom')
        
        # Líneas divisoras (cuadrantes)
        sov_median = np.median(sov_values) if sov_values else 20
        esg_median = np.median(esg_scores) if esg_scores else 3
        
        ax.axhline(y=esg_median, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(x=sov_median, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        # Etiquetas de cuadrantes
        max_sov = max(sov_values) if sov_values else 50
        max_esg = max(esg_scores) if esg_scores else 5
        
        ax.text(sov_median + (max_sov - sov_median) * 0.5, 
               esg_median + (max_esg - esg_median) * 0.7, 
               'LÍDERES\nSOSTENIBLES', fontsize=11, ha='center', 
               fontweight='bold', color=SUCCESS_COLOR, alpha=0.7)
        
        ax.text(sov_median + (max_sov - sov_median) * 0.5, 
               esg_median * 0.5, 
               'RIESGO\nCRÍTICO', fontsize=11, ha='center', 
               fontweight='bold', color=DANGER_COLOR, alpha=0.7)
        
        ax.text(sov_median * 0.3, 
               esg_median + (max_esg - esg_median) * 0.7, 
               'OPORTUNIDAD\nESG', fontsize=11, ha='center', 
               fontweight='bold', color=BRAND_COLOR, alpha=0.7)
        
        ax.text(sov_median * 0.3, esg_median * 0.5, 
               'REZAGADOS', fontsize=11, ha='center', 
               fontweight='bold', color=NEUTRAL_COLOR, alpha=0.7)
        
        # Configurar ejes
        ax.set_xlabel('Share of Voice (%)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score ESG (0-5) [puntos en 0 ajustados a 0.1 para visibilidad]', fontsize=12, fontweight='bold')
        ax.set_title('Matriz de Liderazgo ESG\n(Tamaño de burbuja = Sentimiento)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Leyenda de tamaño
        legend_sizes = [100, 350, 600]
        legend_labels = ['Sent. Bajo\n(-1.0)', 'Sent. Neutral\n(0.0)', 'Sent. Alto\n(+1.0)']
        legend_handles = [plt.scatter([], [], s=s, c='gray', alpha=0.5, edgecolors='white', linewidth=2) 
                         for s in legend_sizes]
        legend1 = ax.legend(legend_handles, legend_labels, loc='upper left', 
                          title='Sentimiento', framealpha=0.9, fontsize=9)
        ax.add_artist(legend1)
        
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

    # Helper: seleccionar top N marcas (por SOV actual si existe; fallback a tendencias)
    def select_top_brands(max_n: int) -> List[str]:
        competencia = report_data.get('competencia', {}) or {}
        sov_now = competencia.get('sov_data') or {}
        if isinstance(sov_now, dict) and sov_now:
            return [m for m, _ in sorted(sov_now.items(), key=lambda x: x[1], reverse=True)[:max_n]]
        # Fallback: usar último valor de tendencia de SOV
        sov_trend = competencia.get('sov_trend_data') or {}
        if isinstance(sov_trend, dict) and sov_trend:
            last_values = []
            for marca, serie in sov_trend.items():
                try:
                    last = serie[-1]['sov'] if (isinstance(serie, list) and serie) else 0
                except Exception:
                    last = 0
                last_values.append((marca, float(last)))
            return [m for m, _ in sorted(last_values, key=lambda x: x[1], reverse=True)[:max_n]]
        # Fallback final: intentar sentimiento por marca
        sent = report_data.get('sentimiento_reputacion', {}) or {}
        sent_data = sent.get('sentiment_data') or {}
        if isinstance(sent_data, dict) and sent_data:
            # ordenar por positivo descendente como proxy
            scores = []
            for marca, dist in sent_data.items():
                pos = 0.0
                try:
                    pos = float(dist.get('positivo', 0) or 0)
                except Exception:
                    pos = 0.0
                scores.append((marca, pos))
            return [m for m, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:max_n]]
        # Si no hay nada, retornar lista vacía (no se filtrará)
        return []

    top_brands = select_top_brands(generator.max_brands)

    def filter_dict_by_brands(data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict) or not data:
            return data
        if not top_brands:
            return data
        return {k: v for k, v in data.items() if k in top_brands}
    
    # SOV Charts (snapshot actual)
    competencia = report_data.get('competencia', {})
    if competencia.get('sov_data'):
        sov_now_filtered = filter_dict_by_brands(competencia['sov_data'])
        charts['sov_chart'] = generator.generate_sov_chart(sov_now_filtered)
        charts['sov_pie_chart'] = generator.generate_sov_pie_chart(sov_now_filtered)
    
    # SOV Trend Chart (evolución temporal)
    if competencia.get('sov_trend_data'):
        sov_trend = competencia['sov_trend_data']
        if isinstance(sov_trend, dict) and sov_trend:
            sov_trend_filtered = {k: v for k, v in sov_trend.items() if not top_brands or k in top_brands}
        else:
            sov_trend_filtered = sov_trend
        charts['sov_trend_chart'] = generator.generate_sov_trend_chart(sov_trend_filtered)
    
    # Sentiment Chart (snapshot actual)
    sentimiento = report_data.get('sentimiento_reputacion', {})
    if sentimiento.get('sentiment_data'):
        sent_data_filtered = filter_dict_by_brands(sentimiento['sentiment_data'])
        charts['sentiment_chart'] = generator.generate_sentiment_chart(sent_data_filtered)
    
    # Sentiment Trend Chart (evolución temporal)
    if sentimiento.get('sentiment_trend_data'):
        sent_trend = sentimiento['sentiment_trend_data']
        if isinstance(sent_trend, dict) and sent_trend:
            sent_trend_filtered = {k: v for k, v in sent_trend.items() if not top_brands or k in top_brands}
        else:
            sent_trend_filtered = sent_trend
        charts['sentiment_trend_chart'] = generator.generate_sentiment_trend_chart(sent_trend_filtered)
    
    # Opportunity Matrix
    opp_riesgos = report_data.get('oportunidades_riesgos', {})
    
    # Lógica defensiva para oportunidades: debe ser una lista de dicts
    opportunities = opp_riesgos.get('oportunidades', [])
    if isinstance(opportunities, str) or not isinstance(opportunities, list):
        opportunities = []
    # Normalizar si es lista de strings → lista de dicts con defaults
    if isinstance(opportunities, list) and opportunities:
        if all(isinstance(o, str) for o in opportunities):
            opportunities = [
                {
                    'titulo': o,
                    'impacto': 'medio',
                    'esfuerzo': 'medio'
                }
                for o in opportunities
            ]
        else:
            # Asegurar claves requeridas con defaults si faltan
            normalized_ops = []
            for i, o in enumerate(opportunities):
                if isinstance(o, dict):
                    normalized_ops.append({
                        'titulo': str(o.get('titulo', f'Oportunidad {i+1}')),
                        'impacto': str(o.get('impacto', 'medio')),
                        'esfuerzo': str(o.get('esfuerzo', 'medio'))
                    })
            opportunities = normalized_ops
    
    if opportunities:
        charts['opportunity_matrix'] = generator.generate_opportunity_matrix(opportunities)
    
    # Risk Matrix
    # Lógica defensiva para riesgos: debe ser una lista de dicts
    risks = opp_riesgos.get('riesgos', [])
    if isinstance(risks, str) or not isinstance(risks, list):
        risks = []
    # Normalizar si es lista de strings → lista de dicts con defaults
    if isinstance(risks, list) and risks:
        if all(isinstance(r, str) for r in risks):
            risks = [
                {
                    'titulo': r,
                    'probabilidad': 'media',
                    'severidad': 'media'
                }
                for r in risks
            ]
        else:
            normalized_risks = []
            for i, r in enumerate(risks):
                if isinstance(r, dict):
                    normalized_risks.append({
                        'titulo': str(r.get('titulo', f'Riesgo {i+1}')),
                        'probabilidad': str(r.get('probabilidad', 'media')),
                        'severidad': str(r.get('severidad', 'media'))
                    })
            risks = normalized_risks
    
    if risks:
        charts['risk_matrix'] = generator.generate_risk_matrix(risks)

    # Waterfall SOV (si hay pasos disponibles)
    if competencia.get('sov_waterfall') and isinstance(competencia['sov_waterfall'], list):
        charts['waterfall_chart'] = generator.generate_waterfall_chart(competencia['sov_waterfall'])
    
    # Timeline
    plan = report_data.get('plan_90_dias', {})
    
    # Lógica defensiva para iniciativas: debe ser una lista de dicts
    iniciativas = plan.get('iniciativas', [])
    if isinstance(iniciativas, str) or not isinstance(iniciativas, list):
        iniciativas = []
    if isinstance(iniciativas, list) and iniciativas:
        if all(isinstance(i, str) for i in iniciativas):
            iniciativas = [
                {
                    'titulo': i,
                    'timeline': '0-30 días',
                    'prioridad': 'media'
                }
                for i in iniciativas
            ]
        else:
            normalized_inits = []
            for i, it in enumerate(iniciativas):
                if isinstance(it, dict):
                    normalized_inits.append({
                        'titulo': str(it.get('titulo', f'Iniciativa {i+1}')),
                        'timeline': str(it.get('timeline', '0-30 días')),
                        'prioridad': str(it.get('prioridad', 'media'))
                    })
            iniciativas = normalized_inits
    
    if iniciativas:
        charts['timeline_chart'] = generator.generate_timeline_chart(iniciativas)
    
    # ===== NUEVOS GRÁFICOS ESTRATÉGICOS =====
    
    # Radar de Atributos por Marca
    atributos = report_data.get('atributos', {})
    if atributos.get('por_marca'):
        attrs_by_brand = atributos['por_marca']
        if isinstance(attrs_by_brand, dict) and attrs_by_brand:
            attrs_filtered = filter_dict_by_brands(attrs_by_brand)
        else:
            attrs_filtered = attrs_by_brand
        charts['attribute_radar'] = generator.generate_attribute_radar_chart(attrs_filtered)
    
    # Penetración por Canal
    analisis_canales = report_data.get('analisis_canales', {})
    if analisis_canales.get('presencia_por_marca'):
        presencia = analisis_canales['presencia_por_marca']
        if isinstance(presencia, dict) and presencia:
            presencia_filtered = filter_dict_by_brands(presencia)
        else:
            presencia_filtered = presencia
        charts['channel_penetration'] = generator.generate_channel_penetration_chart(presencia_filtered)
    
    # Liderazgo ESG (requiere combinar datos de múltiples fuentes)
    analisis_esg = report_data.get('analisis_sostenibilidad_packaging', {})
    
    # Construir datos combinados para el scatter ESG
    if competencia.get('sov_data') and sentimiento.get('sentiment_scores'):
        esg_combined = {}
        
        # Iterar por marcas que tengan SOV (ya filtradas previamente)
        sov_source = filter_dict_by_brands(competencia.get('sov_data', {}) or {})
        for marca, sov_value in sov_source.items():
            esg_combined[marca] = {
                'sov': sov_value,
                'esg_score': 0,  # Default
                'sentiment': 0   # Default
            }
            
            # Añadir score ESG si existe
            if analisis_esg.get('scores_esg'):
                if isinstance(analisis_esg['scores_esg'], dict) and marca in analisis_esg['scores_esg']:
                    esg_val = analisis_esg['scores_esg'][marca]
                    if isinstance(esg_val, (int, float)):
                        esg_combined[marca]['esg_score'] = esg_val
                    elif isinstance(esg_val, dict):
                        esg_combined[marca]['esg_score'] = esg_val.get('score', esg_val.get('nivel', 0))
            
            # Añadir sentimiento si existe
            if isinstance(sentimiento.get('sentiment_scores'), dict) and marca in sentimiento['sentiment_scores']:
                sent_val = sentimiento['sentiment_scores'][marca]
                if isinstance(sent_val, (int, float)):
                    esg_combined[marca]['sentiment'] = sent_val
                elif isinstance(sent_val, dict):
                    esg_combined[marca]['sentiment'] = sent_val.get('score_medio', sent_val.get('score', 0))
        
        if len(esg_combined) >= 2:  # Solo generar si hay al menos 2 marcas
            charts['esg_leadership'] = generator.generate_esg_leadership_scatter(esg_combined)

    # Perceptual Map (Precio vs Calidad, tamaño=SOV)
    pricing_power = report_data.get('pricing_power', {})
    pm_data = pricing_power.get('perceptual_map') if isinstance(pricing_power, dict) else None
    if isinstance(pm_data, list) and len(pm_data) >= 2:
        if top_brands:
            pm_filtered = [item for item in pm_data if str(item.get('marca')) in set(top_brands)]
        else:
            pm_filtered = pm_data
        if len(pm_filtered) >= 2:
            charts['perceptual_map'] = generator.generate_perceptual_map(pm_filtered)

    # BCG Matrix (derivar si no se provee explícitamente)
    bcg_metrics = report_data.get('bcg_metrics')
    if not bcg_metrics:
        # Intentar construir a partir de SOV y su tendencia (dos últimos puntos)
        sov_now = competencia.get('sov_data') or {}
        sov_trend = competencia.get('sov_trend_data') or {}
        derived = {}
        if isinstance(sov_now, dict):
            for marca, share in sov_now.items():
                growth = 0.0
                if isinstance(sov_trend, dict) and marca in sov_trend and len(sov_trend[marca]) >= 2:
                    last = sov_trend[marca][-1].get('sov', 0)
                    prev = sov_trend[marca][-2].get('sov', 0) or 0
                    denom = prev if abs(prev) > 1e-6 else max(last, 1)
                    growth = ((last - prev) / denom) * 100
                derived[marca] = {
                    'market_share': float(share),
                    'growth_rate': float(growth),
                    'size': float(share)
                }
        bcg_metrics = derived

    if isinstance(bcg_metrics, dict) and len(bcg_metrics) >= 2:
        if top_brands:
            bcg_filtered = {k: v for k, v in bcg_metrics.items() if k in top_brands}
        else:
            bcg_filtered = bcg_metrics
        if isinstance(bcg_filtered, dict) and len(bcg_filtered) >= 2:
            charts['bcg_matrix'] = generator.generate_bcg_matrix(bcg_filtered)
    
    return charts

