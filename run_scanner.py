#!/usr/bin/env python3
# run_scanner.py - Ejecutar solo el sistema de escaneo
# -*- coding: utf-8 -*-
"""
RUN SCANNER - Ejecutar solo sistema de escaneo
Johnson Controls - Sistema de Seguimiento Industrial
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("📱 JOHNSON CONTROLS - SISTEMA DE ESCANEO")
    print("=" * 50)
    
    try:
        # Intentar usar sistema principal
        try:
            from main import main as main_func
            sys.argv = ['run_scanner.py', '--mode', 'scanner']
            main_func()
        except ImportError:
            # Fallback a sistema seguro
            from safe_main import main as safe_main_func
            sys.argv = ['run_scanner.py', '--mode', 'scanner']
            safe_main_func()
    except Exception as e:
        print(f"❌ Error ejecutando sistema de escaneo: {e}")
        print("\n💡 Soluciones:")
        print("1. python setup_project.py")
        print("2. pip install -r requirements.txt")
        print("3. python quick_start.py")

if __name__ == "__main__":
    main()