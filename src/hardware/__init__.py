# src/hardware/__init__.py
"""
Interfaces de hardware para dispositivos
"""

from .zebra_scanner import ZebraScanner
from .serial_interface import SerialInterface

__all__ = ['ZebraScanner', 'SerialInterface']