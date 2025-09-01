#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOGGER UTILITY - Sistema de logging centralizado
Johnson Controls - Sistema de Seguimiento Industrial
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class JCIFormatter(logging.Formatter):
    """Formatter personalizado para Johnson Controls"""
    
    def __init__(self, include_colors: bool = True):
        self.include_colors = include_colors
        
        # Colores para consola
        self.colors = {
            'DEBUG': '\033[36m',     # Cian
            'INFO': '\033[32m',      # Verde
            'WARNING': '\033[33m',   # Amarillo
            'ERROR': '\033[31m',     # Rojo
            'CRITICAL': '\033[41m',  # Rojo con fondo
            'RESET': '\033[0m'       # Reset
        }
        
        # Formato base
        base_format = '[{asctime}] {name:<20} {levelname:<8} {message}'
        
        super().__init__(fmt=base_format, style='{', datefmt='%H:%M:%S')
    
    def format(self, record):
        """Formatear registro de log"""
        # Formateo básico
        formatted = super().format(record)
        
        # Agregar colores si está habilitado y es consola
        if self.include_colors and hasattr(record, 'stream_handler'):
            level_color = self.colors.get(record.levelname, '')
            reset_color = self.colors['RESET']
            formatted = f"{level_color}{formatted}{reset_color}"
        
        return formatted


