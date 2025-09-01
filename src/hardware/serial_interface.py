#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERIAL INTERFACE - Interfaz serie genérica para dispositivos
Johnson Controls - Sistema de Seguimiento Industrial
"""

import serial
import threading
import time
from datetime import datetime
from typing import Optional, Callable, List
from enum import Enum

from ..utils.logger import get_logger


class SerialStatus(Enum):
    """Estados de la conexión serie"""
    DISCONNECTED = "Desconectado"
    CONNECTING = "Conectando"
    CONNECTED = "Conectado"
    ERROR = "Error"


class SerialInterface:
    """Interfaz serie genérica para comunicación con dispositivos"""
    
    def __init__(self, 
                 port: str = 'COM1', 
                 baud_rate: int = 9600,
                 timeout: float = 1.0,
                 bytesize: int = serial.EIGHTBITS,
                 parity: str = serial.PARITY_NONE,
                 stopbits: float = serial.STOPBITS_ONE):
        
        self.logger = get_logger(__name__)
        
        # Configuración del puerto serie
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        
        # Objeto serial
        self.serial_connection: Optional[serial.Serial] = None
        
        # Estado de la conexión
        self.status = SerialStatus.DISCONNECTED
        self.is_connected = False
        
        # Control de hilos
        self.read_thread: Optional[threading.Thread] = None
        self.is_reading = False
        self.read_lock = threading.RLock()
        self.write_lock = threading.RLock()
        
        # Buffers
        self.read_buffer = bytearray()
        self.max_buffer_size = 4096
        
        # Callbacks
        self.data_received_callback: Optional[Callable[[bytes], None]] = None
        self.connection_status_callback: Optional[Callable[[SerialStatus], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
        # Estadísticas
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'connection_attempts': 0,
            'last_error': None,
            'connection_time': None,
            'uptime_seconds': 0
        }
        
        self.logger.info(f"Serial Interface inicializada para puerto {port} @ {baud_rate} baud")
    
    def connect(self) -> bool:
        """Conectar al puerto serie"""
        try:
            self.logger.info(f"Conectando a puerto serie {self.port}...")
            self._update_status(SerialStatus.CONNECTING)
            self.stats['connection_attempts'] += 1
            
            # Cerrar conexión existente si hay una
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            # Crear nueva conexión
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits
            )
            
            # Verificar que la conexión esté abierta
            if not self.serial_connection.is_open:
                self.serial_connection.open()
            
            # Limpiar buffers
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            self.read_buffer.clear()
            
            # Actualizar estado
            self.is_connected = True
            self._update_status(SerialStatus.CONNECTED)
            self.stats['connection_time'] = datetime.now()
            
            self.logger.info(f"Conectado exitosamente a {self.port}")
            return True
            
        except serial.SerialException as e:
            error_msg = f"Error de puerto serie: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error inesperado conectando: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return False
    
    def disconnect(self):
        """Desconectar del puerto serie"""
        try:
            self.logger.info(f"Desconectando de puerto serie {self.port}...")
            
            # Detener lectura
            self.stop_reading()
            
            # Cerrar conexión
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            # Actualizar estado
            self.is_connected = False
            self._update_status(SerialStatus.DISCONNECTED)
            
            self.logger.info("Desconectado exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error desconectando: {e}")
    
    def write(self, data: bytes) -> bool:
        """Escribir datos al puerto serie"""
        try:
            if not self.is_connected or not self.serial_connection:
                self.logger.warning("Intento de escritura en puerto desconectado")
                return False
            
            with self.write_lock:
                bytes_written = self.serial_connection.write(data)
                self.serial_connection.flush()  # Asegurar que se envíen inmediatamente
                
                # Actualizar estadísticas
                self.stats['bytes_sent'] += bytes_written
                self.stats['messages_sent'] += 1
                
                self.logger.debug(f"Enviados {bytes_written} bytes: {data}")
                return bytes_written > 0
                
        except serial.SerialException as e:
            error_msg = f"Error escribiendo al puerto serie: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error inesperado escribiendo: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return False
    
    def read(self, size: int = None) -> Optional[bytes]:
        """Leer datos del puerto serie"""
        try:
            if not self.is_connected or not self.serial_connection:
                return None
            
            with self.read_lock:
                if size is None:
                    # Leer todos los datos disponibles
                    data = self.serial_connection.read_all()
                else:
                    # Leer cantidad específica
                    data = self.serial_connection.read(size)
                
                if data:
                    self.stats['bytes_received'] += len(data)
                    self.stats['messages_received'] += 1
                    self.logger.debug(f"Recibidos {len(data)} bytes: {data}")
                
                return data if data else None
                
        except serial.SerialException as e:
            error_msg = f"Error leyendo del puerto serie: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error inesperado leyendo: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return None
    
    def readline(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Leer una línea completa del puerto serie"""
        try:
            if not self.is_connected or not self.serial_connection:
                return None
            
            # Usar timeout específico si se proporciona
            original_timeout = self.serial_connection.timeout
            if timeout is not None:
                self.serial_connection.timeout = timeout
            
            try:
                with self.read_lock:
                    line = self.serial_connection.readline()
                    
                    if line:
                        self.stats['bytes_received'] += len(line)
                        self.stats['messages_received'] += 1
                        self.logger.debug(f"Línea recibida: {line}")
                    
                    return line if line else None
            finally:
                # Restaurar timeout original
                if timeout is not None:
                    self.serial_connection.timeout = original_timeout
                
        except serial.SerialException as e:
            error_msg = f"Error leyendo línea del puerto serie: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error inesperado leyendo línea: {e}"
            self.logger.error(error_msg)
            self._handle_error(error_msg)
            return None
    
    def start_reading(self):
        """Iniciar lectura continua en hilo separado"""
        if self.is_reading:
            self.logger.warning("Lectura ya está iniciada")
            return
        
        if not self.is_connected:
            self.logger.warning("No se puede iniciar lectura, puerto desconectado")
            return
        
        self.is_reading = True
        self.read_thread = threading.Thread(target=self._reading_loop, daemon=True)
        self.read_thread.start()
        
        self.logger.info("Lectura continua iniciada")
    
    def stop_reading(self):
        """Detener lectura continua"""
        if not self.is_reading:
            return
        
        self.is_reading = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        
        self.logger.info("Lectura continua detenida")
    
    def _reading_loop(self):
        """Bucle de lectura continua"""
        self.logger.info("Iniciando bucle de lectura continua")
        
        while self.is_reading and self.is_connected:
            try:
                data = self.read()
                
                if data:
                    # Agregar al buffer
                    self.read_buffer.extend(data)
                    
                    # Limpiar buffer si es muy grande
                    if len(self.read_buffer) > self.max_buffer_size:
                        self.read_buffer = self.read_buffer[-1024:]  # Mantener últimos 1KB
                    
                    # Ejecutar callback si está configurado
                    if self.data_received_callback:
                        self.data_received_callback(data)
                
                time.sleep(0.01)  # Pequeña pausa para no saturar CPU
                
            except Exception as e:
                if self.is_reading:  # Solo log si no se está deteniendo
                    self.logger.error(f"Error en bucle de lectura: {e}")
                    time.sleep(1)  # Pausa más larga en caso de error
        
        self.logger.info("Bucle de lectura terminado")
    
    def get_buffered_data(self) -> bytes:
        """Obtener datos del buffer de lectura"""
        with self.read_lock:
            data = bytes(self.read_buffer)
            self.read_buffer.clear()
            return data
    
    def flush_buffers(self):
        """Limpiar todos los buffers"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.reset_input_buffer()
                self.serial_connection.reset_output_buffer()
            
            with self.read_lock:
                self.read_buffer.clear()
            
            self.logger.info("Buffers limpiados")
            
        except Exception as e:
            self.logger.error(f"Error limpiando buffers: {e}")
    
    def set_data_callback(self, callback: Callable[[bytes], None]):
        """Configurar callback para datos recibidos"""
        self.data_received_callback = callback
        self.logger.debug("Callback de datos configurado")
    
    def set_status_callback(self, callback: Callable[[SerialStatus], None]):
        """Configurar callback para cambios de estado"""
        self.connection_status_callback = callback
        self.logger.debug("Callback de estado configurado")
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Configurar callback para errores"""
        self.error_callback = callback
        self.logger.debug("Callback de error configurado")
    
    def _update_status(self, new_status: SerialStatus):
        """Actualizar estado de la conexión"""
        if self.status != new_status:
            old_status = self.status
            self.status = new_status
            
            self.logger.debug(f"Estado serie: {old_status.value} -> {new_status.value}")
            
            if self.connection_status_callback:
                self.connection_status_callback(new_status)
    
    def _handle_error(self, error_message: str):
        """Manejar errores de la conexión"""
        self.stats['last_error'] = error_message
        self.is_connected = False
        self._update_status(SerialStatus.ERROR)
        
        if self.error_callback:
            self.error_callback(error_message)
    
    def test_connection(self) -> bool:
        """Probar la conexión serie"""
        try:
            if not self.is_connected or not self.serial_connection:
                return False
            
            # Intentar operación simple
            original_timeout = self.serial_connection.timeout
            self.serial_connection.timeout = 0.1
            
            try:
                # Leer cualquier dato disponible
                self.serial_connection.read_all()
                return True
            finally:
                self.serial_connection.timeout = original_timeout
                
        except Exception as e:
            self.logger.error(f"Prueba de conexión falló: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Obtener información de la conexión"""
        info = {
            'port': self.port,
            'baud_rate': self.baud_rate,
            'timeout': self.timeout,
            'bytesize': self.bytesize,
            'parity': self.parity,
            'stopbits': self.stopbits,
            'status': self.status.value,
            'is_connected': self.is_connected,
            'is_reading': self.is_reading
        }
        
        if self.serial_connection:
            try:
                info.update({
                    'port_open': self.serial_connection.is_open,
                    'in_waiting': self.serial_connection.in_waiting,
                    'out_waiting': self.serial_connection.out_waiting
                })
            except:
                pass
        
        return info
    
    def get_statistics(self) -> dict:
        """Obtener estadísticas de la conexión"""
        current_time = datetime.now()
        
        stats = self.stats.copy()
        
        if stats['connection_time']:
            stats['uptime_seconds'] = (current_time - stats['connection_time']).total_seconds()
        
        # Calcular tasas
        if stats['uptime_seconds'] > 0:
            stats['bytes_per_second_sent'] = stats['bytes_sent'] / stats['uptime_seconds']
            stats['bytes_per_second_received'] = stats['bytes_received'] / stats['uptime_seconds']
            stats['messages_per_second'] = (stats['messages_sent'] + stats['messages_received']) / stats['uptime_seconds']
        else:
            stats['bytes_per_second_sent'] = 0
            stats['bytes_per_second_received'] = 0
            stats['messages_per_second'] = 0
        
        return stats
    
    def reset_statistics(self):
        """Resetear estadísticas"""
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'connection_attempts': self.stats['connection_attempts'],  # Mantener intentos
            'last_error': None,
            'connection_time': self.stats['connection_time'],  # Mantener tiempo de conexión
            'uptime_seconds': 0
        }
        
        self.logger.info("Estadísticas reseteadas")
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """Listar puertos serie disponibles"""
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            return sorted(ports)
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error listando puertos: {e}")
            return []
    
    def __str__(self) -> str:
        """Representación en string"""
        return f"SerialInterface({self.port} @ {self.baud_rate}, {self.status.value})"
    
    def __repr__(self) -> str:
        """Representación detallada"""
        return (f"SerialInterface(port='{self.port}', baud_rate={self.baud_rate}, "
                f"status='{self.status.value}', connected={self.is_connected})")
    
    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        else:
            raise Exception(f"No se pudo conectar a {self.port}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Funciones de utilidad
def scan_for_devices(baud_rates: List[int] = None, timeout: float = 0.5) -> List[dict]:
    """Escanear puertos serie en busca de dispositivos"""
    if baud_rates is None:
        baud_rates = [9600, 19200, 38400, 57600, 115200]
    
    logger = get_logger(__name__)
    available_ports = SerialInterface.list_available_ports()
    devices_found = []
    
    logger.info(f"Escaneando {len(available_ports)} puertos con {len(baud_rates)} velocidades...")
    
    for port in available_ports:
        for baud_rate in baud_rates:
            try:
                with SerialInterface(port, baud_rate, timeout) as interface:
                    if interface.test_connection():
                        device_info = {
                            'port': port,
                            'baud_rate': baud_rate,
                            'status': 'responsive',
                            'connection_info': interface.get_connection_info()
                        }
                        devices_found.append(device_info)
                        logger.info(f"Dispositivo encontrado: {port} @ {baud_rate}")
                        break  # No probar otras velocidades para este puerto
                        
            except Exception as e:
                logger.debug(f"No se pudo conectar a {port} @ {baud_rate}: {e}")
                continue
    
    logger.info(f"Escaneo completado. {len(devices_found)} dispositivos encontrados")
    return devices_found