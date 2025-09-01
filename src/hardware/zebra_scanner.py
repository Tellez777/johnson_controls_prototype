#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZEBRA SCANNER INTERFACE - Interfaz específica para Zebra DS3678
Johnson Controls - Sistema de Seguimiento Industrial
"""

import serial
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from enum import Enum

from ..utils.logger import get_logger
from .serial_interface import SerialInterface


class ScannerStatus(Enum):
    """Estados del escáner"""
    DISCONNECTED = "Desconectado"
    CONNECTING = "Conectando"
    CONNECTED = "Conectado"
    SCANNING = "Escaneando"
    ERROR = "Error"


class ZebraScanner:
    """Interfaz específica para escáner Zebra DS3678"""
    
    def __init__(self, port: str = 'COM5', baud_rate: int = 9600, timeout: float = 0.1):
        self.logger = get_logger(__name__)
        
        # Configuración de hardware
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        
        # Interface serie
        self.serial_interface = SerialInterface(port, baud_rate, timeout)
        
        # Estado del escáner
        self.status = ScannerStatus.DISCONNECTED
        self.is_running = False
        self.last_scan_time = None
        self.scan_count = 0
        self.error_count = 0
        
        # Configuración Zebra DS3678
        self.zebra_config = {
            'model': 'DS3678-SR',
            'firmware_version': 'Unknown',
            'serial_number': 'Unknown',
            'scan_modes': ['1D', '2D', 'QR', 'DataMatrix'],
            'current_mode': '1D',
            'beep_enabled': True,
            'led_enabled': True
        }
        
        # Callbacks para eventos
        self.scan_callback: Optional[Callable[[str], None]] = None
        self.status_callback: Optional[Callable[[ScannerStatus], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
        # Buffer de datos
        self.data_buffer = b''
        self.max_buffer_size = 1024
        
        # Estadísticas
        self.stats = {
            'connection_time': None,
            'total_scans': 0,
            'successful_scans': 0,
            'failed_scans': 0,
            'average_scan_time': 0.0,
            'last_error': None,
            'uptime_seconds': 0
        }
        
        self.logger.info(f"Zebra Scanner DS3678 inicializado para puerto {port}")
    
    def connect(self) -> bool:
        """Conectar al escáner Zebra"""
        try:
            self.logger.info(f"Conectando a Zebra DS3678 en {self.port}...")
            self._update_status(ScannerStatus.CONNECTING)
            
            # Conectar interface serie
            if not self.serial_interface.connect():
                self.logger.error("Error conectando interface serie")
                self._update_status(ScannerStatus.ERROR)
                return False
            
            # Verificar comunicación con el escáner
            if not self._verify_scanner_communication():
                self.logger.warning("No se pudo verificar comunicación con Zebra DS3678")
                # Continuar en modo compatible por si el escáner no responde a comandos
            
            # Configurar escáner
            self._configure_scanner()
            
            # Actualizar estado
            self._update_status(ScannerStatus.CONNECTED)
            self.stats['connection_time'] = datetime.now()
            
            self.logger.info("Zebra DS3678 conectado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error conectando Zebra DS3678: {e}")
            self._update_status(ScannerStatus.ERROR)
            self.stats['last_error'] = str(e)
            return False
    
    def disconnect(self):
        """Desconectar del escáner"""
        try:
            self.logger.info("Desconectando Zebra DS3678...")
            
            self.is_running = False
            
            # Desconectar interface serie
            self.serial_interface.disconnect()
            
            self._update_status(ScannerStatus.DISCONNECTED)
            self.logger.info("Zebra DS3678 desconectado")
            
        except Exception as e:
            self.logger.error(f"Error desconectando Zebra DS3678: {e}")
    
    def _verify_scanner_communication(self) -> bool:
        """Verificar comunicación con el escáner"""
        try:
            # Enviar comando de identificación Zebra
            identification_commands = [
                b'<K100,1>\r\n',    # Comando para información del dispositivo
                b'<K200,1>\r\n',    # Comando alternativo
                b'?\r\n'            # Comando genérico
            ]
            
            for cmd in identification_commands:
                self.serial_interface.write(cmd)
                time.sleep(0.1)
                
                response = self.serial_interface.read()
                if response:
                    self.logger.info(f"Respuesta del escáner: {response}")
                    self._parse_device_info(response)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando comunicación: {e}")
            return False
    
    def _parse_device_info(self, response: bytes):
        """Parsear información del dispositivo"""
        try:
            response_str = response.decode('ascii', errors='ignore')
            
            # Buscar información conocida de Zebra
            if 'DS3678' in response_str:
                self.zebra_config['model'] = 'DS3678-SR'
            
            # Parsear otros datos si están disponibles
            lines = response_str.split('\n')
            for line in lines:
                line = line.strip()
                if 'FW:' in line or 'Firmware:' in line:
                    self.zebra_config['firmware_version'] = line
                elif 'SN:' in line or 'Serial:' in line:
                    self.zebra_config['serial_number'] = line
            
            self.logger.info(f"Información del escáner: {self.zebra_config['model']}")
            
        except Exception as e:
            self.logger.error(f"Error parseando información del dispositivo: {e}")
    
    def _configure_scanner(self):
        """Configurar escáner Zebra DS3678"""
        try:
            # Comandos de configuración Zebra DS3678
            config_commands = [
                # Habilitar sonido de confirmación
                b'<K204,1>\r\n' if self.zebra_config['beep_enabled'] else b'<K204,0>\r\n',
                
                # Configurar LED
                b'<K205,1>\r\n' if self.zebra_config['led_enabled'] else b'<K205,0>\r\n',
                
                # Configurar modo de escaneo
                b'<K100,0>\r\n',  # Modo trigger
                
                # Configurar sufijo de datos
                b'<K233,13,10>\r\n',  # CR+LF como sufijo
                
                # Habilitar códigos 1D y 2D
                b'<K470,1>\r\n',  # Código 128
                b'<K480,1>\r\n',  # Código 39
                b'<K491,1>\r\n',  # DataMatrix
                b'<K492,1>\r\n',  # QR Code
            ]
            
            for cmd in config_commands:
                self.serial_interface.write(cmd)
                time.sleep(0.05)  # Pequeña pausa entre comandos
            
            # Guardar configuración en escáner
            self.serial_interface.write(b'<K544,1>\r\n')
            
            self.logger.info("Configuración de Zebra DS3678 aplicada")
            
        except Exception as e:
            self.logger.error(f"Error configurando escáner: {e}")
    
    def read_barcode(self) -> Optional[str]:
        """Leer código de barras del escáner"""
        try:
            # Leer datos del puerto serie
            data = self.serial_interface.read()
            
            if not data:
                return None
            
            # Agregar al buffer
            self.data_buffer += data
            
            # Verificar si tenemos un código completo
            barcode = self._extract_barcode_from_buffer()
            
            if barcode:
                self.last_scan_time = datetime.now()
                self.scan_count += 1
                self.stats['total_scans'] += 1
                self.stats['successful_scans'] += 1
                
                self.logger.debug(f"Código leído: {barcode}")
                
                # Ejecutar callback si está configurado
                if self.scan_callback:
                    self.scan_callback(barcode)
                
                return barcode
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error leyendo código de barras: {e}")
            self.error_count += 1
            self.stats['failed_scans'] += 1
            
            if self.error_callback:
                self.error_callback(str(e))
            
            return None
    
    def _extract_barcode_from_buffer(self) -> Optional[str]:
        """Extraer código de barras del buffer de datos"""
        try:
            # Buscar terminadores comunes
            terminators = [b'\r\n', b'\n', b'\r']
            
            for terminator in terminators:
                if terminator in self.data_buffer:
                    # Extraer línea completa
                    line, self.data_buffer = self.data_buffer.split(terminator, 1)
                    
                    # Limpiar y validar
                    barcode = line.decode('ascii', errors='ignore').strip()
                    
                    if self._is_valid_barcode(barcode):
                        return barcode
            
            # Limpiar buffer si es muy grande
            if len(self.data_buffer) > self.max_buffer_size:
                self.data_buffer = self.data_buffer[-100:]  # Mantener últimos 100 bytes
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extrayendo código del buffer: {e}")
            return None
    
    def _is_valid_barcode(self, barcode: str) -> bool:
        """Validar si el código de barras es válido"""
        if not barcode:
            return False
        
        # Verificar longitud mínima
        if len(barcode) < 3:
            return False
        
        # Verificar caracteres válidos (alfanuméricos y algunos símbolos)
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
        if not all(c.upper() in valid_chars for c in barcode):
            return False
        
        # Verificar patrones conocidos de Johnson Controls
        jci_patterns = ['JCI', 'HVAC', 'BATT', 'INT', 'SWT']
        if any(pattern in barcode.upper() for pattern in jci_patterns):
            return True
        
        # Verificar otros patrones comunes
        if len(barcode) >= 8 and barcode.isalnum():
            return True
        
        return len(barcode) >= 5  # Longitud mínima para códigos genéricos
    
    def trigger_scan(self) -> bool:
        """Activar escaneo manualmente (si el escáner lo soporta)"""
        try:
            # Comando para activar trigger en Zebra DS3678
            trigger_command = b'<K142,1>\r\n'
            self.serial_interface.write(trigger_command)
            
            self._update_status(ScannerStatus.SCANNING)
            
            # Volver a estado conectado después de un tiempo
            threading.Timer(2.0, lambda: self._update_status(ScannerStatus.CONNECTED)).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error activando trigger: {e}")
            return False
    
    def set_scan_callback(self, callback: Callable[[str], None]):
        """Configurar callback para cuando se lee un código"""
        self.scan_callback = callback
    
    def set_status_callback(self, callback: Callable[[ScannerStatus], None]):
        """Configurar callback para cambios de estado"""
        self.status_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Configurar callback para errores"""
        self.error_callback = callback
    
    def _update_status(self, new_status: ScannerStatus):
        """Actualizar estado del escáner"""
        if self.status != new_status:
            old_status = self.status
            self.status = new_status
            
            self.logger.debug(f"Estado del escáner: {old_status.value} -> {new_status.value}")
            
            if self.status_callback:
                self.status_callback(new_status)
    
    def is_connected(self) -> bool:
        """Verificar si el escáner está conectado"""
        return self.status in [ScannerStatus.CONNECTED, ScannerStatus.SCANNING]
    
    def get_status(self) -> ScannerStatus:
        """Obtener estado actual del escáner"""
        return self.status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del escáner"""
        current_time = datetime.now()
        
        if self.stats['connection_time']:
            self.stats['uptime_seconds'] = (current_time - self.stats['connection_time']).total_seconds()
        
        return {
            **self.stats,
            'current_status': self.status.value,
            'scan_count': self.scan_count,
            'error_count': self.error_count,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'success_rate': (self.stats['successful_scans'] / max(1, self.stats['total_scans'])) * 100
        }
    
    def get_device_info(self) -> Dict[str, str]:
        """Obtener información del dispositivo"""
        return self.zebra_config.copy()
    
    def reset_statistics(self):
        """Resetear estadísticas"""
        self.scan_count = 0
        self.error_count = 0
        self.stats.update({
            'total_scans': 0,
            'successful_scans': 0,
            'failed_scans': 0,
            'last_error': None
        })
        
        self.logger.info("Estadísticas del escáner reseteadas")
    
    def test_connection(self) -> bool:
        """Probar la conexión del escáner"""
        try:
            if not self.is_connected():
                return False
            
            # Enviar comando de prueba
            test_command = b'<K100,1>\r\n'
            self.serial_interface.write(test_command)
            
            # Esperar respuesta
            time.sleep(0.2)
            response = self.serial_interface.read()
            
            return response is not None and len(response) > 0
            
        except Exception as e:
            self.logger.error(f"Error probando conexión: {e}")
            return False
    
    def configure_beep(self, enabled: bool):
        """Configurar sonido de confirmación"""
        try:
            self.zebra_config['beep_enabled'] = enabled
            cmd = b'<K204,1>\r\n' if enabled else b'<K204,0>\r\n'
            self.serial_interface.write(cmd)
            
            self.logger.info(f"Sonido de confirmación {'habilitado' if enabled else 'deshabilitado'}")
            
        except Exception as e:
            self.logger.error(f"Error configurando sonido: {e}")
    
    def configure_led(self, enabled: bool):
        """Configurar indicador LED"""
        try:
            self.zebra_config['led_enabled'] = enabled
            cmd = b'<K205,1>\r\n' if enabled else b'<K205,0>\r\n'
            self.serial_interface.write(cmd)
            
            self.logger.info(f"Indicador LED {'habilitado' if enabled else 'deshabilitado'}")
            
        except Exception as e:
            self.logger.error(f"Error configurando LED: {e}")
    
    def __str__(self) -> str:
        """Representación en string del escáner"""
        return f"ZebraScanner(DS3678, {self.port}, {self.status.value})"
    
    def __repr__(self) -> str:
        """Representación detallada del escáner"""
        return (f"ZebraScanner(port='{self.port}', baud_rate={self.baud_rate}, "
                f"status={self.status.value}, scans={self.scan_count})")


# Clase para compatibilidad con código legacy
class ZebraScannerLegacy(ZebraScanner):
    """Versión de compatibilidad con el código anterior"""
    
    def __init__(self, port: str = 'COM5', baud_rate: int = 9600):
        super().__init__(port, baud_rate)
        self.puerto_serial = None
    
    def conectar(self) -> bool:
        """Método legacy para conectar"""
        return self.connect()
    
    def desconectar(self):
        """Método legacy para desconectar"""
        self.disconnect()
    
    def leer_codigo(self) -> Optional[str]:
        """Método legacy para leer código"""
        return self.read_barcode()