#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAFE MAIN - Versión robusta del sistema principal con manejo de errores
Johnson Controls - Sistema de Seguimiento Industrial
"""

import sys
import os
import argparse
import logging
from pathlib import Path


# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_and_setup_environment():
    """Verificar y configurar el ambiente"""
    print("🔍 Verificando ambiente del sistema...")
    
    # Verificar estructura mínima
    required_dirs = ['src', 'config', 'data']
    missing_dirs = []
    
    for directory in required_dirs:
        if not Path(directory).exists():
            missing_dirs.append(directory)
    
    if missing_dirs:
        print(f"❌ Directorios faltantes: {missing_dirs}")
        print("💡 Ejecuta: python setup_project.py")
        return False
    
    # Agregar src al path si no está
    src_path = str(Path(__file__).parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    print("✅ Ambiente configurado correctamente")
    return True


def safe_import(module_name, class_name=None):
    """Importar módulo de forma segura"""
    try:
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(module, class_name)
        return module
    except ImportError as e:
        logger.warning(f"No se pudo importar {module_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error importando {module_name}: {e}")
        return None


class SafeJohnsonControlsSystem:
    """Sistema Johnson Controls con manejo robusto de errores"""
    
    def __init__(self, args):
        self.args = args
        self.components = {}
        self.running = False
        
        # Intentar importar componentes
        self._import_components()
    
    def _import_components(self):
        """Importar componentes del sistema de forma segura"""
        print("📦 Cargando componentes del sistema...")
        
        # Importaciones core
        config_module = safe_import('src.utils.config')
        if config_module:
            self.components['config'] = getattr(config_module, 'config', None)
            print("✅ Configuración cargada")
        else:
            print("⚠️  Configuración no disponible - usando valores por defecto")
        
        # Logger
        logger_module = safe_import('src.utils.logger')
        if logger_module:
            setup_logging = getattr(logger_module, 'setup_logging', None)
            if setup_logging:
                setup_logging(level=self.args.log_level)
            print("✅ Sistema de logging configurado")
        else:
            print("⚠️  Logger avanzado no disponible - usando logging básico")
        
        # Scanner Manager
        scanner_manager_cls = safe_import('src.core.scanner_manager', 'ScannerManager')
        if scanner_manager_cls:
            self.components['scanner_manager'] = scanner_manager_cls
            print("✅ Scanner Manager disponible")
        else:
            print("⚠️  Scanner Manager no disponible")
        
        # Web Application
        web_app_cls = safe_import('src.web.app', 'WebApplication')
        if web_app_cls:
            self.components['web_app'] = web_app_cls
            print("✅ Web Application disponible")
        else:
            print("⚠️  Web Application no disponible")
        
        # Analytics Service
        analytics_cls = safe_import('src.services.analytics_service', 'AnalyticsService')
        if analytics_cls:
            self.components['analytics'] = analytics_cls
            print("✅ Analytics Service disponible")
        else:
            print("⚠️  Analytics Service no disponible")
    
    def run_web_mode(self):
        """Ejecutar en modo web"""
        print("🌐 Iniciando modo web...")
        
        web_app_cls = self.components.get('web_app')
        if web_app_cls:
            try:
                web_app = web_app_cls()
                if web_app.initialize():
                    print("✅ Aplicación web inicializada")
                    web_app.start()
                    print("🚀 Servidor web activo")
                    self._keep_running()
                else:
                    print("❌ Error inicializando aplicación web")
            except Exception as e:
                print(f"❌ Error en modo web: {e}")
                logger.error(f"Error web: {e}")
        else:
            # Fallback a servidor Flask básico
            print("🔄 Usando servidor web básico...")
            self._run_basic_web()
    
    def run_scanner_mode(self):
        """Ejecutar en modo scanner"""
        print("📱 Iniciando modo scanner...")
        
        scanner_cls = self.components.get('scanner_manager')
        if scanner_cls:
            try:
                scanner = scanner_cls()
                if scanner.initialize():
                    print("✅ Scanner inicializado")
                    print("📡 Sistema de escaneo activo")
                    self._scanner_console_loop()
                else:
                    print("❌ Error inicializando scanner")
            except Exception as e:
                print(f"❌ Error en modo scanner: {e}")
                logger.error(f"Error scanner: {e}")
        else:
            print("❌ Scanner Manager no disponible")
            print("💡 Ejecuta: python setup_project.py")
    
    def run_full_mode(self):
        """Ejecutar sistema completo"""
        print("🏭 Iniciando sistema completo...")
        
        initialized = []
        
        # Inicializar scanner si está disponible
        if 'scanner_manager' in self.components:
            try:
                scanner = self.components['scanner_manager']()
                if scanner.initialize():
                    initialized.append('scanner')
                    print("✅ Scanner Manager inicializado")
            except Exception as e:
                print(f"⚠️  Scanner no inicializado: {e}")
        
        # Inicializar web
        if 'web_app' in self.components:
            try:
                web_app = self.components['web_app']()
                if web_app.initialize():
                    web_app.start()
                    initialized.append('web')
                    print("✅ Web Application inicializada")
            except Exception as e:
                print(f"⚠️  Web app no inicializada: {e}")
        
        # Inicializar analytics si está disponible
        if 'analytics' in self.components:
            try:
                analytics = self.components['analytics']()
                if analytics.initialize():
                    analytics.start()
                    initialized.append('analytics')
                    print("✅ Analytics Service inicializado")
            except Exception as e:
                print(f"⚠️  Analytics no inicializado: {e}")
        
        if initialized:
            print(f"🎉 Sistema iniciado con componentes: {', '.join(initialized)}")
            if 'web' in initialized:
                config = self.components.get('config')
                port = getattr(config.web, 'port', 5000) if config else 5000
                print(f"🌐 Dashboard disponible en: http://localhost:{port}")
            self._keep_running()
        else:
            print("❌ No se pudo inicializar ningún componente")
            self._run_basic_web()
    
    def run_console_mode(self):
        """Ejecutar en modo consola"""
        print("💻 Modo consola interactiva")
        
        while True:
            try:
                print("\n" + "="*50)
                print("JOHNSON CONTROLS - CONSOLA DE CONTROL")
                print("="*50)
                print("Componentes disponibles:")
                
                for component, status in self.components.items():
                    status_icon = "✅" if status else "❌"
                    print(f"  {status_icon} {component}")
                
                print("\nOpciones:")
                print("1. Iniciar servidor web")
                print("2. Probar conexión de escáner")  
                print("3. Ver configuración")
                print("4. Ejecutar diagnósticos")
                print("5. Salir")
                
                choice = input("\nSelecciona opción (1-5): ").strip()
                
                if choice == '1':
                    self.run_web_mode()
                elif choice == '2':
                    self._test_scanner()
                elif choice == '3':
                    self._show_config()
                elif choice == '4':
                    self._run_diagnostics()
                elif choice == '5':
                    break
                else:
                    print("❌ Opción inválida")
                    
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _run_basic_web(self):
        """Ejecutar servidor web básico como fallback"""
        try:
            from flask import Flask, jsonify, render_template_string
            
            app = Flask(__name__)
            
            @app.route('/')
            def dashboard():
                return render_template_string(self._get_basic_template())
            
            @app.route('/api/status')
            def status():
                return jsonify({
                    'status': 'running',
                    'mode': 'basic',
                    'system': 'Johnson Controls',
                    'components': list(self.components.keys()),
                    'message': 'Sistema funcionando en modo básico'
                })
            
            print("🔄 Servidor web básico iniciado")
            print("🌐 Disponible en: http://localhost:5000")
            print("⚡ Presiona Ctrl+C para detener")
            
            app.run(host='0.0.0.0', port=5000, debug=False)
            
        except Exception as e:
            print(f"❌ Error iniciando servidor básico: {e}")
    
    def _get_basic_template(self):
        """Template básico HTML"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Johnson Controls - Sistema de Seguimiento</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #003D79, #0066CC); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
                .header h1 { margin: 0; font-size: 2.5em; }
                .header p { margin: 10px 0 0; opacity: 0.9; }
                .card { background: white; padding: 25px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .status { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #e8f5e8; border-left: 4px solid #4CAF50; margin: 15px 0; border-radius: 4px; }
                .button { background: #0066CC; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; margin: 5px; text-decoration: none; display: inline-block; }
                .button:hover { background: #003D79; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
                .metric { text-align: center; }
                .metric-value { font-size: 2.5em; font-weight: bold; color: #0066CC; }
                .metric-label { color: #666; margin-top: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏭 Johnson Controls</h1>
                    <p>Sistema de Seguimiento Industrial - Planta Durango</p>
                </div>
                
                <div class="status">
                    <div><strong>✅ Estado del Sistema:</strong> Operativo (Modo Básico)</div>
                    <div><strong>⏰ Tiempo:</strong> <span id="current-time"></span></div>
                </div>
                
                <div class="grid">
                    <div class="card metric">
                        <div class="metric-value">🔧</div>
                        <div class="metric-label">Sistema Modular</div>
                    </div>
                    <div class="card metric">
                        <div class="metric-value">📱</div>
                        <div class="metric-label">Zebra DS3678</div>
                    </div>
                    <div class="card metric">
                        <div class="metric-value">📊</div>
                        <div class="metric-label">Analytics Avanzados</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🚀 Sistema Inicializado</h3>
                    <p>El sistema básico está funcionando correctamente. Para acceder a todas las funcionalidades:</p>
                    <ol>
                        <li><strong>Configurar sistema completo:</strong> <code>python setup_project.py</code></li>
                        <li><strong>Instalar dependencias:</strong> <code>pip install -r requirements.txt</code></li>
                        <li><strong>Ejecutar sistema completo:</strong> <code>python main.py --mode full</code></li>
                    </ol>
                    
                    <div style="margin-top: 20px;">
                        <a href="/api/status" class="button">📊 Ver Estado API</a>
                        <button class="button" onclick="location.reload()">🔄 Actualizar</button>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📋 Componentes del Sistema</h3>
                    <ul>
                        <li>✅ Servidor Web Básico</li>
                        <li>🔄 Sistema de Escaneo (Pendiente configuración)</li>
                        <li>📊 Dashboard Ejecutivo (Versión completa)</li>
                        <li>📈 Analytics y Reportes (Disponible en versión completa)</li>
                    </ul>
                </div>
            </div>
            
            <script>
                function updateTime() {
                    document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
                }
                updateTime();
                setInterval(updateTime, 1000);
            </script>
        </body>
        </html>
        '''
    
    def _test_scanner(self):
        """Probar conexión del escáner"""
        print("\n📱 Probando conexión del escáner...")
        try:
            # Intentar importar y probar scanner
            scanner_module = safe_import('src.hardware.zebra_scanner')
            if scanner_module:
                ZebraScanner = getattr(scanner_module, 'ZebraScanner', None)
                if ZebraScanner:
                    scanner = ZebraScanner()
                    if scanner.connect():
                        print("✅ Escáner conectado exitosamente")
                        scanner.disconnect()
                    else:
                        print("❌ No se pudo conectar al escáner")
                        print("💡 Verificar puerto COM y conexión física")
                else:
                    print("❌ Clase ZebraScanner no encontrada")
            else:
                print("❌ Módulo de escáner no disponible")
        except Exception as e:
            print(f"❌ Error probando escáner: {e}")
    
    def _show_config(self):
        """Mostrar configuración actual"""
        print("\n⚙️ Configuración del Sistema:")
        config = self.components.get('config')
        if config:
            print(f"  Puerto Serie: {getattr(config.hardware, 'serial_port', 'No configurado')}")
            print(f"  Puerto Web: {getattr(config.web, 'port', 5000)}")
            print(f"  Ambiente: {getattr(config.system, 'environment', 'No configurado')}")
            print(f"  Log Level: {getattr(config.system, 'log_level', 'INFO')}")
        else:
            print("  ❌ Configuración no disponible")
            print("  💡 Ejecuta: python setup_project.py")
    
    def _run_diagnostics(self):
        """Ejecutar diagnósticos del sistema"""
        print("\n🔍 Ejecutando diagnósticos...")
        
        # Verificar Python
        print(f"  Python: {sys.version.split()[0]} ✅")
        
        # Verificar dependencias
        deps = ['flask', 'serial', 'openpyxl']
        for dep in deps:
            try:
                __import__(dep)
                print(f"  {dep}: Instalado ✅")
            except ImportError:
                print(f"  {dep}: Faltante ❌")
        
        # Verificar archivos
        files = ['main.py', 'config/development.json', 'requirements.txt']
        for file in files:
            if Path(file).exists():
                print(f"  {file}: Existe ✅")
            else:
                print(f"  {file}: Faltante ❌")
    
    def _scanner_console_loop(self):
        """Bucle de consola para scanner"""
        print("📱 Sistema de escaneo activo - Presiona Ctrl+C para salir")
        try:
            while True:
                command = input("\nComando (scan/status/quit): ").strip().lower()
                if command == 'quit':
                    break
                elif command == 'scan':
                    print("Simulando escaneo...")
                elif command == 'status':
                    print("Estado: Activo")
        except KeyboardInterrupt:
            print("\n👋 Deteniendo scanner...")
    
    def _keep_running(self):
        """Mantener sistema corriendo"""
        try:
            print("⚡ Sistema activo - Presiona Ctrl+C para detener")
            while self.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Deteniendo sistema...")
        finally:
            self.running = False


def main():
    """Función principal mejorada"""
    parser = argparse.ArgumentParser(
        description="Johnson Controls - Sistema de Seguimiento Industrial (Versión Robusta)"
    )
    
    parser.add_argument('--mode', choices=['full', 'scanner', 'web', 'console'], 
                       default='full', help='Modo de ejecución')
    parser.add_argument('--config', default='development', help='Configuración')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Nivel de logging')
    parser.add_argument('--port', type=int, help='Puerto web')
    
    args = parser.parse_args()
    
    print("🏭 JOHNSON CONTROLS - SISTEMA DE SEGUIMIENTO INDUSTRIAL")
    print("=" * 60)
    print("Versión: 2.0 Robusta")
    print("Planta: Durango, México")
    print("=" * 60)
    
    # Verificar ambiente
    if not check_and_setup_environment():
        print("\n❌ Error en configuración del ambiente")
        print("💡 Ejecuta: python setup_project.py")
        print("💡 O ejecuta: python quick_start.py")
        return
    
    # Crear sistema
    system = SafeJohnsonControlsSystem(args)
    
    # Ejecutar según modo
    try:
        if args.mode == 'full':
            system.run_full_mode()
        elif args.mode == 'web':
            system.run_web_mode()
        elif args.mode == 'scanner':
            system.run_scanner_mode()
        elif args.mode == 'console':
            system.run_console_mode()
    except KeyboardInterrupt:
        print("\n\n👋 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error del sistema: {e}")
        logger.error(f"System error: {e}")


if __name__ == "__main__":
    main()