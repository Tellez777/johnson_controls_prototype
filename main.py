#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JOHNSON CONTROLS - Sistema de Seguimiento Industrial
Punto de entrada principal del sistema modular
"""

import sys
import os
import argparse
import signal
import time
from pathlib import Path

# Agregar src al path para imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.utils.config import config, ConfigManager
from src.utils.logger import setup_logging, get_logger
from src.core.scanner_manager import ScannerManager
from src.web.app import WebApplication
from src.services.analytics_service import AnalyticsService


class JohnsonControlsSystem:
    """Sistema principal de Johnson Controls"""
    
    def __init__(self, args):
        self.args = args
        self.logger = None
        self.scanner_manager = None
        self.web_app = None
        self.analytics_service = None
        self.running = False
        
        # Configurar logging
        setup_logging(level=args.log_level if hasattr(args, 'log_level') else 'INFO')
        self.logger = get_logger(__name__)
        
        self.logger.info("="*60)
        self.logger.info("JOHNSON CONTROLS - Sistema de Seguimiento Industrial")
        self.logger.info("Version 2.0 - Arquitectura Modular")
        self.logger.info("="*60)
    
    def initialize(self) -> bool:
        """Inicializar sistema completo"""
        try:
            self.logger.info("Inicializando sistema...")
            
            # Validar configuración
            if not config.validate_config():
                self.logger.error("Configuración inválida")
                return False
            
            # Mostrar información de configuración
            self._show_config_info()
            
            # Crear directorios necesarios
            self._ensure_directories()
            
            # Inicializar servicios según argumentos
            if self.args.mode in ['full', 'scanner']:
                self.scanner_manager = ScannerManager()
                if not self.scanner_manager.initialize():
                    self.logger.error("Error inicializando scanner manager")
                    return False
            
            if self.args.mode in ['full', 'web']:
                self.web_app = WebApplication()
                if not self.web_app.initialize():
                    self.logger.error("Error inicializando aplicación web")
                    return False
            
            if self.args.mode in ['full', 'analytics']:
                self.analytics_service = AnalyticsService()
                if not self.analytics_service.initialize():
                    self.logger.error("Error inicializando servicio de analytics")
                    return False
            
            self.logger.info("Sistema inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en inicialización: {e}")
            return False
    
    def _show_config_info(self):
        """Mostrar información de configuración"""
        plant_info = config.get_plant_info()
        
        self.logger.info(f"Planta: {plant_info['plant_name']} ({plant_info['plant_id']})")
        self.logger.info(f"Departamento: {plant_info['department']}")
        self.logger.info(f"Ambiente: {config.system.environment}")
        self.logger.info(f"Puerto Serie: {config.hardware.serial_port}")
        self.logger.info(f"Puerto Web: {config.web.port}")
        self.logger.info(f"Modo: {self.args.mode}")
    
    def _ensure_directories(self):
        """Crear directorios necesarios"""
        directories = [
            "data/excel",
            "data/json", 
            "data/logs",
            "data/backup",
            "config"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Directorios verificados/creados")
    
    def run(self):
        """Ejecutar sistema principal"""
        try:
            self.running = True
            
            # Configurar manejo de señales
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.logger.info(f"Iniciando sistema en modo: {self.args.mode}")
            
            # Iniciar servicios
            if self.scanner_manager:
                self.logger.info("Scanner Manager: Activo")
            
            if self.web_app:
                self.web_app.start()
                self.logger.info(f"Aplicación Web: http://localhost:{config.web.port}")
            
            if self.analytics_service:
                self.analytics_service.start()
                self.logger.info("Servicio de Analytics: Activo")
            
            # Mostrar información de control
            self._show_control_info()
            
            # Bucle principal
            if self.args.mode == 'full':
                self._run_full_system()
            elif self.args.mode == 'scanner':
                self._run_scanner_only()
            elif self.args.mode == 'web':
                self._run_web_only()
            elif self.args.mode == 'console':
                self._run_console_mode()
            
        except KeyboardInterrupt:
            self.logger.info("Interrupción por teclado detectada")
        except Exception as e:
            self.logger.error(f"Error en ejecución: {e}")
        finally:
            self.shutdown()
    
    def _run_full_system(self):
        """Ejecutar sistema completo"""
        self.logger.info("Sistema completo en ejecución...")
        self.logger.info("Presiona Ctrl+C para detener")
        
        try:
            while self.running:
                # Monitoreo básico del sistema
                if self.scanner_manager:
                    status = self.scanner_manager.get_system_status()
                    if not status['is_running']:
                        self.logger.warning("Scanner Manager se detuvo inesperadamente")
                
                time.sleep(5)  # Verificar cada 5 segundos
                
        except KeyboardInterrupt:
            pass
    
    def _run_scanner_only(self):
        """Ejecutar solo el sistema de escaneo"""
        self.logger.info("Sistema de escaneo en ejecución...")
        
        # Mostrar menú de consola para control
        self._console_menu()
    
    def _run_web_only(self):
        """Ejecutar solo el servidor web"""
        self.logger.info("Servidor web en ejecución...")
        self.logger.info("El servidor web se ejecuta en segundo plano")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def _run_console_mode(self):
        """Ejecutar en modo consola interactiva"""
        self.logger.info("Modo consola interactiva")
        self._console_menu()
    
    def _console_menu(self):
        """Menú de consola interactiva"""
        while self.running:
            try:
                print(f"\n{'='*60}")
                print("JOHNSON CONTROLS - Sistema de Seguimiento")
                print(f"{'='*60}")
                
                if self.scanner_manager:
                    status = self.scanner_manager.get_system_status()
                    products = self.scanner_manager.get_products_summary()
                    
                    print(f"Estado del Sistema: {'🟢 Activo' if status['is_running'] else '🔴 Inactivo'}")
                    print(f"Etapa Actual: {status['current_stage']}")
                    print(f"Escáner: {'🟢 Conectado' if status['scanner_connected'] else '🔴 Desconectado'}")
                    print(f"Productos: {products['total']} | Completados: {products['completed']} | En Proceso: {products['in_progress']}")
                
                print("\nOpciones disponibles:")
                print("1-6: Cambiar etapa (1=Soldadura, 2=Pulido, 3=Presión, 4=Calidad, 5=Pintura, 6=Almacén)")
                print("s:   Simular escaneo")
                print("e:   Ver estadísticas detalladas")
                print("r:   Resetear producto")
                print("c:   Configuración")
                print("l:   Ver logs recientes")
                print("q:   Salir")
                
                opcion = input("\nOpción: ").strip().lower()
                
                if opcion in ['1', '2', '3', '4', '5', '6']:
                    if self.scanner_manager:
                        self.scanner_manager.change_current_stage(int(opcion))
                        print(f"✅ Cambiado a etapa {opcion}")
                
                elif opcion == 's':
                    self._simulate_scan_menu()
                
                elif opcion == 'e':
                    self._show_detailed_stats()
                
                elif opcion == 'r':
                    self._reset_product_menu()
                
                elif opcion == 'c':
                    self._config_menu()
                
                elif opcion == 'l':
                    self._show_recent_logs()
                
                elif opcion == 'q':
                    break
                
                else:
                    print("❌ Opción no válida")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _simulate_scan_menu(self):
        """Menú para simular escaneos"""
        if not self.scanner_manager:
            print("❌ Scanner Manager no disponible")
            return
        
        print("\nProductos disponibles:")
        for i, (barcode, product) in enumerate(self.scanner_manager.products.items(), 1):
            status_icon = "🟢" if product.status.value == "Completado" else "🟡" if product.status.value == "En Proceso" else "🔴"
            print(f"{i}. {barcode} - {product.product_name} {status_icon}")
        
        try:
            seleccion = input("Selecciona producto (número o código): ").strip()
            
            if seleccion.isdigit():
                productos = list(self.scanner_manager.products.keys())
                if 1 <= int(seleccion) <= len(productos):
                    barcode = productos[int(seleccion) - 1]
                else:
                    print("❌ Número inválido")
                    return
            else:
                barcode = seleccion.upper()
            
            if self.scanner_manager.simulate_scan(barcode):
                print(f"✅ Escaneo simulado exitosamente: {barcode}")
            else:
                print(f"❌ Error en simulación: {barcode}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def _show_detailed_stats(self):
        """Mostrar estadísticas detalladas"""
        if not self.scanner_manager:
            print("❌ Scanner Manager no disponible")
            return
        
        print(f"\n{'='*60}")
        print("ESTADÍSTICAS DETALLADAS")
        print(f"{'='*60}")
        
        # Estadísticas de sesión
        stats = self.scanner_manager.session_stats
        print(f"Inicio de sesión: {stats['start_time']}")
        print(f"Escaneos procesados: {stats['scans_processed']}")
        print(f"Errores: {stats['errors_count']}")
        print(f"Productos completados: {stats['products_completed']}")
        
        # Estadísticas por producto
        print(f"\n{'Producto':<20} {'Estado':<15} {'Progreso':<10} {'Calidad':<8}")
        print("-" * 60)
        
        for product in self.scanner_manager.products.values():
            print(f"{product.barcode:<20} {product.status.value:<15} {product.progress_percentage:<10.1f} {product.quality_score:<8.1f}")
    
    def _reset_product_menu(self):
        """Menú para resetear productos"""
        if not self.scanner_manager:
            print("❌ Scanner Manager no disponible")
            return
        
        print("\nProductos para resetear:")
        for i, (barcode, product) in enumerate(self.scanner_manager.products.items(), 1):
            print(f"{i}. {barcode} - {product.product_name} ({product.status.value})")
        
        try:
            seleccion = input("Selecciona producto: ").strip()
            
            if seleccion.isdigit():
                productos = list(self.scanner_manager.products.keys())
                if 1 <= int(seleccion) <= len(productos):
                    barcode = productos[int(seleccion) - 1]
                    self.scanner_manager.reset_product(barcode)
                    print(f"✅ Producto reseteado: {barcode}")
                else:
                    print("❌ Número inválido")
            else:
                print("❌ Selección inválida")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def _config_menu(self):
        """Menú de configuración"""
        print(f"\n{'='*40}")
        print("CONFIGURACIÓN ACTUAL")
        print(f"{'='*40}")
        
        print(f"Ambiente: {config.system.environment}")
        print(f"Puerto Serie: {config.hardware.serial_port}")
        print(f"Puerto Web: {config.web.port}")
        print(f"Nivel de Log: {config.system.log_level}")
        print(f"Debug: {config.system.log_level == 'DEBUG'}")
        
        # Aquí se podría agregar funcionalidad para cambiar configuración
    
    def _show_recent_logs(self):
        """Mostrar logs recientes (funcionalidad simplificada)"""
        print("📋 Últimos eventos del sistema:")
        print("(Esta funcionalidad se implementaría leyendo archivos de log)")
    
    def _show_control_info(self):
        """Mostrar información de control"""
        print(f"\n{'='*60}")
        print("INFORMACIÓN DE CONTROL")
        print(f"{'='*60}")
        
        if self.args.mode in ['full', 'console', 'scanner']:
            print("🎮 Controles disponibles:")
            print("  - Consola interactiva para gestión")
            print("  - Simulación de escaneos")
            print("  - Control de etapas")
        
        if self.args.mode in ['full', 'web']:
            print(f"🌐 Interfaz Web: http://localhost:{config.web.port}")
            print("  - Dashboard ejecutivo en tiempo real")
            print("  - Control remoto del sistema")
            print("  - Analytics y reportes")
        
        print(f"📊 Archivos de datos:")
        print(f"  - Estado: {config.get_json_path('state')}")
        print(f"  - Excel: {config.get_excel_path('data')}")
        
        print("⚠️  Para detener el sistema: Ctrl+C")
    
    def _signal_handler(self, signum, frame):
        """Manejar señales del sistema"""
        self.logger.info(f"Señal recibida: {signum}")
        self.running = False
    
    def shutdown(self):
        """Apagar sistema ordenadamente"""
        self.logger.info("Iniciando apagado del sistema...")
        
        self.running = False
        
        # Apagar servicios en orden
        if self.scanner_manager:
            self.scanner_manager.shutdown()
            self.logger.info("Scanner Manager detenido")
        
        if self.analytics_service:
            self.analytics_service.stop()
            self.logger.info("Servicio de Analytics detenido")
        
        if self.web_app:
            self.web_app.stop()
            self.logger.info("Aplicación Web detenida")
        
        self.logger.info("Sistema apagado correctamente")
        self.logger.info("="*60)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Johnson Controls - Sistema de Seguimiento Industrial"
    )
    
    parser.add_argument(
        '--mode', 
        choices=['full', 'scanner', 'web', 'console', 'analytics'],
        default='full',
        help='Modo de ejecución del sistema'
    )
    
    parser.add_argument(
        '--config',
        default='development',
        help='Archivo de configuración a usar'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Nivel de logging'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Puerto para servidor web (sobrescribe configuración)'
    )
    
    args = parser.parse_args()
    
    # Configurar ambiente
    os.environ['JCI_ENV'] = args.config
    
    # Sobrescribir puerto si se especifica
    if args.port:
        from src.utils.config import config
        config.web.port = args.port
    
    # Crear y ejecutar sistema
    system = JohnsonControlsSystem(args)
    
    if system.initialize():
        system.run()
    else:
        print("❌ Error en la inicialización del sistema")
        sys.exit(1)


if __name__ == "__main__":
    main()