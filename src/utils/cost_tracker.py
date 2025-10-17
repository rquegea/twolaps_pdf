"""
Cost Tracker
Sistema de tracking de costes de APIs de IAs
"""

import os
import yaml
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


class CostTracker:
    """
    Rastrea costes de llamadas a APIs de LLMs
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Inicializa el cost tracker con precios de configuración
        """
        self.config_path = Path(config_path)
        self.load_pricing()
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET_USD", "500"))
        self.alert_threshold = float(os.getenv("ALERT_THRESHOLD_PERCENT", "80")) / 100
    
    def load_pricing(self):
        """Carga precios de config/settings.yaml"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.pricing = config.get('llm_providers', {}).get('cost_per_1k_tokens', {})
        else:
            # Precios por defecto si no hay config
            self.pricing = {
                'openai': {
                    'gpt-4o': {'input': 0.0025, 'output': 0.01},
                    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
                    'text-embedding-3-small': {'input': 0.00002}
                },
                'anthropic': {
                    'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
                    'claude-3-opus': {'input': 0.015, 'output': 0.075}
                },
                'google': {
                    'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005}
                }
            }
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int = 0
    ) -> float:
        """
        Calcula el coste de una llamada
        
        Args:
            provider: Proveedor (openai, anthropic, google)
            model: Modelo específico
            tokens_input: Tokens de entrada
            tokens_output: Tokens de salida
        
        Returns:
            Coste en USD
        """
        try:
            model_pricing = self.pricing.get(provider, {}).get(model, {})
            
            cost_input = (tokens_input / 1000) * model_pricing.get('input', 0)
            cost_output = (tokens_output / 1000) * model_pricing.get('output', 0)
            
            return cost_input + cost_output
        
        except Exception as e:
            print(f"Warning: Could not calculate cost for {provider}/{model}: {e}")
            return 0.0
    
    def get_monthly_spend(self, session) -> Dict[str, float]:
        """
        Obtiene el gasto del mes actual por proveedor
        
        Args:
            session: Sesión de SQLAlchemy
        
        Returns:
            Dict con gasto por proveedor y total
        """
        from sqlalchemy import func, extract
        from src.database.models import QueryExecution
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Query para obtener gastos del mes por proveedor
        monthly_costs = session.query(
            QueryExecution.proveedor_ia,
            func.sum(QueryExecution.coste_usd).label('total')
        ).filter(
            extract('month', QueryExecution.timestamp) == current_month,
            extract('year', QueryExecution.timestamp) == current_year
        ).group_by(
            QueryExecution.proveedor_ia
        ).all()
        
        result = {}
        total = 0.0
        
        for provider, cost in monthly_costs:
            cost = cost or 0.0
            result[provider] = cost
            total += cost
        
        result['total'] = total
        result['budget'] = self.monthly_budget
        result['budget_used_percent'] = (total / self.monthly_budget * 100) if self.monthly_budget > 0 else 0
        result['budget_remaining'] = self.monthly_budget - total
        
        return result
    
    def check_budget_alert(self, session) -> Optional[Dict]:
        """
        Verifica si se debe emitir una alerta de presupuesto
        
        Returns:
            Dict con información de alerta o None si no hay alerta
        """
        spend = self.get_monthly_spend(session)
        
        if spend['budget_used_percent'] >= (self.alert_threshold * 100):
            return {
                'alert': True,
                'message': f"⚠️  Alerta de presupuesto: {spend['budget_used_percent']:.1f}% usado",
                'total_spent': spend['total'],
                'budget': spend['budget'],
                'remaining': spend['budget_remaining']
            }
        
        return None
    
    def get_period_costs(
        self,
        session,
        categoria_id: int,
        periodo: str
    ) -> Dict[str, float]:
        """
        Obtiene costes de un periodo específico para una categoría
        
        Args:
            session: Sesión de SQLAlchemy
            categoria_id: ID de la categoría
            periodo: Periodo en formato YYYY-MM
        
        Returns:
            Dict con costes por proveedor
        """
        from sqlalchemy import func, extract
        from src.database.models import QueryExecution, Query
        
        year, month = map(int, periodo.split('-'))
        
        costs = session.query(
            QueryExecution.proveedor_ia,
            func.sum(QueryExecution.coste_usd).label('total'),
            func.sum(QueryExecution.tokens_input).label('total_tokens_in'),
            func.sum(QueryExecution.tokens_output).label('total_tokens_out'),
            func.count(QueryExecution.id).label('num_executions')
        ).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            extract('month', QueryExecution.timestamp) == month,
            extract('year', QueryExecution.timestamp) == year
        ).group_by(
            QueryExecution.proveedor_ia
        ).all()
        
        result = {
            'by_provider': {},
            'total_cost': 0.0,
            'total_tokens_input': 0,
            'total_tokens_output': 0,
            'total_executions': 0
        }
        
        for provider, cost, tokens_in, tokens_out, num_exec in costs:
            cost = cost or 0.0
            tokens_in = tokens_in or 0
            tokens_out = tokens_out or 0
            
            result['by_provider'][provider] = {
                'cost': cost,
                'tokens_input': tokens_in,
                'tokens_output': tokens_out,
                'executions': num_exec
            }
            
            result['total_cost'] += cost
            result['total_tokens_input'] += tokens_in
            result['total_tokens_output'] += tokens_out
            result['total_executions'] += num_exec
        
        return result
    
    def format_cost_report(self, costs: Dict) -> str:
        """
        Formatea un reporte de costes para impresión
        """
        lines = []
        lines.append("=" * 50)
        lines.append("REPORTE DE COSTES")
        lines.append("=" * 50)
        
        if 'by_provider' in costs:
            # Reporte de periodo
            lines.append(f"\nTotal: ${costs['total_cost']:.4f}")
            lines.append(f"Ejecuciones: {costs['total_executions']}")
            lines.append(f"Tokens entrada: {costs['total_tokens_input']:,}")
            lines.append(f"Tokens salida: {costs['total_tokens_output']:,}")
            lines.append("\nPor proveedor:")
            
            for provider, data in costs['by_provider'].items():
                lines.append(f"  {provider}:")
                lines.append(f"    Coste: ${data['cost']:.4f}")
                lines.append(f"    Ejecuciones: {data['executions']}")
                lines.append(f"    Tokens: {data['tokens_input']:,} in / {data['tokens_output']:,} out")
        else:
            # Reporte mensual
            lines.append(f"\nTotal gastado: ${costs['total']:.2f}")
            lines.append(f"Presupuesto: ${costs['budget']:.2f}")
            lines.append(f"Usado: {costs['budget_used_percent']:.1f}%")
            lines.append(f"Restante: ${costs['budget_remaining']:.2f}")
            lines.append("\nPor proveedor:")
            
            for provider in ['openai', 'anthropic', 'google']:
                if provider in costs:
                    lines.append(f"  {provider}: ${costs[provider]:.2f}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)


# Instancia global
cost_tracker = CostTracker()

