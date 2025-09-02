#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP EXTENSION - Extensión para WebApplication existente
Integra nuevas funcionalidades SIN modificar app.py original
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import jsonify, request


class WebApplicationExtension:
    """Extensión para WebApplication que añade funcionalidades mejoradas"""
    
    def __init__(self, web_app):
        """
        Inicializar extensión con referencia a la WebApplication original
        
        Args:
            web_app: Instancia de la WebApplication existente
        """
        self.web_app = web_app
        self.app = web_app.app
        self.logger = web_app.logger
        
        # Registrar nuevas rutas sin conflictos
        self._register_enhanced_routes()
        
        # Crear logo JCI si no existe
        self._ensure_jci_assets()
        
        self.logger.info("WebApplication Extension inicializada")
    
    def _register_enhanced_routes(self):
        """Registrar rutas mejoradas que complementan las originales"""
        
        @self.app.route('/api/enhanced_data')
        def get_enhanced_data():
            """Endpoint mejorado con KPIs adicionales (complementa /api/data)"""
            try:
                # Obtener datos base del sistema actual
                base_data = self._get_system_data()
                
                # Calcular KPIs mejorados
                enhanced_kpis = self._calculate_enhanced_kpis(base_data)
                
                # Generar insights
                insights = self._generate_automatic_insights(base_data, enhanced_kpis)
                
                # Respuesta mejorada manteniendo compatibilidad
                response = {
                    **base_data,  # Mantener estructura original
                    'kpis_operacionales': enhanced_kpis,
                    'insights': insights,
                    'enhanced_version': True,
                    'version': '2.0_extended'
                }
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error en enhanced_data: {e}")
                return jsonify({
                    'error': str(e),
                    'fallback': True,
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/simulate_scan_enhanced', methods=['POST'])
        def simulate_scan_enhanced():
            """Simulación mejorada que actualiza datos adicionales"""
            try:
                data = request.get_json()
                codigo = data.get('codigo')
                
                # Validar códigos Johnson Controls
                valid_codes = ['JCI240001A', 'JCI240002B', 'JCI240003C']
                if codigo not in valid_codes:
                    return jsonify({
                        'success': False, 
                        'message': f'Código inválido. Usar: {", ".join(valid_codes)}'
                    }), 400
                
                # Simular actualización de datos
                result = self._simulate_enhanced_scan(codigo)
                
                return jsonify({
                    'success': True,
                    'message': f'Escaneo simulado exitoso: {codigo}',
                    'product_data': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error en simulate_scan_enhanced: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.app.route('/api/stage_change_enhanced', methods=['POST'])
        def stage_change_enhanced():
            """Cambio de etapa con información adicional"""
            try:
                data = request.get_json()
                etapa = int(data.get('etapa', 1))
                
                if not 1 <= etapa <= 6:
                    return jsonify({
                        'success': False,
                        'message': 'Etapa debe estar entre 1 y 6'
                    }), 400
                
                # Información de etapas Johnson Controls
                stage_info = self._get_stage_info(etapa)
                
                return jsonify({
                    'success': True,
                    'etapa': etapa,
                    'stage_info': stage_info,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error en stage_change_enhanced: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.app.route('/api/dashboard_config')
        def get_dashboard_config():
            """Configuración específica del dashboard Johnson Controls"""
            return jsonify({
                'company': {
                    'name': 'Johnson Controls International',
                    'plant': 'Durango, México',
                    'department': 'Manufactura'
                },
                'color_palette': {
                    'primary': '#00B8E0',
                    'secondary': '#0399CC', 
                    'tertiary': '#0554A3',
                    'dark': '#08338F',
                    'success': '#29B582',
                    'accent': '#7DBA00'
                },
                'products': {
                    'JCI240001A': {
                        'name': 'Controlador HVAC Inteligente',
                        'family': 'HVAC-CTL-2024-001'
                    },
                    'JCI240002B': {
                        'name': 'Sistema de Gestión de Batería',
                        'family': 'BATT-SYS-2024-002'
                    },
                    'JCI240003C': {
                        'name': 'Switch Inteligente Interior',
                        'family': 'INT-SWT-2024-003'
                    }
                },
                'stages': {
                    '1': {'name': 'Soldadura', 'operator': 'Lucero Martínez'},
                    '2': {'name': 'Pulido', 'operator': 'Felipe Hernández'},
                    '3': {'name': 'Presión', 'operator': 'Fernando García'},
                    '4': {'name': 'Calidad', 'operator': 'Control de Calidad'},
                    '5': {'name': 'Pintura', 'operator': 'Acabados Finales'},
                    '6': {'name': 'Almacén', 'operator': 'Almacén General'}
                },
                'features': {
                    'enhanced_kpis': True,
                    'bottleneck_analysis': True,
                    'cycle_time_tracking': True,
                    'automated_insights': True
                }
            })
        
        @self.app.route('/dashboard_enhanced')
        def dashboard_enhanced():
            """Dashboard mejorado que usa el template actualizado"""
            try:
                return self.web_app.app.send_static_file('../templates/dashboard.html')
            except:
                # Fallback al dashboard original si hay problemas
                return self.app.redirect('/')
    
    def _get_system_data(self):
        """Obtener datos del sistema actual compatible con arquitectura existente"""
        try:
            # Intentar usar DataAPI existente si está disponible
            if hasattr(self.web_app, 'data_api'):
                # Llamar al método del DataAPI existente si está disponible
                pass
            
            # Fallback: leer desde archivos del sistema
            return self._read_system_files()
            
        except Exception as e:
            self.logger.warning(f"Error obteniendo datos del sistema: {e}")
            return self._get_fallback_data()
    
    def _read_system_files(self):
        """Leer datos desde archivos del sistema existente"""
        possible_files = [
            'data/estado_sistema.json',
            'data/json/estado_sistema.json',
            'estado_sistema.json'
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data
                except Exception as e:
                    self.logger.warning(f"Error leyendo {file_path}: {e}")
        
        return self._get_fallback_data()
    
    def _get_fallback_data(self):
        """Datos de respaldo compatibles"""
        return {
            'productos': {
                'JCI240001A': {
                    'nombre': 'Controlador HVAC Inteligente',
                    'codigo': 'JCI240001A',
                    'estado': 'En Proceso',
                    'progreso': 65,
                    'etapa_actual': 'Pulido',
                    'etapa_actual_numero': 2,
                    'fecha': datetime.now().isoformat(),
                    'operador': 'Felipe Hernández'
                },
                'JCI240002B': {
                    'nombre': 'Sistema de Gestión de Batería', 
                    'codigo': 'JCI240002B',
                    'estado': 'Completado',
                    'progreso': 100,
                    'etapa_actual': 'Almacén',
                    'etapa_actual_numero': 6,
                    'fecha': datetime.now().isoformat(),
                    'operador': 'Almacén General'
                },
                'JCI240003C': {
                    'nombre': 'Switch Inteligente Interior',
                    'codigo': 'JCI240003C', 
                    'estado': 'Pendiente',
                    'progreso': 0,
                    'etapa_actual': 'Soldadura',
                    'etapa_actual_numero': 1,
                    'fecha': datetime.now().isoformat(),
                    'operador': 'Lucero Martínez'
                }
            },
            'estadisticas': {
                'total': 3,
                'completados': 1,
                'en_proceso': 1,
                'pendientes': 1,
                'progreso_promedio': 55.0
            },
            'etapa_actual': 2,
            'etapa_nombre': 'Pulido',
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_enhanced_kpis(self, base_data):
        """Calcular KPIs mejorados basados en datos del sistema"""
        productos = base_data.get('productos', {})
        stats = base_data.get('estadisticas', {})
        
        if not productos:
            return {
                'efficiency_rate': 0.0,
                'throughput_rate': 0.0,
                'avg_cycle_time': 0.0,
                'bottleneck_stage': 'N/A',
                'oee_score': 0.0,
                'quality_score': 0.0
            }
        
        # KPIs basados en datos reales del sistema
        progreso_promedio = stats.get('progreso_promedio', 0)
        completados = stats.get('completados', 0)
        total = stats.get('total', len(productos))
        
        efficiency_rate = round(progreso_promedio, 1)
        throughput_rate = round(completados * 2.5, 1)  # Factor simulado
        avg_cycle_time = round(120 - (progreso_promedio * 0.8), 1)
        bottleneck_stage = self._identify_bottleneck(productos)
        
        # OEE simulado basado en eficiencia
        oee_score = round(max(75, min(95, efficiency_rate + 10)), 1)
        quality_score = round(max(90, min(98, 96 - (total * 0.2))), 1)
        
        return {
            'efficiency_rate': efficiency_rate,
            'throughput_rate': throughput_rate,
            'avg_cycle_time': avg_cycle_time,
            'bottleneck_stage': bottleneck_stage,
            'oee_score': oee_score,
            'quality_score': quality_score
        }
    
    def _identify_bottleneck(self, productos):
        """Identificar cuello de botella basado en datos reales"""
        stage_counts = {}
        stage_names = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        }
        
        for producto in productos.values():
            etapa = producto.get('etapa_actual_numero', 1)
            if etapa not in stage_counts:
                stage_counts[etapa] = 0
            stage_counts[etapa] += 1
        
        if not stage_counts:
            return 'N/A'
        
        # La etapa con más productos es potencialmente el cuello de botella
        bottleneck_etapa = max(stage_counts.keys(), key=lambda x: stage_counts[x])
        return stage_names.get(bottleneck_etapa, 'N/A')
    
    def _generate_automatic_insights(self, base_data, kpis):
        """Generar insights automáticos basados en datos reales"""
        insights = []
        productos = base_data.get('productos', {})
        stats = base_data.get('estadisticas', {})
        
        efficiency = kpis.get('efficiency_rate', 0)
        
        # Insights basados en eficiencia real
        if efficiency < 50:
            insights.append({
                'title': 'Oportunidad Crítica de Mejora',
                'text': f'La eficiencia actual ({efficiency}%) requiere intervención inmediata. Revisar procesos de etapas iniciales.',
                'category': 'performance',
                'priority': 'high'
            })
        elif efficiency > 80:
            insights.append({
                'title': 'Excelente Rendimiento',
                'text': 'El sistema funciona con alta eficiencia. Mantener las buenas prácticas operativas.',
                'category': 'opportunity', 
                'priority': 'low'
            })
        
        # Insights de flujo basados en datos reales
        en_proceso = stats.get('en_proceso', 0)
        completados = stats.get('completados', 0)
        
        if en_proceso > completados:
            insights.append({
                'title': 'Análisis de Flujo',
                'text': 'Más productos en proceso que completados. Considerar balancear cargas de trabajo.',
                'category': 'bottleneck',
                'priority': 'medium'
            })
        
        # Insight sobre cuello de botella
        bottleneck = kpis.get('bottleneck_stage', 'N/A')
        if bottleneck != 'N/A':
            insights.append({
                'title': f'Atención Requerida: {bottleneck}',
                'text': f'La etapa {bottleneck} muestra concentración de productos. Monitorear para prevenir demoras.',
                'category': 'bottleneck',
                'priority': 'medium'
            })
        
        # Insight de tiempo de ciclo
        cycle_time = kpis.get('avg_cycle_time', 0)
        if cycle_time > 100:
            insights.append({
                'title': 'Optimización de Tiempo',
                'text': f'Tiempo de ciclo promedio: {cycle_time}s. Buscar oportunidades para reducir tiempos muertos.',
                'category': 'performance',
                'priority': 'medium'
            })
        
        return insights
    
    def _simulate_enhanced_scan(self, codigo):
        """Simulación mejorada de escaneo"""
        # En sistema real, esto actualizaría la base de datos
        # Por ahora simulamos la respuesta
        
        productos_info = {
            'JCI240001A': {'nombre': 'Controlador HVAC Inteligente', 'familia': 'HVAC-CTL-2024-001'},
            'JCI240002B': {'nombre': 'Sistema de Gestión de Batería', 'familia': 'BATT-SYS-2024-002'},
            'JCI240003C': {'nombre': 'Switch Inteligente Interior', 'familia': 'INT-SWT-2024-003'}
        }
        
        return {
            'codigo': codigo,
            'nombre': productos_info[codigo]['nombre'],
            'familia': productos_info[codigo]['familia'],
            'progreso_anterior': 65,  # Simulado
            'progreso_nuevo': 85,     # Simulado
            'etapa_anterior': 'Pulido',
            'etapa_nueva': 'Presión'
        }
    
    def _get_stage_info(self, etapa):
        """Obtener información detallada de etapa"""
        stages_info = {
            1: {'name': 'Soldadura', 'operator': 'Lucero Martínez', 'code': 'OP001', 'station': 'EST-SOLD-01'},
            2: {'name': 'Pulido', 'operator': 'Felipe Hernández', 'code': 'OP002', 'station': 'EST-PULI-01'},
            3: {'name': 'Presión', 'operator': 'Fernando García', 'code': 'OP003', 'station': 'EST-PRES-01'},
            4: {'name': 'Calidad', 'operator': 'Control de Calidad', 'code': 'QC001', 'station': 'EST-CALI-01'},
            5: {'name': 'Pintura', 'operator': 'Acabados Finales', 'code': 'OP004', 'station': 'EST-PINT-01'},
            6: {'name': 'Almacén', 'operator': 'Almacén General', 'code': 'WH001', 'station': 'EST-ALMA-01'}
        }
        
        return stages_info.get(etapa, {'name': 'Desconocida', 'operator': 'N/A'})
    
    def _ensure_jci_assets(self):
        """Crear assets de Johnson Controls si no existen"""
        try:
            assets_path = Path(self.app.static_folder) / 'assets'
            assets_path.mkdir(parents=True, exist_ok=True)
            
            logo_path = assets_path / 'jci_logo.svg'
            if not logo_path.exists():
                self._create_jci_logo(logo_path)
                self.logger.info("Logo Johnson Controls creado")
                
        except Exception as e:
            self.logger.warning(f"Error creando assets: {e}")
    
    def _create_jci_logo(self, logo_path):
        """Crear logo SVG Johnson Controls"""
        logo_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="200" height="60">
    <defs>
        <linearGradient id="jciGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#00B8E0;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#0399CC;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#0554A3;stop-opacity:1" />
        </linearGradient>
    </defs>
    
    <rect width="200" height="60" fill="none"/>
    
    <text x="10" y="25" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="url(#jciGradient)">JOHNSON</text>
    <text x="10" y="45" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="url(#jciGradient)">CONTROLS</text>
    
    <circle cx="170" cy="30" r="15" fill="none" stroke="url(#jciGradient)" stroke-width="2"/>
    <circle cx="170" cy="30" r="8" fill="url(#jciGradient)"/>
    <path d="M 162 30 L 170 22 L 178 30 L 170 38 Z" fill="white"/>
</svg>'''
        
        with open(logo_path, 'w', encoding='utf-8') as f:
            f.write(logo_svg)


def extend_web_application(web_app):
    """
    Función para extender WebApplication existente sin modificar el código original
    
    Usage:
    # En app.py, después de self._register_apis():
    from .app_extension import extend_web_application
    extend_web_application(self)
    
    Args:
        web_app: Instancia de WebApplication existente
        
    Returns:
        WebApplicationExtension: Instancia de la extensión
    """
    try:
        extension = WebApplicationExtension(web_app)
        web_app.logger.info("WebApplication extension aplicada exitosamente")
        return extension
    except Exception as e:
        web_app.logger.error(f"Error aplicando WebApplication extension: {e}")
        return None


# Función simple para importar en app.py existente
def apply_dashboard_enhancements(web_app):
    """
    Función simple para aplicar mejoras al dashboard
    
    Se puede llamar al final del __init__ en WebApplication:
    apply_dashboard_enhancements(self)
    """
    return extend_web_application(web_app)