class JCIJSONFormatter(logging.Formatter):
    """Formatter JSON para archivos de log estructurados"""
    
    def format(self, record):
        """Formatear registro como JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Agregar información extra si existe
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class JCILoggerAdapter(logging.LoggerAdapter):
    """Adapter para agregar contexto automáticamente"""
    
    def __init__(self, logger, extra):
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """Procesar mensaje agregando contexto"""
        # Agregar contexto extra
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


class LoggerManager:
    """Gestor centralizado de logging"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: Dict[str, logging.Handler] = {}
        self.configured = False
        
        # Configuración por defecto
        self.log_dir = Path("data/logs")
        self.log_level = logging.INFO
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        self.enable_console = True
        self.enable_file = True
        self.enable_json = True
        
        # Crear directorio de logs
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self, 
                     level: str = 'INFO',
                     log_dir: Optional[str] = None,
                     enable_console: bool = True,
                     enable_file: bool = True,
                     enable_json: bool = True):
        """Configurar sistema de logging"""
        
        if self.configured:
            return
        
        # Configurar nivel
        self.log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Configurar directorio
        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        
        # Configurar logging básico
        logging.basicConfig(level=self.log_level, handlers=[])
        
        # Crear handlers
        self._create_console_handler()
        self._create_file_handler()
        self._create_json_handler()
        
        # Configurar root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        self.configured = True
        
        # Log de inicialización
        logger = self.get_logger(__name__)
        logger.info("Sistema de logging Johnson Controls inicializado")
        logger.info(f"Nivel: {level}, Directorio: {self.log_dir}")
    
    def _create_console_handler(self):
        """Crear handler para consola"""
        if not self.enable_console:
            return
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        
        # Formatter con colores para consola
        formatter = JCIFormatter(include_colors=True)
        console_handler.setFormatter(formatter)
        
        # Marcar para identificar en formatter
        console_handler.stream_handler = True
        
        self.handlers['console'] = console_handler
    
    def _create_file_handler(self):
        """Crear handler para archivo de log"""
        if not self.enable_file:
            return
        
        log_file = self.log_dir / "jci_system.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        
        # Formatter sin colores para archivo
        formatter = JCIFormatter(include_colors=False)
        file_handler.setFormatter(formatter)
        
        self.handlers['file'] = file_handler
    
    def _create_json_handler(self):
        """Crear handler para logs en formato JSON"""
        if not self.enable_json:
            return
        
        json_log_file = self.log_dir / "jci_system.jsonl"
        
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)  # Solo INFO y superiores en JSON
        
        # Formatter JSON
        json_formatter = JCIJSONFormatter()
        json_handler.setFormatter(json_formatter)
        
        self.handlers['json'] = json_handler
    
    def get_logger(self, name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """Obtener logger configurado"""
        
        # Asegurarse de que el sistema esté configurado
        if not self.configured:
            self.setup_logging()
        
        # Usar logger existente si ya existe
        if name in self.loggers:
            return self.loggers[name]
        
        # Crear nuevo logger
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Limpiar handlers existentes
        logger.handlers.clear()
        logger.propagate = False
        
        # Agregar handlers configurados
        for handler in self.handlers.values():
            logger.addHandler(handler)
        
        # Crear adapter con contexto extra si se proporciona
        if extra_context:
            logger = JCILoggerAdapter(logger, extra_context)
        
        self.loggers[name] = logger
        return logger
    
    def create_module_logger(self, module_name: str, component: str = None) -> logging.Logger:
        """Crear logger específico para un módulo"""
        context = {
            'module': module_name,
            'component': component or 'core'
        }
        
        logger_name = f"jci.{component}.{module_name}" if component else f"jci.{module_name}"
        return self.get_logger(logger_name, context)
    
    def create_scanner_logger(self) -> logging.Logger:
        """Crear logger específico para scanner"""
        return self.create_module_logger('scanner', 'hardware')
    
    def create_web_logger(self) -> logging.Logger:
        """Crear logger específico para web"""
        return self.create_module_logger('web', 'interface')
    
    def create_analytics_logger(self) -> logging.Logger:
        """Crear logger específico para analytics"""
        return self.create_module_logger('analytics', 'services')
    
    def set_level(self, level: str):
        """Cambiar nivel de logging dinámicamente"""
        new_level = getattr(logging, level.upper(), logging.INFO)
        self.log_level = new_level
        
        # Actualizar todos los loggers y handlers
        for logger in self.loggers.values():
            if isinstance(logger, JCILoggerAdapter):
                logger.logger.setLevel(new_level)
            else:
                logger.setLevel(new_level)
        
        for handler in self.handlers.values():
            handler.setLevel(new_level)
        
        # Log del cambio
        logger = self.get_logger(__name__)
        logger.info(f"Nivel de logging cambiado a: {level}")
    
    def get_log_files(self) -> Dict[str, Path]:
        """Obtener rutas de archivos de log"""
        return {
            'main': self.log_dir / "jci_system.log",
            'json': self.log_dir / "jci_system.jsonl",
            'error': self.log_dir / "jci_errors.log"
        }
    
    def rotate_logs(self):
        """Rotar logs manualmente"""
        for handler_name, handler in self.handlers.items():
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.doRollover()
        
        logger = self.get_logger(__name__)
        logger.info("Logs rotados manualmente")
    
    def get_recent_logs(self, lines: int = 100) -> str:
        """Obtener logs recientes"""
        try:
            log_file = self.log_dir / "jci_system.log"
            
            if not log_file.exists():
                return "No hay archivo de log disponible"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return ''.join(recent_lines)
        
        except Exception as e:
            return f"Error leyendo logs: {e}"
    
    def cleanup_old_logs(self, days: int = 30):
        """Limpiar logs antiguos"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
            
            logger = self.get_logger(__name__)
            logger.info(f"Logs antiguos limpiados (>{days} días)")
        
        except Exception as e:
            logger = self.get_logger(__name__)
            logger.error(f"Error limpiando logs antiguos: {e}")


# Instancia global del gestor de logging
logger_manager = LoggerManager()

# Funciones de conveniencia
def setup_logging(level: str = 'INFO',
                 log_dir: Optional[str] = None,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_json: bool = True):
    """Configurar sistema de logging (función global)"""
    logger_manager.setup_logging(level, log_dir, enable_console, enable_file, enable_json)

def get_logger(name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Obtener logger configurado (función global)"""
    return logger_manager.get_logger(name, extra_context)

def get_scanner_logger() -> logging.Logger:
    """Obtener logger para scanner"""
    return logger_manager.create_scanner_logger()

def get_web_logger() -> logging.Logger:
    """Obtener logger para web"""
    return logger_manager.create_web_logger()

def get_analytics_logger() -> logging.Logger:
    """Obtener logger para analytics"""
    return logger_manager.create_analytics_logger()

def set_log_level(level: str):
    """Cambiar nivel de logging"""
    logger_manager.set_level(level)

def get_recent_logs(lines: int = 100) -> str:
    """Obtener logs recientes"""
    return logger_manager.get_recent_logs(lines)


# Context manager para logging con contexto temporal
class LogContext:
    """Context manager para agregar contexto temporal a logs"""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        self.logger = logger
        self.context = context
        self.original_adapter = None
    
    def __enter__(self):
        if isinstance(self.logger, JCILoggerAdapter):
            # Crear nuevo adapter con contexto adicional
            combined_context = {**self.logger.extra, **self.context}
            self.original_adapter = self.logger
            return JCILoggerAdapter(self.logger.logger, combined_context)
        else:
            # Crear adapter con contexto
            return JCILoggerAdapter(self.logger, self.context)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restaurar adapter original si existía
        if self.original_adapter:
            return self.original_adapter


# Decorador para logging automático de funciones
def log_function_calls(logger: Optional[logging.Logger] = None):
    """Decorador para loggear llamadas a funciones automáticamente"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Iniciando {func_name}")
            
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                logger.debug(f"Completado {func_name} en {duration:.3f}s")
                return result
            
            except Exception as e:
                logger.error(f"Error en {func_name}: {e}")
                raise
        
        return wrapper
    return decorator