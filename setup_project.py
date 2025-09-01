#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SETUP PROJECT - Script de configuración automática del proyecto
Johnson Controls - Sistema de Seguimiento Industrial
"""

import os
from pathlib import Path
import json


def create_directory_structure():
    """Crear estructura de directorios"""
    directories = [
        'src',
        'src/core',
        'src/hardware', 
        'src/web',
        'src/web/api',
        'src/web/static',
        'src/web/static/css',
        'src/web/static/js',
        'src/web/static/assets',
        'src/web/templates',
        'src/web/templates/components',
        'src/models',
        'src/services', 
        'src/utils',
        'src/database',
        'src/database/migrations',
        'config',
        'data',
        'data/excel',
        'data/json',
        'data/logs',
        'data/backup',
        'tests',
        'tests/test_core',
        'tests/test_hardware',
        'tests/test_web',
        'tests/test_integration',
        'docs',
        'scripts'
    ]
    
    print("Creando estructura de directorios...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ {directory}")


def create_init_files():
    """Crear archivos __init__.py"""
    init_files = {
        'src/__init__.py': '''"""
Johnson Controls - Sistema de Seguimiento Industrial
Paquete principal del sistema
"""

__version__ = "2.0.0"
__author__ = "Johnson Controls Development Team"
__description__ = "Sistema de Seguimiento Industrial con Zebra DS3678"
''',
        
        'src/core/__init__.py': '''"""
Módulos centrales del sistema de seguimiento
"""

try:
    from .scanner_manager import ScannerManager
    __all__ = ['ScannerManager']
except ImportError:
    __all__ = []
''',
        
        'src/hardware/__init__.py': '''"""
Interfaces de hardware para dispositivos
"""

try:
    from .zebra_scanner import ZebraScanner
    from .serial_interface import SerialInterface
    __all__ = ['ZebraScanner', 'SerialInterface']
except ImportError:
    __all__ = []
''',
        
        'src/models/__init__.py': '''"""
Modelos de datos del sistema
"""

try:
    from .product import JCIProduct, ProductStatus, QualityMetrics
    __all__ = ['JCIProduct', 'ProductStatus', 'QualityMetrics']
except ImportError:
    __all__ = []
''',
        
        'src/services/__init__.py': '''"""
Servicios de aplicación
"""

try:
    from .data_sync_service import DataSyncService
    from .analytics_service import AnalyticsService
    from .notification_service import NotificationService
    __all__ = ['DataSyncService', 'AnalyticsService', 'NotificationService']
except ImportError:
    __all__ = []
''',
        
        'src/utils/__init__.py': '''"""
Utilidades del sistema
"""

try:
    from .config import config, ConfigManager
    from .logger import get_logger, setup_logging
    __all__ = ['config', 'ConfigManager', 'get_logger', 'setup_logging']
except ImportError:
    __all__ = []
''',
        
        'src/web/__init__.py': '''"""
Componentes web del sistema
"""

try:
    from .app import WebApplication
    __all__ = ['WebApplication']
except ImportError:
    __all__ = []
''',
        
        'src/web/api/__init__.py': '''"""
