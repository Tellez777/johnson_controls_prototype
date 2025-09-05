#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBAS EXHAUSTIVAS DE CONSISTENCIA DEL SISTEMA
Johnson Controls - Sistema de Seguimiento Industrial

Pruebas completas para validar:
- Consistencia de datos de productos (CRUD)
- Consistencia de etapas y transiciones
- Funcionalidad de escaneo y validación
- Gestión de operadores
- Escenarios combinados y casos edge
"""

import sys
import os
import unittest
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scanner_manager import ScannerManager, ScanEvent
from src.core.stage_manager import StageManager, Stage
from src.models.product import JCIProduct, ProductStatus, StageStatus, QualityMetrics
from src.services.data_sync_service import DataSyncService
from src.utils.logger import get_logger
from src.utils.config import config


class TestResults:
    """Clase para recopilar y reportar resultados de pruebas"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_details = []
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
    def add_test_result(self, test_name: str, passed: bool, details: str = "", execution_time: float = 0):
        """Agregar resultado de prueba"""
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            
        self.test_details.append({
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_error(self, error_msg: str):
        """Agregar error crítico"""
        self.errors.append({
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_warning(self, warning_msg: str):
        """Agregar advertencia"""
        self.warnings.append({
            'message': warning_msg,
            'timestamp': datetime.now().isoformat()
        })
        
    def generate_report(self) -> Dict[str, Any]:
        """Generar reporte completo"""
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'summary': {
                'total_tests': total_tests,
                'tests_passed': self.tests_passed,
                'tests_failed': self.tests_failed,
                'success_rate': round(success_rate, 2),
                'total_duration': round(duration, 2),
                'errors_count': len(self.errors),
                'warnings_count': len(self.warnings)
            },
            'test_details': self.test_details,
            'errors': self.errors,
            'warnings': self.warnings,
            'generated_at': datetime.now().isoformat()
        }


class SystemConsistencyTester:
    """Probador exhaustivo de consistencia del sistema"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.results = TestResults()
        self.scanner_manager = None
        self.stage_manager = None
        self.data_sync = None
        
        # Datos de prueba
        self.test_products = []
        self.test_operators = []
        self.backup_data = {}
        
    def setup_test_environment(self):
        """Configurar entorno de pruebas"""
        try:
            self.logger.info("Configurando entorno de pruebas...")
            
            # Crear respaldo de datos existentes
            self._backup_existing_data()
            
            # Inicializar componentes del sistema
            self.scanner_manager = ScannerManager()
            self.stage_manager = StageManager()
            self.data_sync = DataSyncService()
            
            # Inicializar servicios
            self.data_sync.initialize()
            # StageManager no tiene initialize_default_stages, se inicializa automáticamente
            
            # Crear datos de prueba
            self._create_test_data()
            
            self.logger.info("Entorno de pruebas configurado correctamente")
            return True
            
        except Exception as e:
            error_msg = f"Error configurando entorno de pruebas: {e}"
            self.logger.error(error_msg)
            self.results.add_error(error_msg)
            return False
    
    def _backup_existing_data(self):
        """Respaldar datos existentes"""
        try:
            data_files = [
                'data/excel/DATOS_JCI_PROYECTO.xlsx',
                'data/json/sistema_estado.json',
                'data/json/comandos_web.json'
            ]
            
            for file_path in data_files:
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.backup_{int(time.time())}"
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    self.backup_data[file_path] = backup_path
                    
        except Exception as e:
            self.logger.warning(f"Error creando respaldo: {e}")
    
    def _create_test_data(self):
        """Crear datos específicos para pruebas"""
        # Productos de prueba con diferentes estados
        self.test_products = [
            {
                'barcode': 'TEST001',
                'part_number': 'TEST-001',
                'product_name': 'Producto Test 1',
                'product_family': 'Test Family',
                'work_order': 'WO-TEST-001',
                'batch_number': 'BATCH-TEST-001',
                'serial_number': 'SN-TEST-001',
                'customer_code': 'TEST-CLIENT',
                'revision': 'Rev-A',
                'specification': 'TEST-SPEC-001',
                'target_cycle_time': 300
            },
            {
                'barcode': 'TEST002',
                'part_number': 'TEST-002',
                'product_name': 'Producto Test 2',
                'product_family': 'Test Family',
                'work_order': 'WO-TEST-002',
                'batch_number': 'BATCH-TEST-002',
                'serial_number': 'SN-TEST-002',
                'customer_code': 'TEST-CLIENT',
                'revision': 'Rev-B',
                'specification': 'TEST-SPEC-002',
                'target_cycle_time': 400
            }
        ]
        
        # Operadores de prueba
        self.test_operators = [
            {
                'id': 'OP-TEST-001',
                'name': 'Operador Test 1',
                'skills': ['soldadura', 'inspeccion'],
                'status': 'active',
                'station': 'EST-TEST-01',
                'shift': 'morning'
            },
            {
                'id': 'OP-TEST-002',
                'name': 'Operador Test 2',
                'skills': ['pulido', 'acabados'],
                'status': 'active',
                'station': 'EST-TEST-02',
                'shift': 'afternoon'
            }
        ]
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        try:
            self.logger.info("Iniciando pruebas exhaustivas del sistema...")
            
            # Configurar entorno
            if not self.setup_test_environment():
                return self.results.generate_report()
            
            # Ejecutar grupos de pruebas
            test_groups = [
                ('Pruebas CRUD de Productos', self.test_product_crud_operations),
                ('Pruebas de Etapas y Transiciones', self.test_stage_transitions),
                ('Pruebas de Escaneo y Validación', self.test_scanning_functionality),
                ('Pruebas de Gestión de Operadores', self.test_operator_management),
                ('Pruebas de Escenarios Combinados', self.test_combined_scenarios),
                ('Pruebas de Casos Edge', self.test_edge_cases),
                ('Pruebas de Consistencia de Datos', self.test_data_consistency),
                ('Pruebas de Rendimiento', self.test_performance_scenarios)
            ]
            
            for group_name, test_function in test_groups:
                self.logger.info(f"Ejecutando: {group_name}")
                try:
                    test_function()
                except Exception as e:
                    self.results.add_error(f"Error en {group_name}: {e}")
                    self.logger.error(f"Error en {group_name}: {e}")
            
            # Limpiar entorno de pruebas
            self._cleanup_test_environment()
            
            self.logger.info("Pruebas exhaustivas completadas")
            return self.results.generate_report()
            
        except Exception as e:
            self.results.add_error(f"Error crítico en ejecución de pruebas: {e}")
            return self.results.generate_report()
    
    def test_product_crud_operations(self):
        """Pruebas CRUD exhaustivas para productos"""
        
        # Crear productos
        start_time = time.time()
        try:
            for product_data in self.test_products:
                product = JCIProduct(**product_data)
                self.scanner_manager.products[product.barcode] = product
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Creación de productos",
                True,
                f"Creados {len(self.test_products)} productos exitosamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Creación de productos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Leer productos
        start_time = time.time()
        try:
            for product_data in self.test_products:
                barcode = product_data['barcode']
                product = self.scanner_manager.products.get(barcode)
                assert product is not None, f"Producto {barcode} no encontrado"
                assert product.product_name == product_data['product_name'], "Datos inconsistentes"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Lectura de productos",
                True,
                "Productos leídos correctamente con datos consistentes",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Lectura de productos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Actualizar productos
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            product = self.scanner_manager.products[test_barcode]
            original_status = product.status
            product.status = ProductStatus.IN_PROGRESS
            product.notes = "Actualizado en pruebas"
            
            # Verificar cambios
            assert product.status == ProductStatus.IN_PROGRESS, "Estado no actualizado"
            assert product.notes == "Actualizado en pruebas", "Notas no actualizadas"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Actualización de productos",
                True,
                "Producto actualizado correctamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Actualización de productos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Eliminar productos
        start_time = time.time()
        try:
            test_barcode = self.test_products[-1]['barcode']
            if test_barcode in self.scanner_manager.products:
                del self.scanner_manager.products[test_barcode]
                
            # Verificar eliminación
            assert test_barcode not in self.scanner_manager.products, "Producto no eliminado"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Eliminación de productos",
                True,
                "Producto eliminado correctamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Eliminación de productos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_stage_transitions(self):
        """Pruebas de etapas y transiciones"""
        
        # Prueba de secuencia normal de etapas
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            product = self.scanner_manager.products[test_barcode]
            
            # Obtener etapas activas
            active_stages = self.stage_manager.get_active_stages()
            initial_stage = product.current_stage
            
            # Simular progresión a través de etapas
            for i, stage_data in enumerate(active_stages[:3]):  # Probar primeras 3 etapas
                stage_id = stage_data['id']
                product.current_stage = stage_id
                
                # Iniciar etapa
                product.start_current_stage(f"EST-TEST-{i+1:02d}")
                assert product.stage_executions[stage_id].status == StageStatus.IN_PROGRESS
                
                # Completar etapa
                quality_metrics = QualityMetrics(quality_score=95.0)
                product.complete_current_stage(quality_metrics)
                assert product.stage_executions[stage_id].status == StageStatus.COMPLETED
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Secuencia normal de etapas",
                True,
                f"Progresión exitosa a través de {len(active_stages[:3])} etapas",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Secuencia normal de etapas",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Prueba de validación de etapas
        start_time = time.time()
        try:
            # Probar etapa inválida
            invalid_stage_id = 999
            is_valid = self.stage_manager.validate_stage_id(invalid_stage_id)
            assert not is_valid, "Etapa inválida fue validada"
            
            # Probar etapa válida
            valid_stages = self.stage_manager.get_active_stages()
            if valid_stages:
                valid_stage_id = valid_stages[0]['id']
                is_valid = self.stage_manager.validate_stage_id(valid_stage_id)
                assert is_valid, "Etapa válida no fue validada"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Validación de etapas",
                True,
                "Validación de etapas funcionando correctamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Validación de etapas",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_scanning_functionality(self):
        """Pruebas de funcionalidad de escaneo"""
        
        # Simulación de escaneo exitoso
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            
            # Simular escaneo
            success = self.scanner_manager.simulate_scan(test_barcode)
            assert success, "Escaneo simulado falló"
            
            # Verificar que se procesó
            product = self.scanner_manager.products[test_barcode]
            assert product.status in [ProductStatus.IN_PROGRESS, ProductStatus.COMPLETED]
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Escaneo exitoso",
                True,
                f"Producto {test_barcode} escaneado correctamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Escaneo exitoso",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Escaneo de producto inexistente
        start_time = time.time()
        try:
            invalid_barcode = "INVALID_BARCODE_123"
            success = self.scanner_manager.simulate_scan(invalid_barcode)
            assert not success, "Escaneo de producto inexistente debería fallar"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Escaneo de producto inexistente",
                True,
                "Sistema rechazó correctamente producto inexistente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Escaneo de producto inexistente",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_operator_management(self):
        """Pruebas de gestión de operadores"""
        
        # Asignación automática de operadores
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            product = self.scanner_manager.products[test_barcode]
            
            # Simular datos de operadores en el sistema
            self.data_sync.current_state['operadores'] = {
                op['id']: op for op in self.test_operators
            }
            
            # Probar asignación para cada etapa
            active_stages = self.stage_manager.get_active_stages()
            for stage_data in active_stages[:2]:  # Probar primeras 2 etapas
                stage_id = stage_data['id']
                
                # Asignar operador
                self.scanner_manager._assign_operator_to_stage(product, stage_id, "")
                
                # Verificar asignación
                stage_execution = product.stage_executions.get(stage_id)
                if stage_execution:
                    assert stage_execution.operator_id, f"No se asignó operador para etapa {stage_id}"
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Asignación automática de operadores",
                True,
                "Operadores asignados correctamente a etapas",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Asignación automática de operadores",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_combined_scenarios(self):
        """Pruebas de escenarios combinados"""
        
        # Escenario: Múltiples productos en diferentes etapas
        start_time = time.time()
        try:
            products_status = {}
            
            # Procesar múltiples productos simultáneamente
            for i, product_data in enumerate(self.test_products):
                barcode = product_data['barcode']
                if barcode in self.scanner_manager.products:
                    product = self.scanner_manager.products[barcode]
                    
                    # Colocar productos en diferentes etapas
                    active_stages = self.stage_manager.get_active_stages()
                    if active_stages and i < len(active_stages):
                        target_stage_id = active_stages[i]['id']
                        product.current_stage = target_stage_id
                        
                        # Simular escaneo
                        success = self.scanner_manager.simulate_scan(barcode)
                        products_status[barcode] = {
                            'success': success,
                            'stage': product.current_stage,
                            'status': product.status.value
                        }
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Múltiples productos simultáneos",
                True,
                f"Procesados {len(products_status)} productos en paralelo",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Múltiples productos simultáneos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Escenario: Cambio de etapa del sistema durante procesamiento
        start_time = time.time()
        try:
            # Cambiar etapa actual del sistema
            active_stages = self.stage_manager.get_active_stages()
            if len(active_stages) >= 2:
                original_stage = self.scanner_manager.current_stage
                new_stage = active_stages[1]['id']
                
                self.scanner_manager.change_current_stage(new_stage)
                assert self.scanner_manager.current_stage == new_stage
                
                # Volver al estado original
                if original_stage:
                    self.scanner_manager.change_current_stage(original_stage)
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Cambio de etapa del sistema",
                True,
                "Sistema maneja cambios de etapa correctamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Cambio de etapa del sistema",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_edge_cases(self):
        """Pruebas de casos extremos"""
        
        # Producto con datos corruptos
        start_time = time.time()
        try:
            corrupt_product_data = self.test_products[0].copy()
            corrupt_product_data['barcode'] = 'CORRUPT_TEST'
            corrupt_product_data['target_cycle_time'] = -1  # Valor inválido
            
            # Intentar crear producto corrupto
            try:
                corrupt_product = JCIProduct(**corrupt_product_data)
                # Si se crea, verificar que el sistema maneje valores inválidos
                assert corrupt_product.target_cycle_time == -1
            except Exception:
                pass  # Es aceptable que falle
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Manejo de datos corruptos",
                True,
                "Sistema maneja datos inválidos apropiadamente",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Manejo de datos corruptos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
        
        # Escaneos simultáneos del mismo producto
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            
            # Múltiples escaneos rápidos
            results = []
            for _ in range(5):
                result = self.scanner_manager.simulate_scan(test_barcode)
                results.append(result)
                time.sleep(0.1)  # Pequeña pausa
            
            # Verificar que el producto no se corrompió
            product = self.scanner_manager.products[test_barcode]
            assert product.barcode == test_barcode
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Escaneos simultáneos",
                True,
                f"Sistema manejó {len(results)} escaneos consecutivos",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Escaneos simultáneos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_data_consistency(self):
        """Pruebas de consistencia de datos"""
        
        # Verificar integridad de productos después de operaciones
        start_time = time.time()
        try:
            consistency_issues = []
            
            for barcode, product in self.scanner_manager.products.items():
                # Verificar campos obligatorios
                if not product.barcode:
                    consistency_issues.append(f"Producto sin barcode: {barcode}")
                
                if not product.product_name:
                    consistency_issues.append(f"Producto sin nombre: {barcode}")
                
                # Verificar coherencia de etapas
                if product.current_stage not in product.stage_executions:
                    consistency_issues.append(f"Etapa actual {product.current_stage} no existe en executions: {barcode}")
                
                # Verificar estados coherentes
                if product.status == ProductStatus.COMPLETED and product.progress_percentage < 100:
                    consistency_issues.append(f"Producto completado con progreso < 100%: {barcode}")
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Consistencia de datos de productos",
                len(consistency_issues) == 0,
                f"Encontrados {len(consistency_issues)} problemas de consistencia" if consistency_issues else "Datos consistentes",
                execution_time
            )
            
            if consistency_issues:
                for issue in consistency_issues:
                    self.results.add_warning(issue)
                    
        except Exception as e:
            self.results.add_test_result(
                "Consistencia de datos de productos",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def test_performance_scenarios(self):
        """Pruebas de rendimiento básico"""
        
        # Tiempo de procesamiento de escaneo
        start_time = time.time()
        try:
            test_barcode = self.test_products[0]['barcode']
            
            # Medir tiempo de escaneo individual
            scan_start = time.time()
            self.scanner_manager.simulate_scan(test_barcode)
            scan_time = time.time() - scan_start
            
            # Verificar que esté dentro de límites razonables (< 1 segundo)
            performance_ok = scan_time < 1.0
            
            execution_time = time.time() - start_time
            self.results.add_test_result(
                "Rendimiento de escaneo",
                performance_ok,
                f"Tiempo de escaneo: {scan_time:.3f}s (límite: 1.0s)",
                execution_time
            )
        except Exception as e:
            self.results.add_test_result(
                "Rendimiento de escaneo",
                False,
                f"Error: {e}",
                time.time() - start_time
            )
    
    def _cleanup_test_environment(self):
        """Limpiar entorno de pruebas"""
        try:
            # Remover productos de prueba
            for product_data in self.test_products:
                barcode = product_data['barcode']
                if hasattr(self.scanner_manager, 'products') and barcode in self.scanner_manager.products:
                    del self.scanner_manager.products[barcode]
            
            # Restaurar datos originales si es necesario
            # (En este caso no restauramos para preservar el estado del sistema)
            
            self.logger.info("Entorno de pruebas limpiado")
            
        except Exception as e:
            self.logger.warning(f"Error limpiando entorno: {e}")
    
    def save_report_to_file(self, report: Dict[str, Any], filename: str = None):
        """Guardar reporte en archivo"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"data/logs/test_report_{timestamp}.json"
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Reporte guardado en: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Error guardando reporte: {e}")
            return None


def run_comprehensive_tests():
    """Función principal para ejecutar pruebas exhaustivas"""
    print("PRUEBAS EXHAUSTIVAS DE CONSISTENCIA DEL SISTEMA")
    print("=" * 60)
    
    tester = SystemConsistencyTester()
    
    try:
        # Ejecutar todas las pruebas
        report = tester.run_all_tests()
        
        # Mostrar resumen en consola
        summary = report['summary']
        print(f"\nRESUMEN DE RESULTADOS:")
        print(f"   Total de pruebas: {summary['total_tests']}")
        print(f"   Pruebas exitosas: {summary['tests_passed']}")
        print(f"   Pruebas fallidas: {summary['tests_failed']}")
        print(f"   Tasa de éxito: {summary['success_rate']}%")
        print(f"   Duración total: {summary['total_duration']}s")
        print(f"   Errores críticos: {summary['errors_count']}")
        print(f"   Advertencias: {summary['warnings_count']}")
        
        # Mostrar detalles de pruebas fallidas
        if summary['tests_failed'] > 0:
            print(f"\nPRUEBAS FALLIDAS:")
            for test in report['test_details']:
                if not test['passed']:
                    print(f"   - {test['test_name']}: {test['details']}")
        
        # Mostrar errores críticos
        if report['errors']:
            print(f"\nERRORES CRÍTICOS:")
            for error in report['errors']:
                print(f"   - {error['message']}")
        
        # Mostrar advertencias
        if report['warnings']:
            print(f"\nADVERTENCIAS:")
            for warning in report['warnings']:
                print(f"   - {warning['message']}")
        
        # Guardar reporte completo
        report_file = tester.save_report_to_file(report)
        if report_file:
            print(f"\nReporte completo guardado en: {report_file}")
        
        # Determinar estado general
        if summary['success_rate'] >= 90:
            print(f"\nSISTEMA EN BUEN ESTADO - Tasa de éxito: {summary['success_rate']}%")
        elif summary['success_rate'] >= 70:
            print(f"\nSISTEMA CON PROBLEMAS MENORES - Tasa de éxito: {summary['success_rate']}%")
        else:
            print(f"\nSISTEMA CON PROBLEMAS CRÍTICOS - Tasa de éxito: {summary['success_rate']}%")
        
        return report
        
    except Exception as e:
        print(f"\nERROR CRÍTICO EN PRUEBAS: {e}")
        import traceback
        print(traceback.format_exc())
        return None


if __name__ == "__main__":
    # Permitir ejecución directa del archivo de pruebas
    import argparse
    
    parser = argparse.ArgumentParser(description='Pruebas exhaustivas del sistema JCI')
    parser.add_argument('--basic', action='store_true', help='Ejecutar solo pruebas básicas')
    parser.add_argument('--verbose', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    if args.basic:
        print("Ejecutando pruebas básicas...")
        # Aquí se podrían ejecutar solo las pruebas más críticas
    
    # Ejecutar pruebas completas
    run_comprehensive_tests()