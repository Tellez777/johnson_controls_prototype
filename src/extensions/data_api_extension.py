#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATA API EXTENSION - Extensión para el DataAPI existente
Añade funcionalidades mejoradas manteniendo compatibilidad
"""

from datetime import datetime
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, request
import json
import os

class DataAPIExtension:
    """Extensión para el DataAPI existente con nuevas funcionalidades"""
    
    def __init__(self, original_data_api=None):
        self.original_data_api = original_data_api
        self.blueprint = Blueprint('data_api_ext', __name__)
        self._setup_extended_routes()
    
    def _setup_extended_routes(self):
        """Configurar rutas extendidas manteniendo compatibilidad"""
        
        @self.blueprint.route('/enhanced')
        def get_enhanced_data():
            """Endpoint mejorado con KPIs adicionales"""
            try:
                # Obtener datos base del API original si existe
                base_data = self._get_base_data()
                
                # Calcular KPIs mejorados
                enhanced_kpis = self._calculate_enhanced_kpis(base_data.get('productos', {}))
                
                # Generar insights
                insights = self._generate_insights(base_data.get('productos', {}), enhanced_kpis)
                
                # Combinar datos manteniendo estructura original
                response_data = {
                    **base_data,
                    'kpis_operacionales': enhanced_kpis,
                    'insights': insights,
                    'enhanced_features': True,
                    'version': '2.0'
                }
                
                return jsonify(response_data)
                
            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.blueprint.route('/kpis')
        def get_operational_kpis():
            """KPIs operacionales específicos"""
            try:
                base_data = self._get_base_data()
                products_data = base_data.get('productos', {})
                
                kpis = self._calculate_enhanced_kpis(products_data)
                
                return jsonify({
                    'kpis': kpis,
                    'timestamp': datetime.now().isoformat(),
                    'data_source': 'enhanced_analytics'
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.blueprint.route('/insights')
        def get_insights():
            """Insights y recomendaciones"""
            try:
                base_data = self._get_base_data()
                products_data = base_data.get('productos', {})
                kpis = self._calculate_enhanced_kpis(products_data)
                
                insights = self._generate_insights(products_data, kpis)
                
                return jsonify({
                    'insights': insights,
                    'timestamp': datetime.now().isoformat(),
                    'count': len(insights)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _get_base_data(self) -> Dict[str, Any]:
        """Obtener datos base del sistema actual"""
        try:
            # Intentar leer desde archivo de estado del sistema actual
            estado_files = [
                'data/estado_sistema.json',
                'data/json/estado_sistema.json',
                'estado_sistema.json'
            ]
            
            for file_path in estado_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # Datos simulados compatibles con el sistema actual
            return self._get_simulation_data()
            
        except Exception as e:
            print(f"Error leyendo datos base: {e}")
            return self._get_simulation_data()
    
    def _get_simulation_data(self) -> Dict[str, Any]:
        """Datos de simulación compatibles"""
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
    
    def _calculate_enhanced_kpis(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular KPIs mejorados manteniendo compatibilidad"""
        if not products_data:
            return {
                'efficiency_rate': 0.0,
                'throughput_rate': 0.0,
                'avg_cycle_time': 0.0,
                'bottleneck_stage': 'N/A',
                'oee_score': 0.0,
                'quality_score': 0.0
            }
        
        total = len(products_data)
        completados = sum(1 for p in products_data.values() if p.get('progreso', 0) == 100)
        progreso_promedio = sum(p.get('progreso', 0) for p in products_data.values()) / total if total > 0 else 0
        
        # Calcular KPIs operacionales
        efficiency_rate = round(progreso_promedio, 1)
        throughput_rate = round(completados * 2.5, 1)
        avg_cycle_time = round(120 - (progreso_promedio * 0.8), 1)
        
        # Identificar cuello de botella
        bottleneck_stage = self._identify_bottleneck(products_data)
        
        # OEE simulado
        oee_score = round(max(75, min(95, efficiency_rate + 10 + (completados * 5))), 1)
        
        # Calidad simulada
        quality_score = round(max(90, min(98, 96 - (total * 0.2))), 1)
        
        return {
            'efficiency_rate': efficiency_rate,
            'throughput_rate': throughput_rate,
            'avg_cycle_time': avg_cycle_time,
            'bottleneck_stage': bottleneck_stage,
            'oee_score': oee_score,
            'quality_score': quality_score,
            'calculation_timestamp': datetime.now().isoformat()
        }
    
    def _identify_bottleneck(self, products_data: Dict[str, Any]) -> str:
        """Identificar cuello de botella"""
        stage_counts = {}
        stage_names = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        }
        
        for product in products_data.values():
            stage = product.get('etapa_actual_numero', 1)
            if stage not in stage_counts:
                stage_counts[stage] = 0
            stage_counts[stage] += 1
        
        if not stage_counts:
            return 'N/A'
        
        # La etapa con más productos podría ser el cuello de botella
        bottleneck_stage = max(stage_counts.keys(), key=lambda x: stage_counts[x])
        return stage_names.get(bottleneck_stage, 'N/A')
    
    def _generate_insights(self, products_data: Dict[str, Any], kpis: Dict[str, Any]) -> list:
        """Generar insights automáticos"""
        insights = []
        
        efficiency = kpis.get('efficiency_rate', 0)
        
        # Insights basados en eficiencia
        if efficiency < 50:
            insights.append({
                'title': 'Oportunidad Crítica de Mejora',
                'text': f'La eficiencia actual ({efficiency}%) está por debajo del 50%. Considera revisar los procesos iniciales para optimizar el flujo.',
                'category': 'performance',
                'priority': 'high'
            })
        elif efficiency > 80:
            insights.append({
                'title': 'Excelente Rendimiento',
                'text': 'El sistema está funcionando con alta eficiencia. Mantén las buenas prácticas operativas actuales.',
                'category': 'opportunity',
                'priority': 'low'
            })
        
        # Insights de flujo
        if products_data:
            en_proceso = sum(1 for p in products_data.values() if 0 < p.get('progreso', 0) < 100)
            completados = sum(1 for p in products_data.values() if p.get('progreso', 0) == 100)
            
            if en_proceso > completados:
                insights.append({
                    'title': 'Análisis de Flujo',
                    'text': 'Hay más productos en proceso que completados. Considera balancear las cargas de trabajo entre etapas.',
                    'category': 'bottleneck',
                    'priority': 'medium'
                })
        
        # Insights de cuello de botella
        bottleneck = kpis.get('bottleneck_stage', 'N/A')
        if bottleneck != 'N/A':
            insights.append({
                'title': f'Atención Requerida: {bottleneck}',
                'text': f'La etapa {bottleneck} muestra concentración de productos. Monitorear para prevenir demoras.',
                'category': 'bottleneck',
                'priority': 'medium'
            })
        
        # Insights de tiempo de ciclo
        cycle_time = kpis.get('avg_cycle_time', 0)
        if cycle_time > 100:
            insights.append({
                'title': 'Optimización de Tiempo de Ciclo',
                'text': f'El tiempo de ciclo promedio es de {cycle_time}s. Identifica oportunidades para reducir tiempos muertos.',
                'category': 'performance',
                'priority': 'medium'
            })
        
        return insights
    
    def get_blueprint(self) -> Blueprint:
        """Obtener blueprint para registrar en la aplicación"""
        return self.blueprint


def extend_existing_data_api(app, existing_data_api=None):
    """
    Función para extender el DataAPI existente sin romper compatibilidad
    Se puede llamar desde app.py después de registrar el DataAPI original
    """
    try:
        # Crear extensión
        extension = DataAPIExtension(existing_data_api)
        
        # Registrar blueprint con prefijo diferente para evitar conflictos
        app.register_blueprint(
            extension.get_blueprint(), 
            url_prefix='/api/data'  # Se añadirán como /api/data/enhanced, etc.
        )
        
        print("✅ DataAPI Extension registrada exitosamente")
        return extension
        
    except Exception as e:
        print(f"❌ Error registrando DataAPI Extension: {e}")
        return None


# Función de compatibilidad para usar en app.py existente
def register_enhanced_endpoints(app):
    """
    Función simple para registrar endpoints mejorados en la app existente
    Uso: register_enhanced_endpoints(self.app) en WebApplication.__init__()
    """
    extension = DataAPIExtension()
    app.register_blueprint(extension.get_blueprint(), url_prefix='/api/data')
    return extension