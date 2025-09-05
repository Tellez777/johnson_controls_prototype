#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBAS DE ESCENARIOS REALES
Johnson Controls - Sistema de Seguimiento Industrial

Pruebas específicas para validar escenarios de producción reales:
- Flujos completos de productos
- Manejo de errores de operadores
- Cambios de turnos
- Fallos de calidad
- Retrabajo de productos
"""

import sys
import os
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scanner_manager import ScannerManager
from src.models.product import JCIProduct, ProductStatus, StageStatus, QualityMetrics
from src.utils.logger import get_logger


class RealScenarioTester:
    """Probador de escenarios reales de producción"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.scanner_manager = ScannerManager()
        self.test_results = []
        
    def setup(self):
        """Configurar entorno de pruebas"""
        try:
            # Inicializar sistema
            if not self.scanner_manager.initialize():
                raise Exception("No se pudo inicializar el sistema")
                
            self.logger.info("Sistema inicializado para pruebas de escenarios reales")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configurando pruebas: {e}")
            return False
    
    def test_complete_production_flow(self):
        """Probar flujo completo de producción con productos reales"""
        print("\n=== PRUEBA: Flujo Completo de Producción ===")
        
        # Usar productos existentes del sistema
        sample_barcodes = ['fewygfyu3', 'fwe24gvfd', 'fdgffdwwd3']
        results = {}
        
        for barcode in sample_barcodes:
            if barcode in self.scanner_manager.products:
                product = self.scanner_manager.products[barcode]
                initial_status = product.status.value
                initial_stage = product.current_stage
                
                print(f"\nProcesando producto: {barcode}")
                print(f"  Estado inicial: {initial_status}")
                print(f"  Etapa inicial: {initial_stage}")
                
                # Resetear producto para empezar desde cero
                try:
                    self.scanner_manager.reset_product(barcode)
                    print(f"  Producto reseteado exitosamente")
                except Exception as e:
                    print(f"  Error reseteando producto: {e}")
                    continue
                
                # Procesar a través de todas las etapas disponibles
                stages_processed = 0
                start_time = time.time()
                
                while product.status != ProductStatus.COMPLETED and stages_processed < 10:  # Límite de seguridad
                    current_stage = product.current_stage
                    
                    # Simular escaneo
                    success = self.scanner_manager.simulate_scan(barcode)
                    
                    if success:
                        stages_processed += 1
                        new_stage = product.current_stage
                        print(f"    Etapa {current_stage} → {new_stage} ✓")
                        time.sleep(0.1)  # Simular tiempo real entre escaneos
                    else:
                        print(f"    Error procesando etapa {current_stage}")
                        break
                
                total_time = time.time() - start_time
                
                results[barcode] = {
                    'initial_status': initial_status,
                    'final_status': product.status.value,
                    'stages_processed': stages_processed,
                    'processing_time': round(total_time, 3),
                    'completed': product.status == ProductStatus.COMPLETED,
                    'progress': product.progress_percentage
                }
                
                print(f"  Estado final: {product.status.value}")
                print(f"  Etapas procesadas: {stages_processed}")
                print(f"  Tiempo total: {total_time:.3f}s")
                print(f"  Progreso: {product.progress_percentage:.1f}%")
        
        # Mostrar resumen
        print(f"\n--- RESUMEN DEL FLUJO COMPLETO ---")
        completed_count = sum(1 for r in results.values() if r['completed'])
        total_products = len(results)
        
        print(f"Productos completados: {completed_count}/{total_products}")
        
        for barcode, result in results.items():
            status_icon = "✓" if result['completed'] else "✗"
            print(f"  {status_icon} {barcode}: {result['final_status']} ({result['progress']:.1f}%)")
        
        return completed_count == total_products
    
    def test_operator_shift_change(self):
        """Probar cambio de turno de operadores"""
        print("\n=== PRUEBA: Cambio de Turno de Operadores ===")
        
        # Simular operadores de diferentes turnos
        morning_operators = {
            'OP-M001': {'name': 'Juan Pérez', 'shift': 'morning', 'skills': ['soldadura']},
            'OP-M002': {'name': 'María García', 'shift': 'morning', 'skills': ['pulido']}
        }
        
        afternoon_operators = {
            'OP-A001': {'name': 'Carlos López', 'shift': 'afternoon', 'skills': ['soldadura']},
            'OP-A002': {'name': 'Ana Martínez', 'shift': 'afternoon', 'skills': ['pulido']}
        }
        
        # Actualizar operadores en el sistema
        self.scanner_manager.data_sync.current_state['operadores'] = morning_operators
        
        test_barcode = 'ther4mosta7'
        if test_barcode not in self.scanner_manager.products:
            print(f"Producto {test_barcode} no encontrado")
            return False
        
        product = self.scanner_manager.products[test_barcode]
        
        # Procesar con turno de mañana
        print("Procesando con turno de mañana...")
        self.scanner_manager.reset_product(test_barcode)
        success1 = self.scanner_manager.simulate_scan(test_barcode)
        
        # Cambiar a turno de tarde
        print("Cambiando a turno de tarde...")
        self.scanner_manager.data_sync.current_state['operadores'] = afternoon_operators
        
        # Continuar procesamiento
        success2 = self.scanner_manager.simulate_scan(test_barcode)
        
        print(f"Procesamiento turno mañana: {'✓' if success1 else '✗'}")
        print(f"Procesamiento turno tarde: {'✓' if success2 else '✗'}")
        
        return success1 and success2
    
    def test_quality_failure_and_rework(self):
        """Probar falla de calidad y retrabajo"""
        print("\n=== PRUEBA: Falla de Calidad y Retrabajo ===")
        
        test_barcode = 'sens0r9air2'
        if test_barcode not in self.scanner_manager.products:
            print(f"Producto {test_barcode} no encontrado")
            return False
        
        product = self.scanner_manager.products[test_barcode]
        self.scanner_manager.reset_product(test_barcode)
        
        # Procesar hasta cierta etapa
        print("Procesando producto hasta etapa de calidad...")
        for _ in range(3):  # Procesar algunas etapas
            success = self.scanner_manager.simulate_scan(test_barcode)
            if not success:
                break
        
        current_stage = product.current_stage
        print(f"Producto en etapa: {current_stage}")
        
        # Simular falla de calidad manualmente
        if current_stage in product.stage_executions:
            stage_execution = product.stage_executions[current_stage]
            stage_execution.quality_metrics = QualityMetrics(
                quality_score=70.0,  # Calidad baja
                defect_count=3,
                passed_inspection=False
            )
            
            # Cambiar estado a retrabajo
            product.status = ProductStatus.REWORK
            print("Producto marcado para retrabajo debido a baja calidad")
        
        # Simular retrabajo (resetear etapa problemática)
        print("Iniciando proceso de retrabajo...")
        if current_stage in product.stage_executions:
            stage_execution = product.stage_executions[current_stage]
            stage_execution.status = StageStatus.NOT_STARTED
            stage_execution.start_time = None
            stage_execution.end_time = None
            product.status = ProductStatus.IN_PROGRESS
        
        # Reprocesar
        success = self.scanner_manager.simulate_scan(test_barcode)
        
        print(f"Retrabajo completado: {'✓' if success else '✗'}")
        print(f"Estado final: {product.status.value}")
        
        return success
    
    def test_concurrent_products_processing(self):
        """Probar procesamiento concurrente de múltiples productos"""
        print("\n=== PRUEBA: Procesamiento Concurrente ===")
        
        test_barcodes = ['act8uator5v', 'disp1ay4led', 'valve6flow3']
        available_products = []
        
        # Verificar productos disponibles
        for barcode in test_barcodes:
            if barcode in self.scanner_manager.products:
                available_products.append(barcode)
                self.scanner_manager.reset_product(barcode)
        
        if not available_products:
            print("No hay productos disponibles para la prueba")
            return False
        
        print(f"Procesando {len(available_products)} productos concurrentemente...")
        
        # Simular procesamiento concurrente
        max_iterations = 20
        iteration = 0
        products_completed = set()
        
        while iteration < max_iterations and len(products_completed) < len(available_products):
            # Seleccionar producto aleatorio para procesar
            active_products = [p for p in available_products if p not in products_completed]
            if not active_products:
                break
                
            current_barcode = random.choice(active_products)
            product = self.scanner_manager.products[current_barcode]
            
            # Procesar escaneo
            success = self.scanner_manager.simulate_scan(current_barcode)
            
            if success:
                print(f"  {current_barcode}: Etapa {product.current_stage} procesada")
                
                # Verificar si se completó
                if product.status == ProductStatus.COMPLETED:
                    products_completed.add(current_barcode)
                    print(f"  {current_barcode}: COMPLETADO ✓")
            
            iteration += 1
            time.sleep(0.05)  # Simular tiempo entre operaciones
        
        completion_rate = len(products_completed) / len(available_products) * 100
        print(f"\nProductos completados: {len(products_completed)}/{len(available_products)}")
        print(f"Tasa de completado: {completion_rate:.1f}%")
        print(f"Iteraciones utilizadas: {iteration}/{max_iterations}")
        
        return completion_rate >= 50  # Al menos 50% completado
    
    def test_system_state_persistence(self):
        """Probar persistencia del estado del sistema"""
        print("\n=== PRUEBA: Persistencia del Estado ===")
        
        # Obtener estado inicial
        initial_state = self.scanner_manager.get_system_status()
        initial_products_count = len(self.scanner_manager.products)
        
        print(f"Estado inicial - Productos: {initial_products_count}")
        print(f"Estado inicial - Ejecutándose: {initial_state['is_running']}")
        
        # Realizar algunas operaciones
        test_barcode = 'relay8power1'
        if test_barcode in self.scanner_manager.products:
            self.scanner_manager.reset_product(test_barcode)
            self.scanner_manager.simulate_scan(test_barcode)
        
        # Sincronizar estado
        self.scanner_manager.sync_system_state()
        
        # Verificar que el estado se mantenga
        current_state = self.scanner_manager.get_system_status()
        current_products_count = len(self.scanner_manager.products)
        
        print(f"Estado actual - Productos: {current_products_count}")
        print(f"Estado actual - Ejecutándose: {current_state['is_running']}")
        
        # Verificar consistencia
        products_consistent = initial_products_count <= current_products_count  # No deberían perderse productos
        state_consistent = current_state['is_running'] == initial_state['is_running']
        
        print(f"Consistencia de productos: {'✓' if products_consistent else '✗'}")
        print(f"Consistencia de estado: {'✓' if state_consistent else '✗'}")
        
        return products_consistent and state_consistent
    
    def test_error_recovery(self):
        """Probar recuperación ante errores"""
        print("\n=== PRUEBA: Recuperación ante Errores ===")
        
        error_scenarios = [
            ("Producto inexistente", "INVALID_BARCODE_999"),
            ("Código vacío", ""),
            ("Código con caracteres especiales", "TEST@#$%^&*()"),
        ]
        
        error_handled_count = 0
        
        for scenario_name, test_code in error_scenarios:
            print(f"\nProbando: {scenario_name}")
            try:
                success = self.scanner_manager.simulate_scan(test_code)
                
                if not success:  # Error manejado correctamente
                    print(f"  Error manejado correctamente ✓")
                    error_handled_count += 1
                else:  # No debería haber éxito con códigos inválidos
                    print(f"  Error: código inválido procesado exitosamente ✗")
                    
            except Exception as e:
                # Dependiendo del tipo de excepción, puede ser aceptable
                print(f"  Excepción capturada: {type(e).__name__} ✓")
                error_handled_count += 1
        
        # Verificar que el sistema sigue funcionando después de errores
        test_barcode = list(self.scanner_manager.products.keys())[0]
        recovery_success = self.scanner_manager.simulate_scan(test_barcode)
        
        print(f"\nRecuperación del sistema: {'✓' if recovery_success else '✗'}")
        print(f"Errores manejados: {error_handled_count}/{len(error_scenarios)}")
        
        return error_handled_count == len(error_scenarios) and recovery_success
    
    def run_all_real_scenarios(self):
        """Ejecutar todas las pruebas de escenarios reales"""
        print("INICIANDO PRUEBAS DE ESCENARIOS REALES")
        print("=" * 50)
        
        if not self.setup():
            print("ERROR: No se pudo configurar el entorno de pruebas")
            return
        
        tests = [
            ("Flujo Completo de Producción", self.test_complete_production_flow),
            ("Cambio de Turno de Operadores", self.test_operator_shift_change),
            ("Falla de Calidad y Retrabajo", self.test_quality_failure_and_rework),
            ("Procesamiento Concurrente", self.test_concurrent_products_processing),
            ("Persistencia del Estado", self.test_system_state_persistence),
            ("Recuperación ante Errores", self.test_error_recovery),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_function in tests:
            print(f"\n{'='*20}")
            print(f"EJECUTANDO: {test_name}")
            print(f"{'='*20}")
            
            start_time = time.time()
            try:
                result = test_function()
                execution_time = time.time() - start_time
                
                if result:
                    print(f"\n✓ {test_name} - PASÓ ({execution_time:.3f}s)")
                    passed_tests += 1
                else:
                    print(f"\n✗ {test_name} - FALLÓ ({execution_time:.3f}s)")
                    
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"\n✗ {test_name} - ERROR: {e} ({execution_time:.3f}s)")
        
        # Resumen final
        print(f"\n{'='*50}")
        print(f"RESUMEN DE PRUEBAS DE ESCENARIOS REALES")
        print(f"{'='*50}")
        print(f"Pruebas pasadas: {passed_tests}/{total_tests}")
        print(f"Tasa de éxito: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 TODAS LAS PRUEBAS DE ESCENARIOS REALES PASARON!")
        elif passed_tests >= total_tests * 0.8:
            print("\n⚠️ LA MAYORÍA DE PRUEBAS PASARON - Revisar fallos menores")
        else:
            print("\n❌ MÚLTIPLES FALLOS - Se requiere atención inmediata")
        
        return passed_tests / total_tests


def run_real_scenario_tests():
    """Función principal para ejecutar pruebas de escenarios reales"""
    tester = RealScenarioTester()
    return tester.run_all_real_scenarios()


if __name__ == "__main__":
    # Ejecutar pruebas de escenarios reales
    run_real_scenario_tests()