#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCANNER MANAGER - Gestor principal del sistema de escaneo
Johnson Controls - Sistema de Seguimiento Industrial
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

from ..utils.config import config, get_system_config
from ..utils.logger import get_logger
from ..models.product import JCIProduct, ProductStatus, QualityMetrics
from ..hardware.zebra_scanner import ZebraScanner
from ..services.data_sync_service import DataSyncService
from ..services.analytics_service import AnalyticsService
from ..services.notification_service import NotificationService


@dataclass
class ScanEvent:
    """Evento de escaneo"""
    timestamp: datetime
    barcode: str
    stage_id: int
    operator_id: str
    station_id: str
    success: bool
    error_message: str = ""


class ScannerManager:
    """Gestor principal del sistema de escaneo"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        
        # Servicios
        self.scanner = None
        self.data_sync = DataSyncService()
        self.analytics = AnalyticsService()
        self.notifications = NotificationService()
        
        # Estado del sistema
        self.current_stage = 1
        self.is_running = False
        self.scan_count = 0
        self.error_count = 0
        
        # Productos en memoria
        self.products: Dict[str, JCIProduct] = {}
        
        # Hilos de procesamiento
        self.scanner_thread = None
        self.command_thread = None
        self.connection_monitor_thread = None
        
        # Estado de conexión del escáner
        self.scanner_connected = False
        self.last_connection_check = None
        self.connection_check_interval = 3  # segundos
        
        # Callbacks para eventos
        self.scan_callbacks: Dict[str, Callable] = {}
        
        # Estadísticas de sesión
        self.session_stats = {
            'start_time': None,
            'scans_processed': 0,
            'errors_count': 0,
            'products_completed': 0,
            'average_cycle_time': 0.0
        }
        
        self.logger.info("Scanner Manager inicializado")
    
    def initialize(self) -> bool:
        """Inicializar el sistema completo"""
        try:
            self.logger.info("Iniciando sistema de escaneo Johnson Controls...")
            
            # Cargar productos existentes
            self._load_existing_products()
            
            # Inicializar hardware
            if not self._initialize_hardware():
                self.logger.warning("Hardware no disponible - Modo simulación activado")
            
            # Inicializar servicios
            self.data_sync.initialize()
            self.analytics.initialize()
            self.notifications.initialize()
            
            # Iniciar hilos de procesamiento
            self._start_processing_threads()
            
            # Registrar callbacks por defecto
            self._register_default_callbacks()
            
            self.session_stats['start_time'] = datetime.now()
            self.logger.info("Sistema de escaneo inicializado correctamente")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando sistema: {e}")
            return False
    
    def _initialize_hardware(self) -> bool:
        """Inicializar hardware del escáner"""
        try:
            hardware_config = self.config.hardware
            self.scanner = ZebraScanner(
                port=hardware_config.serial_port,
                baud_rate=hardware_config.baud_rate,
                timeout=hardware_config.timeout
            )
            
            if self.scanner.connect():
                self.scanner_connected = True  # Establecer estado inicial
                self.logger.info(f"Escáner Zebra conectado en {hardware_config.serial_port}")
                return True
            else:
                self.scanner_connected = False  # Establecer estado inicial
                self.logger.warning("No se pudo conectar al escáner")
                return False
                
        except Exception as e:
            self.logger.error(f"Error inicializando hardware: {e}")
            return False
    
    def _load_existing_products(self):
        """Cargar productos existentes desde almacenamiento"""
        try:
            stored_products = self.data_sync.load_products()
            
            for product_data in stored_products:
                product = JCIProduct.from_dict(product_data)
                self.products[product.barcode] = product
            
            self.logger.info(f"Cargados {len(self.products)} productos existentes")
            
        except Exception as e:
            self.logger.error(f"Error cargando productos: {e}")
            # Crear productos de muestra si no hay datos
            self._create_sample_products()
    
    def _create_sample_products(self):
        """Crear productos de muestra para Johnson Controls"""
        from ..models.product import JCI_SAMPLE_PRODUCTS
        
        for sample_data in JCI_SAMPLE_PRODUCTS:
            product = JCIProduct(**sample_data)
            self.products[product.barcode] = product
        
        self.logger.info(f"Creados {len(JCI_SAMPLE_PRODUCTS)} productos de muestra")
    
    def _start_processing_threads(self):
        """Iniciar hilos de procesamiento"""
        self.is_running = True
        
        # Hilo para lectura del escáner
        if self.scanner:
            self.scanner_thread = threading.Thread(
                target=self._scanner_reading_loop,
                daemon=True
            )
            self.scanner_thread.start()
            self.logger.info("Hilo de lectura del escáner iniciado")
        
        # Hilo para procesamiento de comandos web
        self.command_thread = threading.Thread(
            target=self._command_processing_loop,
            daemon=True
        )
        self.command_thread.start()
        self.logger.info("Hilo de procesamiento de comandos iniciado")
        
        # Hilo para monitoreo de conexión del escáner
        self.connection_monitor_thread = threading.Thread(
            target=self._connection_monitoring_loop,
            daemon=True
        )
        self.connection_monitor_thread.start()
        self.logger.info("Hilo de monitoreo de conexión iniciado")
    
    def _scanner_reading_loop(self):
        """Bucle de lectura del escáner en hilo separado"""
        self.logger.info("Iniciando bucle de lectura del escáner")
        
        while self.is_running and self.scanner:
            try:
                barcode = self.scanner.read_barcode()
                
                if barcode:
                    self.logger.info(f"Código escaneado: {barcode}")
                    scan_event = ScanEvent(
                        timestamp=datetime.now(),
                        barcode=barcode,
                        stage_id=self.current_stage,
                        operator_id=self._get_current_operator(),
                        station_id=self._get_current_station(),
                        success=True
                    )
                    
                    # Procesar escaneo
                    self._process_scan_event(scan_event)
                
                time.sleep(0.05)  # Pequeña pausa para no saturar CPU
                
            except Exception as e:
                if self.is_running:  # Solo log si no se está cerrando
                    self.logger.error(f"Error en lectura del escáner: {e}")
                    self.error_count += 1
                    time.sleep(1)  # Pausa más larga en caso de error
        
        self.logger.info("Bucle de lectura del escáner terminado")
    
    def _command_processing_loop(self):
        """Bucle de procesamiento de comandos web"""
        self.logger.info("Iniciando bucle de procesamiento de comandos")
        
        while self.is_running:
            try:
                # Leer comandos desde archivo JSON
                commands = self.data_sync.get_pending_commands()
                
                for command in commands:
                    self._process_web_command(command)
                
                time.sleep(0.5)  # Verificar comandos cada 0.5 segundos
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Error procesando comandos: {e}")
                    time.sleep(1)
        
        self.logger.info("Bucle de procesamiento de comandos terminado")
    
    def _connection_monitoring_loop(self):
        """Bucle de monitoreo de conexión del escáner"""
        self.logger.info("Iniciando bucle de monitoreo de conexión")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Verificar conexión cada cierto intervalo
                if (self.last_connection_check is None or 
                    (current_time - self.last_connection_check).total_seconds() >= self.connection_check_interval):
                    
                    self.logger.debug(f"Verificando estado del escáner... (intervalo: {self.connection_check_interval}s)")
                    
                    # Verificar estado actual del escáner
                    was_connected = self.scanner_connected
                    is_connected = self._check_scanner_connection()
                    
                    self.logger.debug(f"Estado anterior: {was_connected}, Estado actual: {is_connected}")
                    
                    if was_connected != is_connected:
                        # El estado de conexión cambió
                        self.scanner_connected = is_connected
                        status_text = "conectado" if is_connected else "desconectado"
                        self.logger.info(f"🔄 Estado del escáner cambió: {status_text}")
                        
                        # Actualizar JSON con el estado real
                        self.data_sync.update_scanner_status(is_connected)
                        
                        if not is_connected:
                            self.logger.warning("⚠️ Escáner desconectado - Verificar conexión física")
                        else:
                            self.logger.info("✅ Escáner reconectado exitosamente")
                    else:
                        # Log cada cierto tiempo para confirmar que está funcionando
                        self.logger.debug(f"Estado del escáner sin cambios: {'conectado' if is_connected else 'desconectado'}")
                    
                    self.last_connection_check = current_time
                
                time.sleep(1)  # Verificar cada segundo
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"❌ Error monitoreando conexión del escáner: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(2)
        
        self.logger.info("Bucle de monitoreo de conexión terminado")
    
    def _check_scanner_connection(self) -> bool:
        """Verificar si el escáner está realmente conectado"""
        try:
            # Si no hay scanner inicializado, intentar reconectar
            if not self.scanner:
                self.logger.debug("No hay scanner inicializado, intentando reconectar...")
                return self._try_reconnect_scanner()
            
            # Usar el método test_connection del scanner si existe
            if hasattr(self.scanner, 'test_connection'):
                connection_ok = self.scanner.test_connection()
                self.logger.debug(f"test_connection() retornó: {connection_ok}")
                
                # Si la conexión falló, intentar reinicializar el scanner
                if not connection_ok:
                    self.logger.info("SCANNER RECONNECT: Conexión falló, intentando reinicializar scanner...")
                    # Desconectar scanner anterior
                    try:
                        self.scanner.disconnect()
                        self.logger.info("SCANNER RECONNECT: Scanner anterior desconectado")
                    except Exception as e:
                        self.logger.info(f"SCANNER RECONNECT: Error desconectando scanner anterior: {e}")
                    self.scanner = None
                    
                    # Intentar reconectar
                    self.logger.info("SCANNER RECONNECT: Iniciando proceso de reconexión...")
                    result = self._try_reconnect_scanner()
                    self.logger.info(f"SCANNER RECONNECT: Resultado de reconexión: {result}")
                    return result
                
                return connection_ok
            
            # Verificar si el estado interno del scanner indica conexión
            if hasattr(self.scanner, 'is_connected'):
                is_conn = self.scanner.is_connected()
                self.logger.debug(f"is_connected() retornó: {is_conn}")
                return is_conn
            
            # Verificar si el serial interface está conectado
            if hasattr(self.scanner, 'serial_interface') and self.scanner.serial_interface:
                if hasattr(self.scanner.serial_interface, 'test_connection'):
                    serial_ok = self.scanner.serial_interface.test_connection()
                    self.logger.debug(f"serial_interface.test_connection() retornó: {serial_ok}")
                    return serial_ok
            
            self.logger.debug("No se pudo verificar conexión - métodos no disponibles")
            return False
            
        except Exception as e:
            self.logger.debug(f"Error verificando conexión del escáner: {e}")
            return False
    
    def _try_reconnect_scanner(self) -> bool:
        """Intentar reconectar el escáner si no está inicializado"""
        try:
            self.logger.info("SCANNER RECONNECT: Intentando reinicializar scanner...")
            hardware_config = self.config.hardware
            self.logger.info(f"SCANNER RECONNECT: Puerto: {hardware_config.serial_port}, Baud: {hardware_config.baud_rate}")
            
            # Crear nuevo scanner
            from ..hardware.zebra_scanner import ZebraScanner
            new_scanner = ZebraScanner(
                port=hardware_config.serial_port,
                baud_rate=hardware_config.baud_rate,
                timeout=hardware_config.timeout
            )
            self.logger.info("SCANNER RECONNECT: Nuevo objeto scanner creado")
            
            # Intentar conectar
            self.logger.info("SCANNER RECONNECT: Intentando conectar...")
            if new_scanner.connect():
                self.scanner = new_scanner
                self.logger.info("SCANNER RECONNECT: Scanner reconectado exitosamente!")
                return True
            else:
                self.logger.info("SCANNER RECONNECT: Fallo al conectar el nuevo scanner")
                return False
                
        except Exception as e:
            self.logger.error(f"SCANNER RECONNECT: Error intentando reconectar scanner: {e}")
            import traceback
            self.logger.error(f"SCANNER RECONNECT: Traceback: {traceback.format_exc()}")
            return False
    
    def _process_scan_event(self, scan_event: ScanEvent):
        """Procesar evento de escaneo"""
        try:
            barcode = scan_event.barcode
            
            # Verificar si el producto existe
            if barcode not in self.products:
                self.logger.warning(f"Producto no encontrado: {barcode}")
                self._trigger_callback('product_not_found', scan_event)
                return False
            
            product = self.products[barcode]
            
            # Verificar si ya completó la etapa actual
            current_stage_execution = product.stage_executions.get(self.current_stage)
            if current_stage_execution and current_stage_execution.status.value == "Completado":
                self.logger.warning(f"Producto {barcode} ya completó la etapa {self.current_stage}")
                self._trigger_callback('stage_already_completed', scan_event)
                return False
            
            # Procesar el escaneo
            self._execute_stage_scan(product, scan_event)
            
            # Actualizar estadísticas
            self._update_session_stats(scan_event)
            
            # Sincronizar datos
            self.data_sync.sync_product(product)
            
            # Notificar evento
            self._trigger_callback('scan_processed', scan_event)
            
            self.logger.info(f"Escaneo procesado exitosamente: {barcode}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error procesando escaneo: {e}")
            scan_event.success = False
            scan_event.error_message = str(e)
            self._trigger_callback('scan_error', scan_event)
            return False
    
    def _execute_stage_scan(self, product: JCIProduct, scan_event: ScanEvent):
        """Ejecutar el escaneo para una etapa específica"""
        stage_id = scan_event.stage_id
        
        # Iniciar la etapa si no ha comenzado
        if product.current_stage == stage_id:
            product.start_current_stage(scan_event.station_id)
            
            # Simular calidad (en producción real vendría de sensores/inspección)
            quality_metrics = self._simulate_quality_metrics(product, stage_id)
            
            # Completar la etapa
            product.complete_current_stage(quality_metrics)
            
            # Actualizar analytics
            self.analytics.record_stage_completion(product, stage_id, quality_metrics)
            
            # Verificar si necesita notificaciones
            self._check_notifications(product)
            
        else:
            # Producto en etapa incorrecta
            raise ValueError(f"Producto en etapa {product.current_stage}, se escaneó en etapa {stage_id}")
    
    def _simulate_quality_metrics(self, product: JCIProduct, stage_id: int) -> QualityMetrics:
        """Simular métricas de calidad (en producción real vendría de sensores)"""
        import random
        
        # Simular calidad basada en el producto y etapa
        base_quality = 95.0
        variation = random.uniform(-5, 2)  # Variación realista
        
        quality_score = max(80.0, min(100.0, base_quality + variation))
        
        return QualityMetrics(
            defect_count=1 if quality_score < 90 else 0,
            rework_count=1 if quality_score < 85 else 0,
            quality_score=quality_score,
            inspector_id=f"QC{stage_id:03d}",
            inspection_notes=f"Inspección automática etapa {stage_id}",
            passed_inspection=quality_score >= 85
        )
    
    def _process_web_command(self, command: Dict[str, Any]):
        """Procesar comando desde interfaz web"""
        try:
            command_type = command.get('comando')
            parameters = command.get('parametros', {})
            
            self.logger.info(f"Procesando comando web: {command_type}")
            
            if command_type == 'simular_escaneo':
                barcode = parameters.get('codigo')
                if barcode:
                    self.simulate_scan(barcode)
            
            elif command_type == 'cambiar_etapa':
                stage = parameters.get('etapa')
                if stage and 1 <= stage <= 6:
                    self.change_current_stage(stage)
            
            elif command_type == 'actualizar_estado':
                self.sync_system_state()
            
            elif command_type == 'reset_producto':
                barcode = parameters.get('codigo')
                if barcode:
                    self.reset_product(barcode)
            
            else:
                self.logger.warning(f"Comando desconocido: {command_type}")
            
            # Marcar comando como procesado
            self.data_sync.mark_command_processed(command)
            
        except Exception as e:
            self.logger.error(f"Error procesando comando web: {e}")
    
    def simulate_scan(self, barcode: str) -> bool:
        """Simular escaneo de código"""
        try:
            scan_event = ScanEvent(
                timestamp=datetime.now(),
                barcode=barcode,
                stage_id=self.current_stage,
                operator_id=self._get_current_operator(),
                station_id=self._get_current_station(),
                success=True
            )
            
            return self._process_scan_event(scan_event)
            
        except Exception as e:
            self.logger.error(f"Error en simulación de escaneo: {e}")
            return False
    
    def change_current_stage(self, stage_id: int):
        """Cambiar la etapa actual del sistema"""
        if 1 <= stage_id <= 6:
            old_stage = self.current_stage
            self.current_stage = stage_id
            
            self.logger.info(f"Etapa cambiada de {old_stage} a {stage_id}")
            self.sync_system_state()
            
            self._trigger_callback('stage_changed', {
                'old_stage': old_stage,
                'new_stage': stage_id
            })
        else:
            raise ValueError(f"Etapa inválida: {stage_id}")
    
    def reset_product(self, barcode: str):
        """Resetear producto a estado inicial"""
        if barcode in self.products:
            product = self.products[barcode]
            product.status = ProductStatus.PENDING
            product.progress_percentage = 0.0
            product.current_stage = 1
            product.started_at = None
            product.completed_at = None
            
            # Resetear todas las etapas
            for stage in product.stage_executions.values():
                stage.status = stage.status.NOT_STARTED
                stage.start_time = None
                stage.end_time = None
                stage.duration_seconds = 0
            
            self.data_sync.sync_product(product)
            self.logger.info(f"Producto reseteado: {barcode}")
        else:
            raise ValueError(f"Producto no encontrado: {barcode}")
    
    def sync_system_state(self):
        """Sincronizar estado completo del sistema"""
        try:
            system_state = {
                'current_stage': self.current_stage,
                'is_running': self.is_running,
                'scan_count': self.scan_count,
                'error_count': self.error_count,
                'products': {barcode: product.to_dict() 
                           for barcode, product in self.products.items()},
                'session_stats': self.session_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            self.data_sync.save_system_state(system_state)
            self.logger.debug("Estado del sistema sincronizado")
            
        except Exception as e:
            self.logger.error(f"Error sincronizando estado: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado actual del sistema"""
        return {
            'is_running': self.is_running,
            'current_stage': self.current_stage,
            'scanner_connected': self.scanner_connected,  # Usar el estado monitoreado en tiempo real
            'products_count': len(self.products),
            'session_stats': self.session_stats,
            'error_count': self.error_count
        }
    
    def get_products_summary(self) -> Dict[str, Any]:
        """Obtener resumen de productos"""
        completed = sum(1 for p in self.products.values() 
                       if p.status == ProductStatus.COMPLETED)
        in_progress = sum(1 for p in self.products.values() 
                         if p.status == ProductStatus.IN_PROGRESS)
        pending = sum(1 for p in self.products.values() 
                     if p.status == ProductStatus.PENDING)
        
        return {
            'total': len(self.products),
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'completion_rate': (completed / len(self.products) * 100) if self.products else 0
        }
    
    def register_callback(self, event_type: str, callback: Callable):
        """Registrar callback para eventos"""
        self.scan_callbacks[event_type] = callback
    
    def _register_default_callbacks(self):
        """Registrar callbacks por defecto"""
        self.register_callback('scan_processed', self._on_scan_processed)
        self.register_callback('product_not_found', self._on_product_not_found)
        self.register_callback('stage_already_completed', self._on_stage_already_completed)
    
    def _trigger_callback(self, event_type: str, data: Any):
        """Disparar callback para evento"""
        if event_type in self.scan_callbacks:
            try:
                self.scan_callbacks[event_type](data)
            except Exception as e:
                self.logger.error(f"Error en callback {event_type}: {e}")
    
    def _on_scan_processed(self, scan_event: ScanEvent):
        """Callback para escaneo procesado exitosamente"""
        self.notifications.send_scan_notification(scan_event)
    
    def _on_product_not_found(self, scan_event: ScanEvent):
        """Callback para producto no encontrado"""
        self.notifications.send_error_notification(
            f"Producto no encontrado: {scan_event.barcode}"
        )
    
    def _on_stage_already_completed(self, scan_event: ScanEvent):
        """Callback para etapa ya completada"""
        self.notifications.send_warning_notification(
            f"Etapa {scan_event.stage_id} ya completada para {scan_event.barcode}"
        )
    
    def _get_current_operator(self) -> str:
        """Obtener operador actual basado en la etapa"""
        operators = {
            1: "OP001",  # Soldadura
            2: "OP002",  # Pulido  
            3: "OP003",  # Presión
            4: "QC001",  # Calidad
            5: "OP004",  # Pintura
            6: "WH001"   # Almacén
        }
        return operators.get(self.current_stage, "OP000")
    
    def _get_current_station(self) -> str:
        """Obtener estación actual"""
        stations = {
            1: "EST-SOLD-01",
            2: "EST-PULI-01", 
            3: "EST-PRES-01",
            4: "EST-CALI-01",
            5: "EST-PINT-01",
            6: "EST-ALMA-01"
        }
        return stations.get(self.current_stage, "EST-GEN-01")
    
    def _update_session_stats(self, scan_event: ScanEvent):
        """Actualizar estadísticas de sesión"""
        self.session_stats['scans_processed'] += 1
        
        if scan_event.success:
            self.scan_count += 1
        else:
            self.error_count += 1
            self.session_stats['errors_count'] += 1
    
    def _check_notifications(self, product: JCIProduct):
        """Verificar si se necesitan notificaciones para el producto"""
        # Verificar si se completó
        if product.status == ProductStatus.COMPLETED:
            self.notifications.send_completion_notification(product)
            self.session_stats['products_completed'] += 1
        
        # Verificar si está retrasado
        if product.is_overdue():
            self.notifications.send_delay_notification(product)
        
        # Verificar calidad
        if product.quality_score < 85:
            self.notifications.send_quality_alert(product)
    
    def shutdown(self):
        """Apagar el sistema ordenadamente"""
        self.logger.info("Iniciando apagado del sistema...")
        
        self.is_running = False
        
        # Cerrar conexión del escáner
        if self.scanner:
            self.scanner.disconnect()
        
        # Esperar que terminen los hilos
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.join(timeout=2)
        
        if self.command_thread and self.command_thread.is_alive():
            self.command_thread.join(timeout=2)
        
        if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            self.connection_monitor_thread.join(timeout=2)
        
        # Sincronizar estado final
        self.sync_system_state()
        
        self.logger.info("Sistema apagado correctamente")