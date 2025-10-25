"""Analytics Agents package"""

from src.analytics.agents.base_agent import BaseAgent
from src.analytics.agents.quantitative_agent import QuantitativeAgent
from src.analytics.agents.qualitative_extraction_agent import QualitativeExtractionAgent
from src.analytics.agents.sentiment_agent import SentimentAgent
from src.analytics.agents.competitive_agent import CompetitiveAgent
from src.analytics.agents.trends_agent import TrendsAgent
from src.analytics.agents.strategic_agent import StrategicAgent
from src.analytics.agents.synthesis_agent import SynthesisAgent
from src.analytics.agents.executive_agent import ExecutiveAgent
# NUEVOS AGENTES FMCG ESPECIALIZADOS
from src.analytics.agents.campaign_analysis_agent import CampaignAnalysisAgent
from src.analytics.agents.channel_analysis_agent import ChannelAnalysisAgent
from src.analytics.agents.esg_analysis_agent import ESGAnalysisAgent
from src.analytics.agents.packaging_analysis_agent import PackagingAnalysisAgent
from src.analytics.agents.transversal_agent import TransversalAgent
from src.analytics.agents.customer_journey_agent import CustomerJourneyAgent
from src.analytics.agents.scenario_planning_agent import ScenarioPlanningAgent
from src.analytics.agents.pricing_power_agent import PricingPowerAgent
from src.analytics.agents.roi_agent import ROIAgent

__all__ = [
    'BaseAgent',
    'QuantitativeAgent',
    'QualitativeExtractionAgent',
    'SentimentAgent',
    'CompetitiveAgent',
    'TrendsAgent',
    'StrategicAgent',
    'SynthesisAgent',
    'ExecutiveAgent',
    'CampaignAnalysisAgent',
    'ChannelAnalysisAgent',
    'ESGAnalysisAgent',
    'PackagingAnalysisAgent',
    'TransversalAgent',
    'CustomerJourneyAgent',
    'ScenarioPlanningAgent',
    'PricingPowerAgent',
    'ROIAgent'
]