APIs REST del sistema
"""

try:
    from .data_api import DataAPI
    from .control_api import ControlAPI  
    from .analytics_api import AnalyticsAPI
    __all__ = ['DataAPI', 'ControlAPI', 'AnalyticsAPI']
except ImportError:
    __all__ = []
''',
        
        'tests/__init__.py': '# Tests package',
        'src/database/__init__.py': '# Database package',
    }
    
    print("\nCreando archivos __init__.py...")
    for file_path, content in init_files.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ {file_path}")


def create_config_files():
    """Crear archivos de configuración"""
    configs = {
        'config/development.json': {
            "hardware": {
                "serial_port": "COM5",
                "baud_rate": 9600,
                "scanner_model": "Zebra_DS3678",
                "timeout": 0.1,
                "retry_attempts": 3
            },
            "database": {
                "excel_tracking_file": "SEGUIMIENTO_JCI_PROYECTO.xlsx",
                "excel_data_file": "DATOS_JCI_PROYECTO.xlsx",
                "json_state_file": "sistema_estado.json",
                "json_commands_file": "comandos_web.json",
                "backup_enabled": True,
                "backup_interval": 300
            },
            "web": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": True,
                "auto_reload": True,
                "cors_enabled": True,
                "session_timeout": 3600
            },
            "johnson_controls": {
                "plant_id": "JCI_MX_DEV_001",
                "plant_name": "Planta Durango - Desarrollo",
                "department": "Manufactura - Testing",
                "shift_start": "06:00",
                "shift_end": "22:00",
                "quality_standards": {
                    "max_cycle_time": 420,
                    "quality_threshold": 95,
                    "alert_threshold": 85
                }
            },
            "system": {
                "environment": "development",
                "log_level": "DEBUG",
                "auto_update_interval": 3,
                "data_retention_days": 30,
                "enable_analytics": True,
                "enable_notifications": True
            }
        },
        
        'config/production.json': {
            "hardware": {
                "serial_port": "COM3",
                "baud_rate": 9600,
                "scanner_model": "Zebra_DS3678",
                "timeout": 0.5,
                "retry_attempts": 5
            },
            "database": {
                "excel_tracking_file": "SEGUIMIENTO_JCI_PRODUCCION.xlsx",
                "excel_data_file": "DATOS_JCI_PRODUCCION.xlsx",
                "json_state_file": "sistema_estado_prod.json",
                "json_commands_file": "comandos_web_prod.json",
                "backup_enabled": True,
                "backup_interval": 180
            },
            "web": {
                "host": "0.0.0.0",
                "port": 8080,
                "debug": False,
                "auto_reload": False,
                "cors_enabled": False,
                "session_timeout": 7200
            },
            "johnson_controls": {
                "plant_id": "JCI_MX_PROD_001",
                "plant_name": "Johnson Controls Planta Durango",
                "department": "Manufactura Industrial",
                "shift_start": "06:00",
                "shift_end": "22:00",
                "quality_standards": {
                    "max_cycle_time": 300,
                    "quality_threshold": 98,
                    "alert_threshold": 90
                }
            },
            "system": {
                "environment": "production",
                "log_level": "INFO",
                "auto_update_interval": 5,
                "data_retention_days": 90,
                "enable_analytics": True,
                "enable_notifications": True
            }
        }
    }
    
    print("\nCreando archivos de configuración...")
    for file_path, config_data in configs.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print(f"✓ {file_path}")


def create_placeholder_files():
    """Crear archivos placeholder para componentes faltantes"""
    placeholders = {
        'src/models/stage.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STAGE MODELS - Modelos de etapas del proceso
Johnson Controls - Sistema de Seguimiento Industrial
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Stage:
    """Modelo de etapa del proceso"""
    id: int
    name: str
    operator_id: str
    operator_name: str
    target_time: int = 300
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'target_time': self.target_time
        }
''',
        
        'src/models/analytics.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYTICS MODELS - Modelos para analytics y métricas
Johnson Controls - Sistema de Seguimiento Industrial
"""

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class AnalyticsModel:
    """Modelo base para analytics"""
    timestamp: str
    metric_name: str
    value: float
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'metric_name': self.metric_name,
            'value': self.value,
            'unit': self.unit
        }
''',
        
        'src/core/product_manager.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRODUCT MANAGER - Gestor de productos
Johnson Controls - Sistema de Seguimiento Industrial
"""

from ..utils.logger import get_logger

class ProductManager:
    """Gestor de productos del sistema"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.products = {}
        
    def initialize(self) -> bool:
        """Inicializar gestor de productos"""
        self.logger.info("Product Manager inicializado")
        return True
''',
        
        'src/core/stage_manager.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STAGE MANAGER - Gestor de etapas del proceso
Johnson Controls - Sistema de Seguimiento Industrial
"""

from ..utils.logger import get_logger

class StageManager:
    """Gestor de etapas del proceso"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.stages = {}
        
    def initialize(self) -> bool:
        """Inicializar gestor de etapas"""
        self.logger.info("Stage Manager inicializado")
        return True
''',
        
        'src/core/workflow_engine.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WORKFLOW ENGINE - Motor de flujo de trabajo
Johnson Controls - Sistema de Seguimiento Industrial
"""

from ..utils.logger import get_logger

class WorkflowEngine:
    """Motor de flujo de trabajo"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    def initialize(self) -> bool:
        """Inicializar motor de flujo"""
        self.logger.info("Workflow Engine inicializado")
        return True
''',
        
        'src/hardware/hardware_manager.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HARDWARE MANAGER - Gestor general de hardware
