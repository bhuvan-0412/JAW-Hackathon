"""
Integration package connecting Role A (Extraction), Role B (Graph/Store), and Role C (Reasoning Engine).
"""

from .adapters import RoleAAdapter, RoleBAdapter, RoleCAdapter, BaselineRoleCAdapter
from .orchestrator import PipelineOrchestrator

__all__ = [
    "RoleAAdapter",
    "RoleBAdapter",
    "RoleCAdapter",
    "BaselineRoleCAdapter",
    "PipelineOrchestrator",
]
