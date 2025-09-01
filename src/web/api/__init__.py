# src/web/api/__init__.py
"""
APIs REST del sistema
"""

from .data_api import DataAPI
from .control_api import ControlAPI
from .analytics_api import AnalyticsAPI

__all__ = ['DataAPI', 'ControlAPI', 'AnalyticsAPI']