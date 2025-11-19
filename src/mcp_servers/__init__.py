"""
MCP服务器模块
提供专业水电模型的MCP接口
"""

from .flood_evolution_mcp import FloodEvolutionMCPServer
from .reservoir_simulation_mcp import ReservoirSimulationMCPServer
from .anomaly_detection_mcp import AnomalyDetectionMCPServer
from .risk_assessment_mcp import RiskAssessmentMCPServer
from .prediction_mcp import PredictionMCPServer

__all__ = [
    'FloodEvolutionMCPServer',
    'ReservoirSimulationMCPServer',
    'AnomalyDetectionMCPServer',
    'RiskAssessmentMCPServer',
    'PredictionMCPServer'
]