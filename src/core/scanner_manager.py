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
from .stage_manager import global_stage_manager


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
        
        # Estado del sistema - se inicializará con la primera etapa activa
        self.current_stage = None
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
    
    def _initialize_current_stage(self):
        """Inicializar etapa actual con la primera etapa activa del sistema dinámico"""
        try:
            active_stages = global_stage_manager.get_active_stages()
            if active_stages:
                # Ordenar por order_position y tomar la primera
                sorted_stages = sorted(active_stages, key=lambda x: x.get('order_position', 999))
                self.current_stage = sorted_stages[0]['id']
                stage_name = sorted_stages[0]['name']
                self.logger.info(f"TARGET: Etapa inicial sincronizada dinámicamente: {self.current_stage} ({stage_name})")
            else:
                # Fallback si no hay etapas activas
                self.current_stage = 1
                self.logger.warning("WARNING: No hay etapas activas, usando fallback: etapa 1")
                
        except Exception as e:
            self.logger.error(f"ERROR: Error inicializando etapa actual: {e}")
            self.current_stage = 1  # Fallback seguro
    
    def initialize(self) -> bool:
        """Inicializar el sistema completo"""
        try:
            self.logger.info("Iniciando sistema de escaneo Johnson Controls...")
            
            # Inicializar servicios PRIMERO (incluye sincronización de datos)
            self.data_sync.initialize()
            self.analytics.initialize()
            self.notifications.initialize()
            
            # Cargar productos existentes DESPUÉS de la sincronización
            self._load_existing_products()
            
            # Inicializar hardware
            if not self._initialize_hardware():
                self.logger.warning("Hardware no disponible - Modo simulación activado")
            
            # Iniciar hilos de procesamiento
            self._start_processing_threads()
            
            # Registrar callbacks por defecto
            self._register_default_callbacks()
            
            # Inicializar etapa actual con la primera etapa activa del sistema dinámico
            self._initialize_current_stage()
            
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
            
            # Cargar productos existentes
            for product_data in stored_products:
                product = JCIProduct.from_dict(product_data)
                self.products[product.barcode] = product
            
            self.logger.info(f"Cargados {len(self.products)} productos existentes")
            
            # Siempre asegurar que todos los productos de muestra estén disponibles
            self._ensure_all_sample_products()
            
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
    
    def _ensure_all_sample_products(self):
        """Asegurar que todos los productos de muestra estén disponibles"""
        from ..models.product import JCI_SAMPLE_PRODUCTS
        
        added_count = 0
        for sample_data in JCI_SAMPLE_PRODUCTS:
            barcode = sample_data['barcode']
            if barcode not in self.products:
                product = JCIProduct(**sample_data)
                self.products[product.barcode] = product
                added_count += 1
                self.logger.info(f"Agregado producto faltante: {barcode} - {product.product_name}")
        
        if added_count > 0:
            self.logger.info(f"Se agregaron {added_count} productos nuevos al catálogo")
            # Guardar los cambios
            self.data_sync.save_products(list(self.products.values()))
        else:
            self.logger.info(f"Todos los productos de muestra ({len(JCI_SAMPLE_PRODUCTS)}) ya están disponibles")
    
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
                        self.logger.info(f"REFRESH: Estado del escáner cambió: {status_text}")
                        
                        # Actualizar JSON con el estado real
                        self.data_sync.update_scanner_status(is_connected)
                        
                        if not is_connected:
                            self.logger.warning("WARNING: Escáner desconectado - Verificar conexión física")
                        else:
                            self.logger.info("SUCCESS: Escáner reconectado exitosamente")
                    else:
                        # Log cada cierto tiempo para confirmar que está funcionando
                        self.logger.debug(f"Estado del escáner sin cambios: {'conectado' if is_connected else 'desconectado'}")
                    
                    self.last_connection_check = current_time
                
                time.sleep(1)  # Verificar cada segundo
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"ERROR: Error monitoreando conexión del escáner: {e}")
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
                
                # Reiniciar el bucle de lectura si no está activo
                self.logger.debug(f"SCANNER RECONNECT: Verificando estado del hilo de lectura...")
                has_thread = hasattr(self, 'scanning_thread')
                thread_alive = self.scanning_thread.is_alive() if has_thread else False
                self.logger.debug(f"SCANNER RECONNECT: has_thread={has_thread}, thread_alive={thread_alive}")
                
                if not has_thread or not thread_alive:
                    self.logger.info("SCANNER RECONNECT: Reiniciando bucle de lectura...")
                    self._start_scanning_thread()
                else:
                    self.logger.info("SCANNER RECONNECT: Hilo de lectura ya está activo, no se reinicia")
                
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
            
            # Verificar si ya completó la etapa actual del producto
            product_current_stage = product.current_stage
            current_stage_execution = product.stage_executions.get(product_current_stage)
            if current_stage_execution and current_stage_execution.status.value == "Completado":
                self.logger.warning(f"Producto {barcode} ya completó la etapa {product_current_stage}")
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
        
        # Asignar operador automáticamente basado en la etapa
        self._assign_operator_to_stage(product, stage_id, scan_event.operator_id)
        
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
            # Si producto no está en la etapa esperada, actualizar su etapa al sistema
            self.logger.info(f"Producto {product.barcode} en etapa {product.current_stage}, actualizando a etapa del sistema {stage_id}")
            product.current_stage = stage_id
            
            # Ahora ejecutar el procesamiento de la etapa
            product.start_current_stage(scan_event.station_id)
            
            # Simular calidad (en producción real vendría de sensores/inspección)
            quality_metrics = self._simulate_quality_metrics(product, stage_id)
            
            # Completar la etapa
            product.complete_current_stage(quality_metrics)
            
            # Actualizar analytics
            self.analytics.record_stage_completion(product, stage_id, quality_metrics)
            
            # Verificar si necesita notificaciones
            self._check_notifications(product)
    
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
                if stage and global_stage_manager.validate_stage_id(stage):
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
            # Obtener el producto para usar su etapa actual
            if barcode not in self.products:
                self.logger.warning(f"Producto no encontrado para simulación: {barcode}")
                return False
                
            product = self.products[barcode]
            product_stage = product.current_stage
            
            # Si el producto está en etapa 1, usar la primera etapa activa del sistema
            if product_stage == 1:
                active_stages = global_stage_manager.get_active_stages()
                if active_stages:
                    sorted_stages = sorted(active_stages, key=lambda x: x.get('order_position', 999))
                    product_stage = sorted_stages[0]['id']
                    self.logger.info(f"Producto {barcode} en etapa 1, actualizando a etapa del sistema {product_stage}")
            
            scan_event = ScanEvent(
                timestamp=datetime.now(),
                barcode=barcode,
                stage_id=product_stage,
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
        if global_stage_manager.validate_stage_id(stage_id):
            old_stage = self.current_stage
            self.current_stage = stage_id
            
            stage_name = global_stage_manager.get_stage_name(stage_id)
            self.logger.info(f"Etapa cambiada de {old_stage} a {stage_id} ({stage_name})")
            self.sync_system_state()
            
            self._trigger_callback('stage_changed', {
                'old_stage': old_stage,
                'new_stage': stage_id,
                'stage_name': stage_name
            })
        else:
            raise ValueError(f"Etapa inválida: {stage_id}")
    
    def reset_product(self, barcode: str):
        """Resetear producto a estado inicial"""
        if barcode in self.products:
            product = self.products[barcode]
            product.status = ProductStatus.PENDING
            product.progress_percentage = 0.0
            
            # Resetear a la primera etapa activa disponible
            active_stages = global_stage_manager.get_active_stages()
            if active_stages:
                product.current_stage = active_stages[0]['id']
            else:
                product.current_stage = 1  # Fallback
                
            product.started_at = None
            product.completed_at = None
            
            # Resetear todas las etapas
            for stage in product.stage_executions.values():
                stage.status = stage.status.NOT_STARTED
                stage.start_time = None
                stage.end_time = None
                stage.duration_seconds = 0
            
            # Sincronizar etapas con la configuración actual
            product.synchronize_stages()
            
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
    
    def _assign_operator_to_stage(self, product: JCIProduct, stage_id: int, operator_id: str):
        """Asignar operador automáticamente a la etapa del producto usando gestión dinámica"""
        try:
            self.logger.info(f"OPERATOR_ASSIGN: Iniciando asignación de operador para producto {product.barcode}, etapa {stage_id}")
            
            # Usar el nuevo gestor de operadores dinámicos
            from ..utils.operators_manager import operators_manager
            
            # Cargar todos los operadores disponibles (dinámico)
            all_operators = operators_manager.get_all_operators()
            self.logger.info(f"OPERATOR_ASSIGN: Operadores disponibles: {len(all_operators)}")
            
            if stage_id in product.stage_executions:
                stage_execution = product.stage_executions[stage_id]
                self.logger.info(f"OPERATOR_ASSIGN: Etapa {stage_id} encontrada, operador actual: '{stage_execution.operator_id}'")
                
                # Si ya tiene operador asignado y está activo, mantenerlo
                if stage_execution.operator_id and stage_execution.operator_id in all_operators:
                    current_operator = all_operators[stage_execution.operator_id]
                    if current_operator.get('active', True):
                        self.logger.info(f"OPERATOR_ASSIGN: Operador {stage_execution.operator_id} ya asignado y activo")
                        return
                
                # Buscar el mejor operador para esta etapa específica
                best_operator = operators_manager.find_best_operator_for_stage(stage_id)
                
                if best_operator:
                    # Asignar el operador encontrado
                    stage_execution.operator_id = best_operator['id']
                    stage_execution.operator_name = best_operator['name']
                    stage_execution.station_id = best_operator.get('station', '')
                    
                    self.logger.info(f"OPERATOR_ASSIGN: Operador asignado exitosamente:")
                    self.logger.info(f"  - ID: {best_operator['id']}")
                    self.logger.info(f"  - Nombre: {best_operator['name']}")
                    self.logger.info(f"  - Estación: {best_operator.get('station', 'N/A')}")
                    self.logger.info(f"  - Fuente: {best_operator.get('source', 'unknown')}")
                    
                    # Actualizar operador en la ejecución de etapa
                    if stage_id in product.stage_executions:
                        product.stage_executions[stage_id].operator_id = best_operator['id']
                        self.logger.info(f"OPERATOR_ASSIGN: Operador {best_operator['id']} asignado a etapa {stage_id}")
                else:
                    # Si no hay operador específico, usar operador genérico desde stages
                    self.logger.warning(f"OPERATOR_ASSIGN: No se encontró operador específico para etapa {stage_id}")
                    
                    # Buscar operador genérico en la configuración de etapas
                    stage_operator = self._get_stage_default_operator(stage_id)
                    if stage_operator:
                        stage_execution.operator_name = stage_operator
                        stage_execution.operator_id = ""  # Sin ID específico
                        self.logger.info(f"OPERATOR_ASSIGN: Usando operador de etapa por defecto: {stage_operator}")
                    else:
                        self.logger.warning(f"OPERATOR_ASSIGN: No se pudo asignar operador para etapa {stage_id}")
            else:
                self.logger.warning(f"OPERATOR_ASSIGN: Etapa {stage_id} no encontrada en producto {product.barcode}")
                
        except Exception as e:
            self.logger.error(f"OPERATOR_ASSIGN: Error asignando operador a etapa {stage_id}: {e}")
            # En caso de error, intentar asignar información básica
            if stage_id in product.stage_executions:
                stage_execution = product.stage_executions[stage_id]
                stage_operator = self._get_stage_default_operator(stage_id)
                if stage_operator:
                    stage_execution.operator_name = stage_operator
                    stage_execution.operator_id = ""
                    self.logger.info(f"OPERATOR_ASSIGN: Fallback - usando operador de configuración: {stage_operator}")
                else:
                    stage_execution.operator_name = "Sistema Automático"
                    stage_execution.operator_id = "AUTO"
    
    def _get_stage_default_operator(self, stage_id: int) -> str:
        """Obtener operador por defecto desde la configuración de etapas"""
        try:
            from ..utils import config
            import json
            
            stages_file = config.get_data_path("json") / "stages_config.json"
            if stages_file.exists():
                with open(stages_file, 'r', encoding='utf-8') as f:
                    stages_data = json.load(f)
                
                for stage in stages_data.get('stages', []):
                    if stage.get('id') == stage_id:
                        return stage.get('operator_name', '').strip()
            
            return ""
        except Exception as e:
            self.logger.error(f"OPERATOR_ASSIGN: Error obteniendo operador de etapa {stage_id}: {e}")
            return ""
    
    def _find_suitable_operator(self, stage_id: int, operators_data: dict) -> dict:
        """Encontrar operador más adecuado para una etapa específica"""
        stage_skills_map = {
            7: ['soldadura'],  # Soldadura
            8: ['pulido', 'acabados'],  # Pulido
            10: ['inspeccion', 'control_calidad', 'medicion'],  # Calidad
            11: ['pintura', 'acabados'],  # Pintura
            12: ['almacen', 'logistica'],  # Almacén
            13: ['supervision']  # Prueba
        }
        
        required_skills = stage_skills_map.get(stage_id, [])
        
        # Buscar operadores que tengan las habilidades requeridas
        suitable_operators = []
        for op_id, operator in operators_data.items():
            if operator.get('status') == 'active':
                operator_skills = operator.get('skills', [])
                # Verificar si el operador tiene alguna de las habilidades requeridas
                if any(skill in operator_skills for skill in required_skills):
                    suitable_operators.append({
                        'id': op_id,
                        'name': operator['name'],
                        'skills': operator_skills,
                        'station': operator.get('station', ''),
                        'shift': operator.get('shift', '')
                    })
        
        # Si hay operadores aptos, devolver el primero (se puede mejorar con lógica de priorización)
        if suitable_operators:
            return suitable_operators[0]
        
        # Si no hay operadores específicos, buscar cualquier operador activo
        for op_id, operator in operators_data.items():
            if operator.get('status') == 'active':
                return {
                    'id': op_id,
                    'name': operator['name'],
                    'skills': operator.get('skills', []),
                    'station': operator.get('station', ''),
                    'shift': operator.get('shift', '')
                }
        
        return None
    
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
        # Usar información dinámica de estaciones
        try:
            stage_info = global_stage_manager.get_stage(self.current_stage)
            if stage_info and stage_info.get('station_id'):
                return stage_info['station_id']
        except Exception:
            pass
        
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