Johnson Controls - Sistema de Seguimiento Industrial
"""

from ..utils.logger import get_logger

class HardwareManager:
    """Gestor general de hardware"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    def initialize(self) -> bool:
        """Inicializar gestor de hardware"""
        self.logger.info("Hardware Manager inicializado")
        return True
''',
        
        'src/utils/validators.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDATORS - Utilidades de validación
Johnson Controls - Sistema de Seguimiento Industrial
"""

def validate_barcode(barcode: str) -> bool:
    """Validar código de barras"""
    if not barcode or len(barcode) < 8:
        return False
    return barcode.replace('-', '').replace('_', '').isalnum()

def validate_stage(stage: int) -> bool:
    """Validar etapa"""
    return isinstance(stage, int) and 1 <= stage <= 6
''',
        
        'run_scanner.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUN SCANNER - Ejecutar solo el sistema de escaneo
"""

if __name__ == "__main__":
    import sys
    sys.argv.extend(["--mode", "scanner"])
    from main import main
    main()
''',
        
        'run_web.py': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUN WEB - Ejecutar solo el servidor web
"""

if __name__ == "__main__":
    import sys
    sys.argv.extend(["--mode", "web"])
    from main import main
    main()
''',
        
        '.gitignore': '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
data/logs/*
!data/logs/.gitkeep

# Data files
data/json/*.json
data/excel/*.xlsx
data/backup/*
!data/backup/.gitkeep

# Config files (except examples)
config/local.json
config/custom.json

# OS
.DS_Store
Thumbs.db

# Temp files
*.tmp
*.temp
'''
    }
    
    print("\nCreando archivos placeholder...")
    for file_path, content in placeholders.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ {file_path}")


def create_gitkeep_files():
    """Crear archivos .gitkeep para directorios vacíos"""
    gitkeep_dirs = [
        'data/logs',
        'data/backup',
        'src/web/static/css',
        'src/web/static/js',
        'src/web/static/assets',
        'src/web/templates/components',
        'tests/test_core',
        'tests/test_hardware',
        'tests/test_web',
        'tests/test_integration'
    ]
    
    print("\nCreando archivos .gitkeep...")
    for directory in gitkeep_dirs:
        gitkeep_file = Path(directory) / '.gitkeep'
        gitkeep_file.touch()
        print(f"✓ {gitkeep_file}")


def create_requirements():
    """Crear archivo requirements.txt"""
    requirements = """# Johnson Controls - Sistema de Seguimiento Industrial
# Dependencias mínimas para funcionamiento básico

# Framework Web
Flask==2.3.2
Flask-CORS==4.0.0

# Comunicación Serie
pyserial==3.5

# Manejo de archivos Excel
openpyxl==3.1.2

# Utilidades de datos
python-dateutil==2.8.2

# Para variables de entorno
python-dotenv==1.0.0

# Testing (opcional)
# pytest==7.4.0
# pytest-cov==4.1.0

# Desarrollo (opcional)
# black==23.7.0
# flake8==6.0.0

# Para análisis de datos (opcional)
# numpy==1.24.3
# pandas==2.0.3

# Para monitoreo del sistema (opcional)
# psutil==5.9.5
"""
    
    print("\nCreando requirements.txt...")
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(requirements)
    print("✓ requirements.txt")


def main():
    """Función principal de configuración"""
    print("="*60)
    print("JOHNSON CONTROLS - CONFIGURACIÓN DEL PROYECTO")
    print("="*60)
    
    try:
        create_directory_structure()
        create_init_files()
        create_config_files()
        create_placeholder_files()
        create_gitkeep_files()
        create_requirements()
        
        print("\n" + "="*60)
        print("✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\nPróximos pasos:")
        print("1. Instalar dependencias: pip install -r requirements.txt")
        print("2. Ejecutar sistema: python main.py --mode full")
        print("3. Acceder al dashboard: http://localhost:5000")
        print("\nModos disponibles:")
        print("- python main.py --mode full      # Sistema completo")
        print("- python main.py --mode web       # Solo servidor web")
        print("- python main.py --mode scanner   # Solo sistema de escaneo")
        print("- python main.py --mode console   # Modo consola")
        
    except Exception as e:
        print(f"\n❌ Error en configuración: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main()