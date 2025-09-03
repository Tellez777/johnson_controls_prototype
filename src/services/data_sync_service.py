#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATA SYNC SERVICE - Servicio de sincronización de datos
Johnson Controls - Sistema de Seguimiento Industrial
"""

import json
import threading
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from ..utils.config import config, get_database_config
from ..utils.logger import get_logger
from ..models.product import JCIProduct, ProductStatus


class DataSyncService:
    """Servicio de sincronización de datos entre JSON, Excel y sistema"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.db_config = get_database_config()
        
        # Estado del servicio
        self.is_running = False
        self.sync_thread = None
        
        # Archivos de datos
        self.json_state_file = config.get_json_path('state')
        self.json_commands_file = config.get_json_path('commands')
        self.excel_data_file = config.get_excel_path('data')
        self.excel_tracking_file = config.get_excel_path('tracking')
        
        # Cache de datos
        self.current_state = {}
        self.products_cache: Dict[str, Dict[str, Any]] = {}
        
        # Control de versiones y respaldos
        self.backup_dir = Path("data/backup")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de sincronización
        self.sync_interval = 5  # segundos
        self.backup_interval = 300  # 5 minutos
        self.last_backup = datetime.now()
        
        # Locks para thread safety
        self.state_lock = threading.RLock()
        self.excel_lock = threading.RLock()
        
        self.logger.info("Data Sync Service inicializado")
    
    def initialize(self) -> bool:
        """Inicializar servicio de sincronización"""
        try:
            # Crear archivos base si no existen
            self._ensure_data_files()
            
            # Cargar estado inicial
            self._load_initial_state()
            
            # Verificar integridad de datos
            self._verify_data_integrity()
            
            self.logger.info("Data Sync Service inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando Data Sync Service: {e}")
            return False
    
    def start(self):
        """Iniciar servicio de sincronización automática"""
        if not self.is_running:
            self.is_running = True
            self.sync_thread = threading.Thread(
                target=self._sync_loop,
                daemon=True
            )
            self.sync_thread.start()
            self.logger.info("Data Sync Service iniciado")
    
    def stop(self):
        """Detener servicio de sincronización"""
        self.is_running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10)
        self.logger.info("Data Sync Service detenido")
    
    def _ensure_data_files(self):
        """Asegurar que los archivos de datos existan"""
        # Crear directorios
        self.json_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.excel_data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo JSON de estado si no existe
        if not self.json_state_file.exists():
            initial_state = {
                'timestamp': datetime.now().isoformat(),
                'system_version': '2.0',
                'plant_id': config.johnson_controls.plant_id,
                'current_stage': 1,
                'products': {},
                'statistics': {
                    'total': 0,
                    'completed': 0,
                    'in_progress': 0,
                    'pending': 0
                }
            }
            self._save_json_file(self.json_state_file, initial_state)
        
        # Crear archivo Excel de datos si no existe
        if not self.excel_data_file.exists():
            self._create_excel_data_file()
    
    def _create_excel_data_file(self):
        """Crear archivo Excel de datos con estructura JCI"""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Datos_Productos"
            
            # Headers específicos para Johnson Controls
            headers = [
                'Código_Barras', 'Número_Parte', 'Nombre_Producto', 'Familia_Producto',
                'Orden_Trabajo', 'Número_Lote', 'Número_Serie', 'Código_Cliente',
                'Revisión', 'Especificación', 'Estado', 'Progreso_%', 'Etapa_Actual',
                'Fecha_Creación', 'Fecha_Inicio', 'Fecha_Completado', 'Última_Actualización',
                'Tiempo_Ciclo_Objetivo', 'Tiempo_Ciclo_Real', 'Eficiencia_%', 'Calidad_%',
                'Soldadura_Estado', 'Soldadura_Operador', 'Soldadura_Tiempo', 'Soldadura_Calidad',
                'Pulido_Estado', 'Pulido_Operador', 'Pulido_Tiempo', 'Pulido_Calidad',
                'Presión_Estado', 'Presión_Operador', 'Presión_Tiempo', 'Presión_Calidad',
                'Calidad_Estado', 'Calidad_Inspector', 'Calidad_Tiempo', 'Calidad_Resultado',
                'Pintura_Estado', 'Pintura_Operador', 'Pintura_Tiempo', 'Pintura_Calidad',
                'Almacén_Estado', 'Almacén_Operador', 'Almacén_Tiempo', 'Notas'
            ]
            
            # Escribir headers con formato
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='003D79', end_color='003D79', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Ajustar ancho de columnas
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
            
            # Congelar primera fila
            ws.freeze_panes = 'A2'
            
            wb.save(self.excel_data_file)
            self.logger.info(f"Archivo Excel creado: {self.excel_data_file}")
            
        except Exception as e:
            self.logger.error(f"Error creando archivo Excel: {e}")
            raise
    
    def _load_initial_state(self):
        """Cargar estado inicial desde archivos"""
        with self.state_lock:
            try:
                # Cargar estado JSON
                if self.json_state_file.exists():
                    self.current_state = self._load_json_file(self.json_state_file)
                
                # Cargar productos desde Excel si existe
                if self.excel_data_file.exists():
                    self._load_products_from_excel()
                
                self.logger.info("Estado inicial cargado correctamente")
                
            except Exception as e:
                self.logger.error(f"Error cargando estado inicial: {e}")
    
    def _verify_data_integrity(self):
        """Verificar integridad de datos"""
        try:
            # Verificar consistencia entre JSON y Excel
            json_product_count = len(self.current_state.get('products', {}))
            excel_product_count = len(self.products_cache)
            
            if json_product_count != excel_product_count:
                self.logger.warning(f"Inconsistencia de datos: JSON={json_product_count}, Excel={excel_product_count}")
                # Sincronizar automáticamente
                self._sync_json_to_excel()
            
            self.logger.info("Verificación de integridad completada")
            
        except Exception as e:
            self.logger.error(f"Error verificando integridad: {e}")
    
    def _sync_loop(self):
        """Bucle de sincronización automática"""
        self.logger.info("Iniciando bucle de sincronización")
        
        while self.is_running:
            try:
                # Sincronizar datos
                self._perform_sync()
                
                # Realizar respaldo si es necesario
                if self._should_backup():
                    self._perform_backup()
                
                time.sleep(self.sync_interval)
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Error en bucle de sincronización: {e}")
                    time.sleep(10)  # Pausa más larga en caso de error
        
        self.logger.info("Bucle de sincronización terminado")
    
    def _perform_sync(self):
        """Realizar sincronización completa"""
        with self.state_lock:
            # Verificar si hay cambios pendientes en JSON
            current_json = self._load_json_file(self.json_state_file) if self.json_state_file.exists() else {}
            
            if current_json != self.current_state:
                self.current_state = current_json
                self._sync_json_to_excel()
            
            # Actualizar timestamp de última sincronización
            self.current_state['last_sync'] = datetime.now().isoformat()
    
    def save_system_state(self, state_data: Dict[str, Any]):
        """Guardar estado completo del sistema"""
        try:
            with self.state_lock:
                # Agregar metadatos
                state_data.update({
                    'last_sync': datetime.now().isoformat(),
                    'system_version': '2.0',
                    'plant_id': config.johnson_controls.plant_id
                })
                
                # Guardar en JSON
                self._save_json_file(self.json_state_file, state_data)
                self.current_state = state_data
                
                # Sincronizar a Excel
                self._sync_json_to_excel()
                
                self.logger.debug("Estado del sistema guardado")
            
        except Exception as e:
            self.logger.error(f"Error guardando estado del sistema: {e}")
    
    def load_products(self) -> List[Dict[str, Any]]:
        """Cargar productos desde almacenamiento"""
        try:
            products = []
            
            # Cargar desde JSON primero
            if 'products' in self.current_state:
                for product_data in self.current_state['products'].values():
                    products.append(product_data)
            
            # Si no hay productos en JSON, cargar desde Excel
            if not products and self.excel_data_file.exists():
                self._load_products_from_excel()
                products = list(self.products_cache.values())
            
            self.logger.info(f"Cargados {len(products)} productos")
            return products
            
        except Exception as e:
            self.logger.error(f"Error cargando productos: {e}")
            return []
    
    def sync_product(self, product: JCIProduct):
        """Sincronizar producto individual"""
        try:
            with self.state_lock:
                # Convertir producto a dict
                product_data = product.to_dict()
                
                # Actualizar en estado actual
                if 'products' not in self.current_state:
                    self.current_state['products'] = {}
                
                self.current_state['products'][product.barcode] = product_data
                self.products_cache[product.barcode] = product_data
                
                # Actualizar estadísticas
                self._update_statistics()
                
                # Guardar estado
                self._save_json_file(self.json_state_file, self.current_state)
                
                # Actualizar Excel
                self._update_product_in_excel(product)
                
                self.logger.debug(f"Producto sincronizado: {product.barcode}")
            
        except Exception as e:
            self.logger.error(f"Error sincronizando producto {product.barcode}: {e}")
    
    def _load_products_from_excel(self):
        """Cargar productos desde archivo Excel"""
        try:
            if not self.excel_data_file.exists():
                return
            
            with self.excel_lock:
                wb = openpyxl.load_workbook(self.excel_data_file, data_only=True)
                ws = wb.active
                
                # Leer productos (empezar desde fila 2, saltar headers)
                for row in range(2, ws.max_row + 1):
                    if ws.cell(row, 1).value:  # Si hay código de barras
                        product_data = self._excel_row_to_product_dict(ws, row)
                        if product_data:
                            barcode = product_data['barcode']
                            self.products_cache[barcode] = product_data
                
                wb.close()
                
        except Exception as e:
            self.logger.error(f"Error cargando productos desde Excel: {e}")
    
    def _excel_row_to_product_dict(self, ws, row: int) -> Optional[Dict[str, Any]]:
        """Convertir fila de Excel a diccionario de producto"""
        try:
            # Mapping de columnas (basado en headers creados en _create_excel_data_file)
            data = {
                'barcode': ws.cell(row, 1).value,
                'part_number': ws.cell(row, 2).value,
                'product_name': ws.cell(row, 3).value,
                'product_family': ws.cell(row, 4).value,
                'work_order': ws.cell(row, 5).value,
                'batch_number': ws.cell(row, 6).value,
                'serial_number': ws.cell(row, 7).value,
                'customer_code': ws.cell(row, 8).value,
                'revision': ws.cell(row, 9).value,
                'specification': ws.cell(row, 10).value,
                'status': ws.cell(row, 11).value or 'Pendiente',
                'progress_percentage': ws.cell(row, 12).value or 0.0,
                'current_stage': ws.cell(row, 13).value or 1,
                'created_at': ws.cell(row, 14).value,
                'started_at': ws.cell(row, 15).value,
                'completed_at': ws.cell(row, 16).value,
                'last_updated': ws.cell(row, 17).value,
                'target_cycle_time': ws.cell(row, 18).value or 300,
                'total_cycle_time': ws.cell(row, 19).value or 0,
                'efficiency_score': ws.cell(row, 20).value or 0.0,
                'quality_score': ws.cell(row, 21).value or 100.0
            }
            
            # Validar datos mínimos requeridos
            if not all([data['barcode'], data['part_number'], data['product_name']]):
                return None
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error convirtiendo fila Excel {row}: {e}")
            return None
    
    def _sync_json_to_excel(self):
        """Sincronizar datos JSON a Excel"""
        try:
            if not self.current_state.get('products'):
                return
            
            with self.excel_lock:
                # Cargar workbook existente o crear nuevo
                if self.excel_data_file.exists():
                    wb = openpyxl.load_workbook(self.excel_data_file)
                    ws = wb.active
                    # Limpiar datos existentes (mantener headers)
                    ws.delete_rows(2, ws.max_row)
                else:
                    self._create_excel_data_file()
                    wb = openpyxl.load_workbook(self.excel_data_file)
                    ws = wb.active
                
                # Escribir productos
                row = 2
                for product_data in self.current_state['products'].values():
                    self._write_product_to_excel_row(ws, row, product_data)
                    row += 1
                
                wb.save(self.excel_data_file)
                wb.close()
                
                self.logger.debug("Datos sincronizados a Excel")
            
        except Exception as e:
            self.logger.error(f"Error sincronizando a Excel: {e}")
    
    def _update_product_in_excel(self, product: JCIProduct):
        """Actualizar producto específico en Excel"""
        try:
            with self.excel_lock:
                if not self.excel_data_file.exists():
                    self._create_excel_data_file()
                
                wb = openpyxl.load_workbook(self.excel_data_file)
                ws = wb.active
                
                # Buscar fila del producto
                product_row = None
                for row in range(2, ws.max_row + 1):
                    if ws.cell(row, 1).value == product.barcode:
                        product_row = row
                        break
                
                # Si no existe, agregar al final
                if product_row is None:
                    product_row = ws.max_row + 1
                
                # Escribir datos del producto
                self._write_product_to_excel_row(ws, product_row, product.to_dict())
                
                wb.save(self.excel_data_file)
                wb.close()
            
        except Exception as e:
            self.logger.error(f"Error actualizando producto en Excel: {e}")
    
    def _write_product_to_excel_row(self, ws, row: int, product_data: Dict[str, Any]):
        """Escribir datos de producto a fila de Excel"""
        try:
            # Escribir datos básicos
            ws.cell(row, 1, product_data.get('barcode'))
            ws.cell(row, 2, product_data.get('part_number'))
            ws.cell(row, 3, product_data.get('product_name'))
            ws.cell(row, 4, product_data.get('product_family'))
            ws.cell(row, 5, product_data.get('work_order'))
            ws.cell(row, 6, product_data.get('batch_number'))
            ws.cell(row, 7, product_data.get('serial_number'))
            ws.cell(row, 8, product_data.get('customer_code'))
            ws.cell(row, 9, product_data.get('revision'))
            ws.cell(row, 10, product_data.get('specification'))
            ws.cell(row, 11, product_data.get('status'))
            ws.cell(row, 12, product_data.get('progress_percentage'))
            ws.cell(row, 13, product_data.get('current_stage'))
            
            # Fechas (convertir de ISO string si es necesario)
            for col, field in [(14, 'created_at'), (15, 'started_at'), (16, 'completed_at'), (17, 'last_updated')]:
                date_value = product_data.get(field)
                if date_value and isinstance(date_value, str):
                    try:
                        date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    except:
                        pass
                ws.cell(row, col, date_value)
            
            # Métricas
            ws.cell(row, 18, product_data.get('target_cycle_time'))
            ws.cell(row, 19, product_data.get('total_cycle_time'))
            ws.cell(row, 20, product_data.get('efficiency_score'))
            ws.cell(row, 21, product_data.get('quality_score'))
            
            # Etapas (columnas 22-43)
            stage_executions = product_data.get('stage_executions', {})
            col = 22
            for stage_id in range(1, 7):  # 6 etapas
                stage_data = stage_executions.get(str(stage_id), {})
                ws.cell(row, col, stage_data.get('status', 'No Iniciado'))
                ws.cell(row, col + 1, stage_data.get('operator_name', ''))
                ws.cell(row, col + 2, stage_data.get('duration_seconds', 0))
                ws.cell(row, col + 3, stage_data.get('quality_score', 0))
                col += 4
            
            # Notas
            ws.cell(row, 43, product_data.get('notes', ''))
            
        except Exception as e:
            self.logger.error(f"Error escribiendo producto a Excel: {e}")
    
    def _update_statistics(self):
        """Actualizar estadísticas en el estado actual"""
        try:
            products = self.current_state.get('products', {})
            
            total = len(products)
            completed = sum(1 for p in products.values() if p.get('status') == 'Completado')
            in_progress = sum(1 for p in products.values() if p.get('status') == 'En Proceso')
            pending = sum(1 for p in products.values() if p.get('status') == 'Pendiente')
            
            self.current_state['statistics'] = {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'pending': pending,
                'completion_rate': (completed / total * 100) if total > 0 else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas: {e}")
    
    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Obtener comandos pendientes para procesamiento"""
        try:
            if not self.json_commands_file.exists():
                return []
            
            command_data = self._load_json_file(self.json_commands_file)
            
            # Si no está procesado, devolverlo como lista
            if not command_data.get('procesado', False):
                return [command_data]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error obteniendo comandos pendientes: {e}")
            return []
    
    def mark_command_processed(self, command: Dict[str, Any]):
        """Marcar comando como procesado"""
        try:
            command['procesado'] = True
            command['procesado_timestamp'] = datetime.now().isoformat()
            
            self._save_json_file(self.json_commands_file, command)
            
        except Exception as e:
            self.logger.error(f"Error marcando comando como procesado: {e}")
    
    def _should_backup(self) -> bool:
        """Determinar si es necesario hacer respaldo"""
        return (datetime.now() - self.last_backup).total_seconds() > self.backup_interval
    
    def _perform_backup(self):
        """Realizar respaldo de archivos importantes"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Respaldar archivos principales
            files_to_backup = [
                (self.json_state_file, f"state_{timestamp}.json"),
                (self.excel_data_file, f"data_{timestamp}.xlsx")
            ]
            
            for source_file, backup_name in files_to_backup:
                if source_file.exists():
                    backup_path = self.backup_dir / backup_name
                    shutil.copy2(source_file, backup_path)
            
            # Limpiar respaldos antiguos (mantener últimos 10)
            self._cleanup_old_backups()
            
            self.last_backup = datetime.now()
            self.logger.info(f"Respaldo creado: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error creando respaldo: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Limpiar respaldos antiguos"""
        try:
            # Obtener todos los archivos de respaldo
            backup_files = list(self.backup_dir.glob("*_*.json")) + list(self.backup_dir.glob("*_*.xlsx"))
            
            # Ordenar por fecha de modificación (más recientes primero)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Eliminar los más antiguos
            for old_file in backup_files[keep_count:]:
                old_file.unlink()
            
        except Exception as e:
            self.logger.error(f"Error limpiando respaldos: {e}")
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Cargar archivo JSON con manejo de errores"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando JSON {file_path}: {e}")
            return {}
    
    def _save_json_file(self, file_path: Path, data: Dict[str, Any]):
        """Guardar archivo JSON con manejo de errores"""
        try:
            # Crear directorio si no existe
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Escribir con respaldo temporal
            temp_file = file_path.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Reemplazar archivo original
            temp_file.replace(file_path)
            
        except Exception as e:
            self.logger.error(f"Error guardando JSON {file_path}: {e}")
            raise
    
    def update_scanner_status(self, is_connected: bool):
        """Actualizar estado de conexión del escáner en el JSON"""
        try:
            # Cargar estado actual
            current_state = self._load_json_file(self.json_state_file)
            
            # Actualizar estado del escáner
            current_state['scanner_connected'] = is_connected
            current_state['timestamp'] = datetime.now().isoformat()
            
            # Guardar estado actualizado
            self._save_json_file(self.json_state_file, current_state)
            
            # Actualizar cache
            self.current_state = current_state
            
            self.logger.debug(f"Estado del escáner actualizado: {'conectado' if is_connected else 'desconectado'}")
            
        except Exception as e:
            self.logger.error(f"Error actualizando estado del escáner: {e}")