#!/usr/bin/env python3
# run_web.py - Ejecutar solo el servidor web
# -*- coding: utf-8 -*-
"""
RUN WEB - Ejecutar solo servidor web
Johnson Controls - Sistema de Seguimiento Industrial
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("🌐 JOHNSON CONTROLS - SERVIDOR WEB")
    print("=" * 50)
    
    try:
        # Intentar usar sistema principal
        try:
            from main import main as main_func
            sys.argv = ['run_web.py', '--mode', 'web']
            main_func()
        except ImportError:
            # Fallback a sistema seguro
            from safe_main import main as safe_main_func
            sys.argv = ['run_web.py', '--mode', 'web']
            safe_main_func()
    except Exception as e:
        print(f"❌ Error ejecutando servidor web: {e}")
        print("\n💡 Soluciones:")
        print("1. python setup_project.py")
        print("2. pip install -r requirements.txt")
        print("3. python start_basic.py")

if __name__ == "__main__":
    main()