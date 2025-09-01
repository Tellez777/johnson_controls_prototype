#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONFIG MANAGER - Gestión centralizada de configuración
Johnson Controls - Sistema de Seguimiento Industrial
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class HardwareConfig:
    """Configuración de hardware"""
    serial_port: str = 'COM5'
    baud_rate: int = 9600
    scanner_model: str = 'Zebra_DS3678'
    timeout: float = 0.1
    retry_attempts: int = 3


@dataclass
class DatabaseConfig:
    """Configuración de base de datos/archivos"""
    excel_tracking_file: str = 'SEGUIMIENTO_JCI_PROYECTO.xlsx'
    excel_data_file: str = 'DATOS_JCI_PROYECTO.xlsx'
    json_state_file: str = 'sistema_estado.json'
    json_commands_file: str = 'comandos_web.json'
    backup_enabled: bool = True
    backup_interval: int = 300  # segundos


@dataclass
class WebConfig:
    """Configuración del servidor web"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False
    auto_reload: bool = False
    cors_enabled: bool = True
    session_timeout: int = 3600


@dataclass
class JohnsonControlsConfig:
    """Configuración específica de Johnson Controls"""
    plant_id: str = 'JCI_MX_001'
    plant_name: str = 'Planta Durango'
    department: str = 'Manufactura'
    shift_start: str = '06:00'
    shift_end: str = '22:00'
    quality_standards: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.quality_standards is None:
            self.quality_standards = {
                'max_cycle_time': 300,  # segundos
                'quality_threshold': 95,  # porcentaje
                'alert_threshold': 85
            }


@dataclass
class SystemConfig:
    """Configuración general del sistema"""
    environment: str = 'development'
    log_level: str = 'INFO'
    auto_update_interval: int = 3
    data_retention_days: int = 30
    enable_analytics: bool = True
    enable_notifications: bool = True


class ConfigManager:
    """Gestor centralizado de configuración"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuraciones por defecto
        self.hardware = HardwareConfig()
        self.database = DatabaseConfig()
        self.web = WebConfig()
        self.johnson_controls = JohnsonControlsConfig()
        self.system = SystemConfig()
        
        # Cargar configuración del ambiente
        self._load_environment_config()
    
    def _load_environment_config(self):
        """Cargar configuración según el ambiente"""
        env = os.getenv('JCI_ENV', 'development')
        config_file = self.config_dir / f"{env}.json"
        
        if config_file.exists():
            self._load_from_file(config_file)
        else:
            # Crear archivo de configuración por defecto
            self._create_default_config(env)
    
    def _load_from_file(self, config_file: Path):
        """Cargar configuración desde archivo JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Actualizar configuraciones
            if 'hardware' in config_data:
                self.hardware = HardwareConfig(**config_data['hardware'])
            
            if 'database' in config_data:
                self.database = DatabaseConfig(**config_data['database'])
            
            if 'web' in config_data:
                self.web = WebConfig(**config_data['web'])
            
            if 'johnson_controls' in config_data:
                self.johnson_controls = JohnsonControlsConfig(**config_data['johnson_controls'])
            
            if 'system' in config_data:
                self.system = SystemConfig(**config_data['system'])
                
        except Exception as e:
            print(f"Error cargando configuración: {e}")
    
    def _create_default_config(self, env: str):
        """Crear archivo de configuración por defecto"""
        config_data = {
            'hardware': asdict(self.hardware),
            'database': asdict(self.database),
            'web': asdict(self.web),
            'johnson_controls': asdict(self.johnson_controls),
            'system': asdict(self.system)
        }
        
        # Ajustar según ambiente
        if env == 'production':
            config_data['web']['debug'] = False
            config_data['system']['log_level'] = 'WARNING'
        elif env == 'development':
            config_data['web']['debug'] = True
            config_data['system']['log_level'] = 'DEBUG'
        
        config_file = self.config_dir / f"{env}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def save_config(self, env: Optional[str] = None):
        """Guardar configuración actual"""
        if env is None:
            env = self.system.environment
        
        config_data = {
            'hardware': asdict(self.hardware),
            'database': asdict(self.database),
            'web': asdict(self.web),
            'johnson_controls': asdict(self.johnson_controls),
            'system': asdict(self.system)
        }
        
        config_file = self.config_dir / f"{env}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def get_data_path(self, filename: str) -> Path:
        """Obtener ruta completa de archivo de datos"""
        return Path("data") / filename
    
    def get_excel_path(self, excel_type: str = 'tracking') -> Path:
        """Obtener ruta de archivo Excel"""
        if excel_type == 'tracking':
            return self.get_data_path("excel") / self.database.excel_tracking_file
        elif excel_type == 'data':
            return self.get_data_path("excel") / self.database.excel_data_file
        else:
            raise ValueError(f"Tipo de Excel desconocido: {excel_type}")
    
    def get_json_path(self, json_type: str) -> Path:
        """Obtener ruta de archivo JSON"""
        if json_type == 'state':
            return self.get_data_path("json") / self.database.json_state_file
        elif json_type == 'commands':
            return self.get_data_path("json") / self.database.json_commands_file
        else:
            raise ValueError(f"Tipo de JSON desconocido: {json_type}")
    
    def is_production(self) -> bool:
        """Verificar si está en modo producción"""
        return self.system.environment == 'production'
    
    def is_development(self) -> bool:
        """Verificar si está en modo desarrollo"""
        return self.system.environment == 'development'
    
    def get_plant_info(self) -> Dict[str, str]:
        """Obtener información de la planta"""
        return {
            'plant_id': self.johnson_controls.plant_id,
            'plant_name': self.johnson_controls.plant_name,
            'department': self.johnson_controls.department
        }
    
    def validate_config(self) -> bool:
        """Validar configuración actual"""
        try:
            # Validar puerto serie
            if not self.hardware.serial_port:
                return False
            
            # Validar archivos requeridos
            required_files = [
                self.database.excel_tracking_file,
                self.database.excel_data_file
            ]
            
            for file in required_files:
                if not file:
                    return False
            
            # Validar configuración web
            if self.web.port < 1 or self.web.port > 65535:
                return False
            
            return True
            
        except Exception:
            return False


# Instancia global de configuración
config = ConfigManager()

# Funciones de conveniencia
def get_hardware_config() -> HardwareConfig:
    """Obtener configuración de hardware"""
    return config.hardware

def get_database_config() -> DatabaseConfig:
    """Obtener configuración de base de datos"""
    return config.database

def get_web_config() -> WebConfig:
    """Obtener configuración web"""
    return config.web

def get_jci_config() -> JohnsonControlsConfig:
    """Obtener configuración de Johnson Controls"""
    return config.johnson_controls

def get_system_config() -> SystemConfig:
    """Obtener configuración del sistema"""
    return config.system