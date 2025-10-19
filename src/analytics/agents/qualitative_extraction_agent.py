"""
Qualitative Extraction Agent
Análisis cualitativo unificado (sentimiento + atributos) usando LLM sobre 100% de datos textuales
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import extract
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import Query, QueryExecution, Marca
from src.query_executor.api_clients import AnthropicClient


class QualitativeExtractionAgent(BaseAgent):
    """
    Agente de extracción cualitativa unificado
    Analiza el 100% de respuestas textuales para extraer:
    - Sentimiento por marca
    - Atributos por marca
    - Temas emergentes
    - Insights cualitativos clave
    """
    
    def __init__(self, session, version: str = "2.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()
        self.load_prompts()
        # Límite de caracteres por batch para Claude (200K tokens ≈ 800K chars)
        self.max_chars_per_batch = 700000
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('qualitative_extraction_agent', {}).get('task', '')
        else:
            self.task_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Prompt por defecto si no hay config"""
        return """
        Analiza TODOS los siguientes textos sobre las marcas: {marcas}
        
        TEXTOS:
        {textos}
        
        Devuelve JSON con:
        {{
          "sentimiento_por_marca": {{
            "Marca X": {{
              "score_medio": float (-1 a 1),
              "tono": "positivo|neutral|negativo",
              "intensidad": "alta|media|baja",
              "distribucion": {{"positivo": int, "neutral": int, "negativo": int}}
            }}
          }},
          "atributos_por_marca": {{
            "Marca X": {{
              "calidad": ["premium", "consistente"],
              "precio": ["alto", "justificado"],
              "innovacion": ["innovador"]
            }}
          }},
          "temas_emergentes": ["tema 1", "tema 2"],
          "insights_cualitativos": ["insight 1", "insight 2"]
        }}
        """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis cualitativo completo sobre 100% de datos textuales
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis cualitativo completo
        """
        year, month = map(int, periodo.split('-'))
        
        # 1. Obtener marcas
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas'}
        
        marca_nombres = [m.nombre for m in marcas]
        
        # 2. Obtener TODAS las ejecuciones con respuesta_texto
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            extract('month', QueryExecution.timestamp) == month,
            extract('year', QueryExecution.timestamp) == year,
            QueryExecution.respuesta_texto.isnot(None)
        ).all()
        
        if not executions:
            return {'error': 'No hay datos textuales para analizar'}
        
        self.logger.info(
            f"Analizando {len(executions)} respuestas textuales (100% de datos)",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # 3. Procesar en batches si es necesario
        batches = self._create_batches(executions)
        
        self.logger.info(
            f"Procesando en {len(batches)} batch(es)",
            total_textos=len(executions)
        )
        
        # 4. Analizar cada batch con Claude
        batch_results = []
        for i, batch_texts in enumerate(batches, 1):
            self.logger.info(f"Procesando batch {i}/{len(batches)}")
            
            # Construir prompt
            prompt = self.task_prompt.format(
                marcas=', '.join(marca_nombres),
                textos='\n\n---\n\n'.join(batch_texts)
            )
            
            try:
                # Llamar a Claude (soporta contextos largos)
                result = self.client.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=4000,
                    json_mode=True
                )
                
                # Parsear JSON
                batch_data = json.loads(result['response_text'])
                batch_results.append(batch_data)
                
            except Exception as e:
                self.logger.error(
                    f"Error procesando batch {i}: {e}",
                    exc_info=True
                )
                # Continuar con el siguiente batch
                continue
        
        if not batch_results:
            return {'error': 'No se pudo procesar ningún batch correctamente'}
        
        # 5. Agregar resultados de todos los batches
        resultado_final = self._aggregate_batches(batch_results, marca_nombres)
        
        # 6. Añadir metadata
        resultado_final['periodo'] = periodo
        resultado_final['categoria_id'] = categoria_id
        resultado_final['metadata'] = {
            'textos_analizados': len(executions),
            'total_caracteres': sum(len(e.respuesta_texto or '') for e in executions),
            'batches_procesados': len(batch_results),
            'metodo': 'llm_full_analysis_claude'
        }
        
        # 7. Guardar
        self.save_results(categoria_id, periodo, resultado_final)
        
        return resultado_final
    
    def _create_batches(self, executions: List) -> List[List[str]]:
        """
        Divide las ejecuciones en batches manejables por límite de tokens
        
        Args:
            executions: Lista de QueryExecution
        
        Returns:
            Lista de batches, cada batch es lista de strings (textos)
        """
        batches = []
        current_batch = []
        current_chars = 0
        
        for execution in executions:
            texto = execution.respuesta_texto or ''
            texto_length = len(texto)
            
            # Si añadir este texto superaría el límite, crear nuevo batch
            if current_chars + texto_length > self.max_chars_per_batch and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            
            # Truncar textos individuales muy largos
            if texto_length > 3000:
                texto = texto[:3000] + "... [truncado]"
            
            current_batch.append(texto)
            current_chars += len(texto)
        
        # Añadir último batch
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _aggregate_batches(self, batch_results: List[Dict], marca_nombres: List[str]) -> Dict[str, Any]:
        """
        Agrega resultados de múltiples batches en un resultado unificado
        
        Args:
            batch_results: Lista de resultados de cada batch
            marca_nombres: Lista de nombres de marcas
        
        Returns:
            Dict con resultados agregados
        """
        # Agregar sentimientos
        sentimiento_agregado = {}
        for marca in marca_nombres:
            scores = []
            tonos = []
            intensidades = []
            distribuciones = {'positivo': 0, 'neutral': 0, 'negativo': 0}
            
            for batch in batch_results:
                marca_data = batch.get('sentimiento_por_marca', {}).get(marca, {})
                if marca_data:
                    if 'score_medio' in marca_data:
                        scores.append(marca_data['score_medio'])
                    if 'tono' in marca_data:
                        tonos.append(marca_data['tono'])
                    if 'intensidad' in marca_data:
                        intensidades.append(marca_data['intensidad'])
                    if 'distribucion' in marca_data:
                        for key in ['positivo', 'neutral', 'negativo']:
                            distribuciones[key] += marca_data['distribucion'].get(key, 0)
            
            sentimiento_agregado[marca] = {
                'score_medio': sum(scores) / len(scores) if scores else 0.0,
                'tono': max(set(tonos), key=tonos.count) if tonos else 'neutral',
                'intensidad': max(set(intensidades), key=intensidades.count) if intensidades else 'baja',
                'distribucion': distribuciones,
                'menciones_analizadas': sum(distribuciones.values())
            }
        
        # Agregar atributos (unión de todos los atributos encontrados)
        atributos_agregados = {}
        for marca in marca_nombres:
            atributos_marca = {}
            
            for batch in batch_results:
                marca_attrs = batch.get('atributos_por_marca', {}).get(marca, {})
                for categoria_attr, valores in marca_attrs.items():
                    if categoria_attr not in atributos_marca:
                        atributos_marca[categoria_attr] = []
                    # Añadir valores únicos
                    atributos_marca[categoria_attr].extend(
                        v for v in valores if v not in atributos_marca[categoria_attr]
                    )
            
            atributos_agregados[marca] = atributos_marca
        
        # Agregar temas emergentes (unión de todos)
        temas_emergentes = []
        for batch in batch_results:
            temas = batch.get('temas_emergentes', [])
            temas_emergentes.extend(t for t in temas if t not in temas_emergentes)
        
        # Agregar insights cualitativos (unión de todos)
        insights_cualitativos = []
        for batch in batch_results:
            insights = batch.get('insights_cualitativos', [])
            insights_cualitativos.extend(i for i in insights if i not in insights_cualitativos)
        
        return {
            'sentimiento_por_marca': sentimiento_agregado,
            'atributos_por_marca': atributos_agregados,
            'temas_emergentes': temas_emergentes[:10],  # Top 10
            'insights_cualitativos': insights_cualitativos[:10]  # Top 10
        }

