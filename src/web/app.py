#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEB APPLICATION - Aplicación web principal
Johnson Controls - Sistema de Seguimiento Industrial
"""

import threading
import webbrowser
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, jsonify, request, render_template_string
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
        
        self.logger.info("Web Application inicializada")
    
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
            """Dashboard principal"""
            return self._get_dashboard_template()
        
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
    
    def _get_dashboard_template(self) -> str:
        """Obtener template del dashboard mejorado para Johnson Controls"""
        return '''
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Johnson Controls - Sistema de Seguimiento Industrial</title>
            <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏭</text></svg>">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                
                :root {
                    --jci-blue: #0066CC;
                    --jci-dark-blue: #003D79;
                    --jci-light-blue: #E6F3FF;
                    --jci-gray: #6C757D;
                    --jci-dark-gray: #343A40;
                    
                    --bg-primary: #0f1419;
                    --bg-secondary: #1a1f26;
                    --bg-card: #242b36;
                    --bg-card-hover: #2a3240;
                    --text-primary: #e6e8eb;
                    --text-secondary: #9ca3af;
                    --text-muted: #6b7280;
                    --accent-primary: var(--jci-blue);
                    --accent-success: #10b981;
                    --accent-warning: #f59e0b;
                    --accent-danger: #ef4444;
                    --border-color: #374151;
                    --border-hover: #4b5563;
                    --shadow: rgba(0, 0, 0, 0.25);
                }
                
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
                    min-height: 100vh; 
                    color: var(--text-primary);
                    line-height: 1.6;
                }
                
                .container { max-width: 1600px; margin: 0 auto; padding: 24px; }
                
                .jci-header { 
                    background: linear-gradient(135deg, var(--jci-dark-blue) 0%, var(--jci-blue) 100%); 
                    border-radius: 16px; 
                    padding: 32px; 
                    margin-bottom: 32px; 
                    text-align: center; 
                    box-shadow: 0 8px 32px var(--shadow);
                    position: relative;
                    overflow: hidden;
                }
                
                .jci-header::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="%23ffffff" stroke-width="0.5" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
                }
                
                .jci-header .content { position: relative; z-index: 1; }
                
                .jci-header h1 { 
                    color: white; 
                    margin-bottom: 12px; 
                    font-size: 2.8em; 
                    font-weight: 700;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }
                
                .jci-header p { 
                    color: var(--jci-light-blue); 
                    font-size: 1.2em; 
                    font-weight: 500;
                }
                
                .jci-logo {
                    display: inline-block;
                    background: white;
                    color: var(--jci-blue);
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: bold;
                    margin-bottom: 16px;
                    font-size: 0.9em;
                    letter-spacing: 2px;
                }
                
                .plant-info { 
                    display: flex; 
                    justify-content: center;
                    gap: 40px;
                    margin-top: 24px;
                    font-size: 0.95em;
                }
                
                .plant-info div {
                    background: rgba(255,255,255,0.1);
                    padding: 8px 16px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }
                
                .status-bar { 
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px; 
                    padding: 20px 24px; 
                    background: var(--bg-card); 
                    border: 1px solid var(--border-color);
                    border-radius: 12px; 
                    margin-bottom: 32px; 
                    box-shadow: 0 4px 16px var(--shadow);
                }
                
                .status-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .status-dot { 
                    width: 12px; 
                    height: 12px; 
                    border-radius: 50%; 
                    animation: pulse 2s infinite;
                }
                .status-active { 
                    background: var(--accent-success); 
                    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
                }
                .status-warning { 
                    background: var(--accent-warning);
                    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
                }
                .status-error { 
                    background: var(--accent-danger);
                    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
                }
                @keyframes pulse { 
                    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
                    70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
                }
                
                .kpi-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                    gap: 24px; 
                    margin-bottom: 32px; 
                }
                
                .kpi-card { 
                    background: var(--bg-card); 
                    border: 1px solid var(--border-color);
                    padding: 28px; 
                    border-radius: 16px; 
                    text-align: center; 
                    box-shadow: 0 4px 16px var(--shadow); 
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                
                .kpi-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 4px;
                    background: linear-gradient(90deg, var(--jci-blue), var(--accent-success));
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }
                
                .kpi-card:hover::before { opacity: 1; }
                .kpi-card:hover { 
                    transform: translateY(-4px); 
                    border-color: var(--border-hover);
                    box-shadow: 0 8px 32px var(--shadow);
                }
                
                .kpi-value { 
                    font-size: 3.2em; 
                    font-weight: 800; 
                    margin-bottom: 8px; 
                    line-height: 1;
                    background: linear-gradient(135deg, var(--jci-blue), var(--accent-success));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                
                .kpi-label { 
                    color: var(--text-secondary); 
                    font-size: 1em; 
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .kpi-subtitle {
                    color: var(--text-muted);
                    font-size: 0.85em;
                    margin-top: 4px;
                }
                
                .dashboard-grid { 
                    display: grid; 
                    grid-template-columns: 2fr 1fr; 
                    gap: 32px; 
                    margin-bottom: 32px; 
                }
                
                .section { 
                    background: var(--bg-card); 
                    border: 1px solid var(--border-color);
                    border-radius: 16px; 
                    padding: 28px; 
                    box-shadow: 0 4px 16px var(--shadow);
                    transition: border-color 0.3s ease;
                }
                
                .section:hover { border-color: var(--border-hover); }
                
                .section-title { 
                    font-size: 1.5em; 
                    font-weight: 700; 
                    margin-bottom: 24px; 
                    color: var(--text-primary); 
                    border-bottom: 2px solid var(--jci-blue); 
                    padding-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .section-title::before {
                    content: '';
                    width: 4px;
                    height: 24px;
                    background: var(--jci-blue);
                    border-radius: 2px;
                }
                
                .chart-container {
                    height: 350px;
                    margin: 20px 0;
                    position: relative;
                }
                
                .product-card { 
                    background: var(--bg-secondary); 
                    border: 1px solid var(--border-color); 
                    border-radius: 12px; 
                    padding: 20px; 
                    margin: 12px 0; 
                    border-left: 4px solid var(--jci-blue); 
                    transition: all 0.3s ease;
                }
                
                .product-card:hover { 
                    border-color: var(--border-hover);
                    transform: translateX(4px);
                    box-shadow: 0 4px 16px var(--shadow);
                }
                
                .product-header { 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: flex-start; 
                    margin-bottom: 16px; 
                }
                
                .product-name { 
                    font-size: 1.2em; 
                    font-weight: 700; 
                    color: var(--text-primary); 
                    margin-bottom: 4px;
                }
                
                .product-code { 
                    font-size: 0.85em; 
                    color: var(--text-muted); 
                    font-family: 'Courier New', monospace;
                    background: var(--bg-primary);
                    padding: 2px 6px;
                    border-radius: 4px;
                }
                
                .product-meta {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px;
                    font-size: 0.85em;
                    color: var(--text-secondary);
                    margin-top: 12px;
                }
                
                .control-panel {
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                
                .control-group { 
                    margin-bottom: 20px; 
                }
                
                .control-label { 
                    font-weight: 700; 
                    margin-bottom: 12px; 
                    color: var(--text-primary);
                    font-size: 1em;
                }
                
                .btn { 
                    padding: 10px 16px; 
                    border: none; 
                    border-radius: 8px; 
                    cursor: pointer; 
                    font-size: 0.9em; 
                    font-weight: 600;
                    transition: all 0.2s ease; 
                    margin: 4px; 
                    text-transform: none;
                    letter-spacing: 0.3px;
                }
                
                .btn-jci { 
                    background: var(--jci-blue); 
                    color: white; 
                    box-shadow: 0 2px 8px rgba(0, 102, 204, 0.3);
                }
                .btn-jci:hover { 
                    background: var(--jci-dark-blue); 
                    transform: translateY(-1px); 
                    box-shadow: 0 4px 16px rgba(0, 102, 204, 0.4);
                }
                
                .btn-success { 
                    background: var(--accent-success); 
                    color: white; 
                    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
                }
                .btn-success:hover { 
                    background: #059669; 
                    transform: translateY(-1px); 
                }
                
                .btn-warning { 
                    background: var(--accent-warning); 
                    color: white; 
                }
                .btn-warning:hover { 
                    background: #d97706; 
                    transform: translateY(-1px); 
                }
                
                .btn-sm { padding: 8px 12px; font-size: 0.8em; }
                
                .notification { 
                    position: fixed; 
                    top: 24px; 
                    right: 24px; 
                    padding: 16px 24px; 
                    border-radius: 12px; 
                    color: white; 
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); 
                    z-index: 1000; 
                    animation: slideIn 0.3s ease; 
                    max-width: 350px;
                    font-weight: 600;
                }
                
                .notification.success { 
                    background: var(--accent-success); 
                }
                .notification.error { 
                    background: var(--accent-danger); 
                }
                .notification.warning { 
                    background: var(--accent-warning); 
                }
                
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                .loading { 
                    text-align: center; 
                    padding: 40px; 
                    color: var(--text-secondary);
                    font-size: 1.1em;
                }
                
                .footer { 
                    text-align: center; 
                    margin-top: 48px; 
                    padding: 32px; 
                    color: var(--text-muted);
                    border-top: 1px solid var(--border-color);
                    background: var(--bg-card);
                    border-radius: 16px;
                }
                
                .footer .jci-branding {
                    background: linear-gradient(135deg, var(--jci-blue), var(--jci-dark-blue));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    font-weight: bold;
                    font-size: 1.1em;
                }
                
                @media (max-width: 1200px) {
                    .dashboard-grid {
                        grid-template-columns: 1fr;
                    }
                    .plant-info {
                        flex-direction: column;
                        gap: 12px;
                    }
                }
                
                @media (max-width: 768px) {
                    .container { padding: 16px; }
                    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
                    .status-bar { grid-template-columns: 1fr; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="jci-header">
                    <div class="content">
                        <div class="jci-logo">JOHNSON CONTROLS</div>
                        <h1>Sistema de Seguimiento Industrial</h1>
                        <p>Plataforma de Monitoreo en Tiempo Real - Manufactura Avanzada</p>
                        <div class="plant-info">
                            <div><strong>🏭 Planta:</strong> <span id="plant-name">Durango, México</span></div>
                            <div><strong>🏢 Departamento:</strong> <span id="department">Manufactura</span></div>
                            <div><strong>⏰ Turno:</strong> <span id="current-shift">Día</span></div>
                        </div>
                    </div>
                </div>
                
                <div class="status-bar">
                    <div class="status-item">
                        <div class="status-dot status-active" id="system-status"></div>
                        <span><strong>Sistema:</strong> <span id="system-status-text">Operativo</span></span>
                    </div>
                    <div class="status-item">
                        <div class="status-dot status-active" id="scanner-status"></div>
                        <span><strong>Escáner:</strong> <span id="scanner-status-text">Conectado</span></span>
                    </div>
                    <div class="status-item">
                        <span><strong>Etapa Activa:</strong> <span id="current-stage">Soldadura</span></span>
                    </div>
                    <div class="status-item">
                        <span><strong>Actualizado:</strong> <span id="last-update">--:--</span></span>
                    </div>
                </div>
                
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-value" id="oee-score">87%</div>
                        <div class="kpi-label">OEE Score</div>
                        <div class="kpi-subtitle">Overall Equipment Effectiveness</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value" id="efficiency-rate">92%</div>
                        <div class="kpi-label">Eficiencia</div>
                        <div class="kpi-subtitle">Rendimiento del Proceso</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value" id="quality-score">96%</div>
                        <div class="kpi-label">Calidad</div>
                        <div class="kpi-subtitle">Estándar Johnson Controls</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value" id="throughput">24</div>
                        <div class="kpi-label">Throughput</div>
                        <div class="kpi-subtitle">Unidades por Hora</div>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <div class="section">
                        <h2 class="section-title">Estado de Productos</h2>
                        <div id="products-container">
                            <div class="loading">Cargando datos del sistema...</div>
                        </div>
                    </div>
                    
                    <div>
                        <div class="section">
                            <h2 class="section-title">Centro de Control</h2>
                            
                            <div class="control-panel">
                                <div class="control-group">
                                    <div class="control-label">📊 Sistema</div>
                                    <button class="btn btn-jci" onclick="refreshData()">Actualizar Datos</button>
                                    <button class="btn btn-success btn-sm" onclick="exportReport()">Exportar Reporte</button>
                                </div>
                                
                                <div class="control-group">
                                    <div class="control-label">🔧 Simulaciones</div>
                                    <button class="btn btn-success btn-sm" onclick="simulateScan('JCI240001A')">Producto A</button>
                                    <button class="btn btn-success btn-sm" onclick="simulateScan('JCI240002B')">Producto B</button>
                                    <button class="btn btn-success btn-sm" onclick="simulateScan('JCI240003C')">Producto C</button>
                                </div>
                                
                                <div class="control-group">
                                    <div class="control-label">⚙️ Control de Etapas</div>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(1)">Soldadura</button>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(2)">Pulido</button>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(3)">Presión</button>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(4)">Calidad</button>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(5)">Pintura</button>
                                    <button class="btn btn-warning btn-sm" onclick="changeStage(6)">Almacén</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="section" style="margin-top: 20px;">
                            <h2 class="section-title">Analytics</h2>
                            <div class="chart-container">
                                <canvas id="performanceChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p class="jci-branding">JOHNSON CONTROLS</p>
                    <p>Sistema de Seguimiento Industrial v2.0</p>
                    <p>Planta Durango | Manufactura Avanzada | Integración Zebra DS3678</p>
                </div>
            </div>

            <script>
                let autoRefresh = true;
                let refreshInterval = null;
                let performanceChart = null;
                
                // Configuración de colores JCI
                const jciColors = {
                    primary: '#0066CC',
                    secondary: '#003D79',
                    success: '#10b981',
                    warning: '#f59e0b',
                    danger: '#ef4444'
                };
                
                // Inicialización
                document.addEventListener('DOMContentLoaded', function() {
                    initializeChart();
                    loadSystemInfo();
                    startAutoRefresh();
                });
                
                async function loadSystemInfo() {
                    try {
                        const response = await fetch('/api/system/info');
                        const info = await response.json();
                        
                        document.getElementById('plant-name').textContent = info.plant_name;
                        document.getElementById('department').textContent = info.department;
                        
                    } catch (error) {
                        console.error('Error cargando información del sistema:', error);
                    }
                }
                
                async function refreshData() {
                    try {
                        // Simular datos para el prototipo
                        updateKPIs();
                        updateProducts();
                        updateStatus();
                        
                        showNotification('Datos actualizados correctamente', 'success');
                        
                    } catch (error) {
                        console.error('Error actualizando datos:', error);
                        showNotification('Error actualizando datos', 'error');
                    }
                }
                
                function updateKPIs() {
                    // Simular KPIs realistas para Johnson Controls
                    document.getElementById('oee-score').textContent = (85 + Math.random() * 10).toFixed(0) + '%';
                    document.getElementById('efficiency-rate').textContent = (88 + Math.random() * 8).toFixed(0) + '%';
                    document.getElementById('quality-score').textContent = (94 + Math.random() * 5).toFixed(0) + '%';
                    document.getElementById('throughput').textContent = Math.floor(20 + Math.random() * 10);
                }
                
                function updateProducts() {
                    const container = document.getElementById('products-container');
                    const products = [
                        {
                            code: 'JCI240001A',
                            name: 'Controlador HVAC Inteligente',
                            partNumber: 'HVAC-CTL-2024-001',
                            workOrder: 'WO-2024-0156',
                            progress: 75,
                            stage: 'Calidad',
                            status: 'En Proceso'
                        },
                        {
                            code: 'JCI240002B',
                            name: 'Sistema de Gestión de Batería',
                            partNumber: 'BATT-SYS-2024-002',
                            workOrder: 'WO-2024-0157',
                            progress: 100,
                            stage: 'Completado',
                            status: 'Completado'
                        },
                        {
                            code: 'JCI240003C',
                            name: 'Switch Inteligente Interior',
                            partNumber: 'INT-SWT-2024-003',
                            workOrder: 'WO-2024-0158',
                            progress: 33,
                            stage: 'Pulido',
                            status: 'En Proceso'
                        }
                    ];
                    
                    container.innerHTML = products.map(product => `
                        <div class="product-card">
                            <div class="product-header">
                                <div>
                                    <div class="product-name">${product.name}</div>
                                    <div class="product-code">${product.code}</div>
                                </div>
                                <div style="padding: 6px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600; background: ${product.status === 'Completado' ? '#10b981' : '#f59e0b'}; color: white;">
                                    ${product.status}
                                </div>
                            </div>
                            <div class="product-meta">
                                <div><strong>P/N:</strong> ${product.partNumber}</div>
                                <div><strong>WO:</strong> ${product.workOrder}</div>
                                <div><strong>Etapa:</strong> ${product.stage}</div>
                                <div><strong>Progreso:</strong> ${product.progress}%</div>
                            </div>
                        </div>
                    `).join('');
                }
                
                function updateStatus() {
                    document.getElementById('system-status-text').textContent = 'Operativo';
                    document.getElementById('scanner-status-text').textContent = 'Conectado';
                    document.getElementById('current-stage').textContent = 'Soldadura';
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                }
                
                function initializeChart() {
                    const ctx = document.getElementById('performanceChart').getContext('2d');
                    performanceChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00'],
                            datasets: [{
                                label: 'Eficiencia',
                                data: [92, 89, 94, 91, 88, 93],
                                borderColor: jciColors.primary,
                                backgroundColor: jciColors.primary + '20',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#e6e8eb' }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { color: '#374151' },
                                    ticks: { color: '#e6e8eb' }
                                },
                                y: {
                                    grid: { color: '#374151' },
                                    ticks: { color: '#e6e8eb' },
                                    min: 80,
                                    max: 100
                                }
                            }
                        }
                    });
                }
                
                async function simulateScan(productCode) {
                    try {
                        showNotification(`Simulando escaneo: ${productCode}`, 'warning');
                        
                        const response = await fetch('/api/control/simulate_scan', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ barcode: productCode })
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showNotification('Escaneo simulado exitosamente', 'success');
                            setTimeout(refreshData, 1000);
                        } else {
                            showNotification('Error en simulación: ' + result.message, 'error');
                        }
                        
                    } catch (error) {
                        showNotification('Error de conexión', 'error');
                    }
                }
                
                async function changeStage(stageNumber) {
                    try {
                        const response = await fetch('/api/control/change_stage', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ stage: stageNumber })
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showNotification(`Etapa cambiada a ${stageNumber}`, 'success');
                            refreshData();
                        } else {
                            showNotification('Error cambiando etapa', 'error');
                        }
                        
                    } catch (error) {
                        showNotification('Error de conexión', 'error');
                    }
                }
                
                function exportReport() {
                    showNotification('Funcionalidad de exportación en desarrollo', 'warning');
                }
                
                function showNotification(message, type = 'success') {
                    const notification = document.createElement('div');
                    notification.className = `notification ${type}`;
                    notification.textContent = message;
                    
                    document.body.appendChild(notification);
                    
                    setTimeout(() => {
                        notification.remove();
                    }, 4000);
                }
                
                function startAutoRefresh() {
                    refreshInterval = setInterval(() => {
                        if (autoRefresh) {
                            refreshData();
                        }
                    }, 5000);
                }
                
                // Controles de teclado
                document.addEventListener('keydown', (e) => {
                    if (e.target.tagName.toLowerCase() === 'input') return;
                    
                    switch(e.key) {
                        case '1': simulateScan('JCI240001A'); break;
                        case '2': simulateScan('JCI240002B'); break;
                        case '3': simulateScan('JCI240003C'); break;
                        case 'r': case 'R': refreshData(); break;
                    }
                });
                
                // Inicialización
                refreshData();
            </script>
        </body>
        </html>
        '''