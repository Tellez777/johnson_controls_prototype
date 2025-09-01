#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEB APPLICATION - Aplicación web principal (Modularizada)
Johnson Controls - Sistema de Seguimiento Industrial
"""

import threading
import webbrowser
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS

from ..utils.config import config, get_web_config, get_jci_config
from ..utils.logger import get_logger
from .api.data_api import DataAPI
from .api.control_api import ControlAPI
from .api.analytics_api import AnalyticsAPI


class WebApplication:
    """Aplicación web principal de Johnson Controls"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.web_config = get_web_config()
        self.jci_config = get_jci_config()
        
        # Crear aplicación Flask
        self.app = Flask(__name__)
        
        # Configurar paths para templates y static
        self.app.template_folder = str(Path(__file__).parent / 'templates')
        self.app.static_folder = str(Path(__file__).parent / 'static')
        
        # Configurar CORS si está habilitado
        if self.web_config.cors_enabled:
            CORS(self.app)
        
        # APIs
        self.data_api = DataAPI()
        self.control_api = ControlAPI()
        self.analytics_api = AnalyticsAPI()
        
        # Estado del servidor
        self.server_thread = None
        self.is_running = False
        
        self.logger.info("Web Application inicializada con archivos estáticos")
    
    def initialize(self) -> bool:
        """Inicializar aplicación web"""
        try:
            # Configurar Flask
            self._configure_flask()
            
            # Registrar rutas
            self._register_routes()
            
            # Registrar APIs
            self._register_apis()
            
            # Configurar manejo de errores
            self._configure_error_handlers()
            
            # Verificar que los archivos estáticos existan
            self._ensure_static_files()
            
            self.logger.info("Web Application configurada correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando Web Application: {e}")
            return False
    
    def _configure_flask(self):
        """Configurar aplicación Flask"""
        self.app.config['SECRET_KEY'] = 'jci_manufacturing_system_2024'
        self.app.config['JSON_SORT_KEYS'] = False
        
        # Configuración de sesión
        self.app.config['PERMANENT_SESSION_LIFETIME'] = self.web_config.session_timeout
        
        if not self.web_config.debug:
            # Configuración para producción
            self.app.config['ENV'] = 'production'
            self.app.config['DEBUG'] = False
        else:
            # Configuración para desarrollo
            self.app.config['ENV'] = 'development'
            self.app.config['DEBUG'] = True
    
    def _register_routes(self):
        """Registrar rutas principales"""
        
        @self.app.route('/')
        def dashboard():
            """Dashboard principal usando template"""
            try:
                return render_template('dashboard.html')
            except Exception as e:
                self.logger.error(f"Error renderizando dashboard: {e}")
                # Fallback a dashboard básico
                return self._get_fallback_dashboard()
        
        @self.app.route('/health')
        def health_check():
            """Verificación de salud del sistema"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0',
                'plant': self.jci_config.plant_name
            })
        
        @self.app.route('/api/system/info')
        def system_info():
            """Información del sistema"""
            return jsonify({
                'plant_id': self.jci_config.plant_id,
                'plant_name': self.jci_config.plant_name,
                'department': self.jci_config.department,
                'environment': self.config.system.environment,
                'version': '2.0',
                'features': {
                    'analytics': self.config.system.enable_analytics,
                    'notifications': self.config.system.enable_notifications,
                    'debug_mode': self.config.system.log_level == 'DEBUG'
                }
            })
        
        @self.app.route('/api/time')
        def current_time():
            """Tiempo actual del sistema"""
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'timezone': 'America/Mexico_City',
                'shift_info': self._get_shift_info()
            })
        
        # Ruta para servir archivos estáticos personalizados (si es necesario)
        @self.app.route('/assets/<path:filename>')
        def custom_assets(filename):
            """Servir assets personalizados"""
            return send_from_directory(
                Path(self.app.static_folder) / 'assets', 
                filename
            )
    
    def _ensure_static_files(self):
        """Asegurar que los archivos estáticos existan"""
        static_path = Path(self.app.static_folder)
        template_path = Path(self.app.template_folder)
        
        # Crear directorios si no existen
        (static_path / 'css').mkdir(parents=True, exist_ok=True)
        (static_path / 'js').mkdir(parents=True, exist_ok=True)
        (static_path / 'assets').mkdir(parents=True, exist_ok=True)
        template_path.mkdir(parents=True, exist_ok=True)
        
        # Verificar archivos críticos
        critical_files = [
            template_path / 'dashboard.html',
            static_path / 'css' / 'jci-dashboard.css',
            static_path / 'js' / 'jci-dashboard.js'
        ]
        
        missing_files = [f for f in critical_files if not f.exists()]
        
        if missing_files:
            self.logger.warning(f"Archivos estáticos faltantes: {missing_files}")
            self.logger.info("Creando archivos estáticos básicos...")
            self._create_basic_static_files()
    
    def _create_basic_static_files(self):
        """Crear archivos estáticos básicos si no existen"""
        static_path = Path(self.app.static_folder)
        template_path = Path(self.app.template_folder)
        
        # CSS básico
        css_file = static_path / 'css' / 'jci-dashboard.css'
        if not css_file.exists():
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write("""
/* CSS básico para Johnson Controls Dashboard */
body { 
    font-family: Arial, sans-serif; 
    background: #f5f5f5; 
    margin: 0; 
    padding: 20px; 
}
.container { 
    max-width: 1200px; 
    margin: 0 auto; 
}
.jci-header { 
    background: linear-gradient(135deg, #003D79, #0066CC); 
    color: white; 
    padding: 30px; 
    border-radius: 10px; 
    text-align: center; 
    margin-bottom: 20px; 
}
                """)
        
        # JavaScript básico
        js_file = static_path / 'js' / 'jci-dashboard.js'
        if not js_file.exists():
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write("""
// JavaScript básico para Johnson Controls Dashboard
console.log('Johnson Controls Dashboard cargado');

function refreshData() {
    console.log('Actualizando datos...');
    alert('Funcionalidad en desarrollo');
}

function simulateScan(productCode) {
    console.log('Simulando escaneo:', productCode);
    alert('Escaneo simulado: ' + productCode);
}
                """)
        
        # Template HTML básico
        html_file = template_path / 'dashboard.html'
        if not html_file.exists():
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write("""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Johnson Controls - Sistema de Seguimiento Industrial</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/jci-dashboard.css') }}">
</head>
<body>
    <div class="container">
        <div class="jci-header">
            <h1>🏭 Johnson Controls</h1>
            <p>Sistema de Seguimiento Industrial - Planta Durango</p>
        </div>
        <div>
            <h2>Dashboard en Desarrollo</h2>
            <p>Los archivos estáticos completos están disponibles. Configurar usando setup_project.py</p>
            <button onclick="refreshData()">Actualizar Datos</button>
        </div>
    </div>
    <script src="{{ url_for('static', filename='js/jci-dashboard.js') }}"></script>
</body>
</html>
                """)
    
    def _register_apis(self):
        """Registrar APIs especializadas"""
        # API de datos
        self.app.register_blueprint(self.data_api.get_blueprint(), url_prefix='/api/data')
        
        # API de control
        self.app.register_blueprint(self.control_api.get_blueprint(), url_prefix='/api/control')
        
        # API de analytics
        self.app.register_blueprint(self.analytics_api.get_blueprint(), url_prefix='/api/analytics')
        
        self.logger.info("APIs registradas: data, control, analytics")
    
    def _configure_error_handlers(self):
        """Configurar manejadores de errores"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'error': 'Endpoint no encontrado',
                'status_code': 404,
                'timestamp': datetime.now().isoformat()
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                'error': 'Error interno del servidor',
                'status_code': 500,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            self.logger.error(f"Error no manejado: {e}")
            return jsonify({
                'error': 'Error interno del sistema',
                'status_code': 500,
                'timestamp': datetime.now().isoformat()
            }), 500
    
    def _get_shift_info(self) -> Dict[str, str]:
        """Obtener información del turno actual"""
        now = datetime.now().time()
        shift_start = datetime.strptime(self.jci_config.shift_start, '%H:%M').time()
        shift_end = datetime.strptime(self.jci_config.shift_end, '%H:%M').time()
        
        if shift_start <= now <= shift_end:
            return {
                'current_shift': 'Día',
                'shift_start': self.jci_config.shift_start,
                'shift_end': self.jci_config.shift_end,
                'status': 'active'
            }
        else:
            return {
                'current_shift': 'Noche',
                'shift_start': self.jci_config.shift_start,
                'shift_end': self.jci_config.shift_end,
                'status': 'inactive'
            }
    
    def _get_fallback_dashboard(self) -> str:
        """Dashboard de fallback si no hay template"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Johnson Controls - Sistema de Seguimiento</title>
            <style>
                body { font-family: Arial; background: #f5f5f5; margin: 0; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                .header { background: #003D79; color: white; padding: 20px; border-radius: 5px; text-align: center; }
                .status { padding: 15px; background: #e8f5e8; border: 1px solid #4CAF50; border-radius: 4px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏭 Johnson Controls</h1>
                    <p>Sistema de Seguimiento Industrial</p>
                </div>
                <div class="status">
                    <strong>⚠️ Modo Fallback:</strong> Los archivos de template no están disponibles.
                    <br><br>
                    <strong>Para dashboard completo:</strong>
                    <ol>
                        <li>Ejecutar: <code>python setup_project.py</code></li>
                        <li>Los archivos CSS/JS/HTML se crearán automáticamente</li>
                        <li>Recargar la página</li>
                    </ol>
                </div>
                <button onclick="location.reload()" style="padding: 10px 20px; background: #0066CC; color: white; border: none; border-radius: 4px; cursor: pointer;">🔄 Recargar</button>
            </div>
        </body>
        </html>
        """
    
    def start(self):
        """Iniciar servidor web"""
        if not self.is_running:
            self.is_running = True
            
            def run_server():
                try:
                    self.logger.info(f"Iniciando servidor web en puerto {self.web_config.port}")
                    
                    # Abrir navegador automáticamente en desarrollo
                    if self.config.system.environment == 'development':
                        threading.Timer(2.0, lambda: webbrowser.open(
                            f'http://localhost:{self.web_config.port}'
                        )).start()
                    
                    self.app.run(
                        host=self.web_config.host,
                        port=self.web_config.port,
                        debug=self.web_config.debug,
                        use_reloader=False,
                        threaded=True
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error iniciando servidor web: {e}")
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            self.logger.info("Servidor web iniciado")
    
    def stop(self):
        """Detener servidor web"""
        self.is_running = False
        self.logger.info("Servidor web detenido")