#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTIFICATION SERVICE - Servicio de notificaciones y alertas
Johnson Controls - Sistema de Seguimiento Industrial
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..utils.config import config


class NotificationType(Enum):
    """Tipos de notificación"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Modelo de notificación"""
    id: str
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    source: str = "system"
    data: Dict[str, Any] = None
    acknowledged: bool = False
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class NotificationService:
    """Servicio de notificaciones y alertas"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        
        # Estado del servicio
        self.is_running = False
        self.notification_thread = None
        
        # Almacenamiento de notificaciones
        self.notifications: List[Notification] = []
        self.max_notifications = 1000
        
        # Callbacks para diferentes tipos de notificación
        self.callbacks: Dict[NotificationType, List[Callable]] = {
            NotificationType.INFO: [],
            NotificationType.SUCCESS: [],
            NotificationType.WARNING: [],
            NotificationType.ERROR: [],
            NotificationType.CRITICAL: []
        }
        
        # Configuración de alertas
        self.alert_thresholds = {
            'quality_threshold': 85,
            'efficiency_threshold': 70,
            'cycle_time_threshold': 600,  # segundos
            'error_count_threshold': 5
        }
        
        # Control de hilos
        self.notification_lock = threading.RLock()
        
        self.logger.info("Notification Service inicializado")
    
    def initialize(self) -> bool:
        """Inicializar servicio de notificaciones"""
        try:
            # Registrar callbacks por defecto
            self._register_default_callbacks()
            
            self.logger.info("Notification Service inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando Notification Service: {e}")
            return False
    
    def start(self):
        """Iniciar servicio de notificaciones"""
        if not self.is_running:
            self.is_running = True
            self.logger.info("Notification Service iniciado")
    
    def stop(self):
        """Detener servicio de notificaciones"""
        self.is_running = False
        self.logger.info("Notification Service detenido")
    
    def send_notification(self, 
                         type: NotificationType,
                         title: str,
                         message: str,
                         source: str = "system",
                         data: Dict[str, Any] = None) -> str:
        """Enviar notificación"""
        try:
            # Generar ID único
            notification_id = f"{type.value}_{int(datetime.now().timestamp() * 1000)}"
            
            # Crear notificación
            notification = Notification(
                id=notification_id,
                type=type,
                title=title,
                message=message,
                timestamp=datetime.now(),
                source=source,
                data=data or {}
            )
            
            # Agregar a la lista
            with self.notification_lock:
                self.notifications.append(notification)
                
                # Mantener límite de notificaciones
                if len(self.notifications) > self.max_notifications:
                    self.notifications = self.notifications[-self.max_notifications:]
            
            # Log según tipo
            if type == NotificationType.CRITICAL:
                self.logger.critical(f"{title}: {message}")
            elif type == NotificationType.ERROR:
                self.logger.error(f"{title}: {message}")
            elif type == NotificationType.WARNING:
                self.logger.warning(f"{title}: {message}")
            else:
                self.logger.info(f"{title}: {message}")
            
            # Ejecutar callbacks
            self._execute_callbacks(type, notification)
            
            return notification_id
            
        except Exception as e:
            self.logger.error(f"Error enviando notificación: {e}")
            return ""
    
    def send_scan_notification(self, scan_event):
        """Enviar notificación de escaneo"""
        try:
            title = "Escaneo Procesado"
            message = f"Producto {scan_event.barcode} procesado en etapa {scan_event.stage_id}"
            
            self.send_notification(
                NotificationType.SUCCESS,
                title,
                message,
                source="scanner",
                data={
                    'barcode': scan_event.barcode,
                    'stage_id': scan_event.stage_id,
                    'operator_id': scan_event.operator_id,
                    'timestamp': scan_event.timestamp.isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando notificación de escaneo: {e}")
    
    def send_error_notification(self, error_message: str, source: str = "system"):
        """Enviar notificación de error"""
        self.send_notification(
            NotificationType.ERROR,
            "Error del Sistema",
            error_message,
            source=source
        )
    
    def send_warning_notification(self, warning_message: str, source: str = "system"):
        """Enviar notificación de advertencia"""
        self.send_notification(
            NotificationType.WARNING,
            "Advertencia del Sistema",
            warning_message,
            source=source
        )
    
    def send_completion_notification(self, product):
        """Enviar notificación de producto completado"""
        try:
            title = "Producto Completado"
            message = f"Producto {product.barcode} ({product.product_name}) completado exitosamente"
            
            self.send_notification(
                NotificationType.SUCCESS,
                title,
                message,
                source="production",
                data={
                    'barcode': product.barcode,
                    'product_name': product.product_name,
                    'total_cycle_time': product.total_cycle_time,
                    'efficiency_score': product.efficiency_score,
                    'quality_score': product.quality_score
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando notificación de completado: {e}")
    
    def send_delay_notification(self, product):
        """Enviar notificación de retraso"""
        try:
            title = "Producto Retrasado"
            message = f"Producto {product.barcode} excedió tiempo objetivo ({product.target_cycle_time}s)"
            
            self.send_notification(
                NotificationType.WARNING,
                title,
                message,
                source="production",
                data={
                    'barcode': product.barcode,
                    'product_name': product.product_name,
                    'target_cycle_time': product.target_cycle_time,
                    'current_time': product.total_cycle_time
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando notificación de retraso: {e}")
    
    def send_quality_alert(self, product):
        """Enviar alerta de calidad"""
        try:
            title = "Alerta de Calidad"
            message = f"Producto {product.barcode} con calidad baja ({product.quality_score:.1f}%)"
            
            notification_type = NotificationType.CRITICAL if product.quality_score < 70 else NotificationType.WARNING
            
            self.send_notification(
                notification_type,
                title,
                message,
                source="quality",
                data={
                    'barcode': product.barcode,
                    'product_name': product.product_name,
                    'quality_score': product.quality_score,
                    'threshold': self.alert_thresholds['quality_threshold']
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta de calidad: {e}")
    
    def register_callback(self, notification_type: NotificationType, callback: Callable):
        """Registrar callback para tipo de notificación"""
        if notification_type in self.callbacks:
            self.callbacks[notification_type].append(callback)
            self.logger.debug(f"Callback registrado para {notification_type.value}")
    
    def _register_default_callbacks(self):
        """Registrar callbacks por defecto"""
        # Callback para notificaciones críticas
        def critical_callback(notification: Notification):
            # En producción, esto podría enviar email, SMS, etc.
            self.logger.critical(f"CRÍTICO: {notification.title} - {notification.message}")
        
        self.register_callback(NotificationType.CRITICAL, critical_callback)
    
    def _execute_callbacks(self, notification_type: NotificationType, notification: Notification):
        """Ejecutar callbacks para tipo de notificación"""
        try:
            for callback in self.callbacks.get(notification_type, []):
                try:
                    callback(notification)
                except Exception as e:
                    self.logger.error(f"Error ejecutando callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error ejecutando callbacks: {e}")
    
    def get_notifications(self, 
                         limit: int = 50,
                         type_filter: NotificationType = None,
                         acknowledged_filter: bool = None) -> List[Dict[str, Any]]:
        """Obtener notificaciones"""
        try:
            with self.notification_lock:
                notifications = self.notifications.copy()
            
            # Aplicar filtros
            if type_filter:
                notifications = [n for n in notifications if n.type == type_filter]
            
            if acknowledged_filter is not None:
                notifications = [n for n in notifications if n.acknowledged == acknowledged_filter]
            
            # Ordenar por timestamp (más recientes primero)
            notifications.sort(key=lambda n: n.timestamp, reverse=True)
            
            # Aplicar límite
            notifications = notifications[:limit]
            
            # Convertir a diccionarios
            return [self._notification_to_dict(n) for n in notifications]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo notificaciones: {e}")
            return []
    
    def acknowledge_notification(self, notification_id: str) -> bool:
        """Marcar notificación como reconocida"""
        try:
            with self.notification_lock:
                for notification in self.notifications:
                    if notification.id == notification_id:
                        notification.acknowledged = True
                        self.logger.debug(f"Notificación {notification_id} reconocida")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error reconociendo notificación: {e}")
            return False
    
    def clear_notifications(self, type_filter: NotificationType = None) -> int:
        """Limpiar notificaciones"""
        try:
            with self.notification_lock:
                if type_filter:
                    original_count = len(self.notifications)
                    self.notifications = [n for n in self.notifications if n.type != type_filter]
                    cleared_count = original_count - len(self.notifications)
                else:
                    cleared_count = len(self.notifications)
                    self.notifications.clear()
                
                self.logger.info(f"{cleared_count} notificaciones limpiadas")
                return cleared_count
                
        except Exception as e:
            self.logger.error(f"Error limpiando notificaciones: {e}")
            return 0
    
    def get_notification_summary(self) -> Dict[str, Any]:
        """Obtener resumen de notificaciones"""
        try:
            with self.notification_lock:
                notifications = self.notifications.copy()
            
            # Contar por tipo
            type_counts = {}
            unacknowledged_count = 0
            
            for notification in notifications:
                type_name = notification.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
                
                if not notification.acknowledged:
                    unacknowledged_count += 1
            
            # Notificaciones recientes (última hora)
            recent_threshold = datetime.now().timestamp() - 3600
            recent_count = sum(1 for n in notifications if n.timestamp.timestamp() > recent_threshold)
            
            return {
                'total': len(notifications),
                'unacknowledged': unacknowledged_count,
                'recent_hour': recent_count,
                'by_type': type_counts,
                'last_notification': notifications[-1].timestamp.isoformat() if notifications else None
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen: {e}")
            return {}
    
    def _notification_to_dict(self, notification: Notification) -> Dict[str, Any]:
        """Convertir notificación a diccionario"""
        return {
            'id': notification.id,
            'type': notification.type.value,
            'title': notification.title,
            'message': notification.message,
            'timestamp': notification.timestamp.isoformat(),
            'source': notification.source,
            'data': notification.data,
            'acknowledged': notification.acknowledged
        }
    
    def test_notifications(self):
        """Método de prueba para generar notificaciones de ejemplo"""
        self.send_notification(
            NotificationType.INFO,
            "Sistema Iniciado",
            "El sistema de notificaciones está funcionando correctamente"
        )
        
        self.send_notification(
            NotificationType.WARNING,
            "Prueba de Advertencia",
            "Esta es una notificación de prueba de tipo advertencia"
        )
        
        self.send_notification(
            NotificationType.SUCCESS,
            "Prueba Exitosa",
            "Las notificaciones están configuradas correctamente"
        )
        
        self.logger.info("Notificaciones de prueba enviadas")