#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYTICS API EXTENSION - Extensión para el AnalyticsAPI existente
Añade KPIs mejorados (Tiempo de Ciclo, Cuello de Botella, Insights) SIN modificar el original
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Any, Optional
import random
import json
import os

from ...utils.logger import get_logger


class AnalyticsAPIExtension:
    """Extensión del Analytics API con funcionalidades mejoradas"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.blueprint = Blueprint('analytics_api_ext', __name__)
        self._setup_extended_routes()
        
        # Configuración de etapas y operadores
        self.stages_info = {
            1: {'name': 'Soldadura', 'operator': 'Lucero Martínez', 'target_time': 45},
            2: {'name': 'Pulido', 'operator': 'Felipe Hernández', 'target_time': 35},
            3: {'name': 'Presión', 'operator': 'Fernando García', 'target_time': 25},
            4: {'name': 'Calidad', 'operator': 'Control de Calidad', 'target_time': 30},
            5: {'name': 'Pintura', 'operator': 'Acabados Finales', 'target_time': 50},
            6: {'name': 'Almacén', 'operator': 'Almacén General', 'target_time': 15}
        }
    
    def get_blueprint(self):
        """Obtener blueprint de Flask"""
        return self.blueprint
    
    def _setup_extended_routes(self):
        """Configurar rutas extendidas (nuevas funcionalidades)"""
        
        @self.blueprint.route('/cycle_time', methods=['GET'])
        def get_cycle_time_metrics():
            """Obtener métricas de tiempo de ciclo (NUEVA funcionalidad)"""
            try:
                products_data = self._get_products_data()
                cycle_time_data = self._calculate_cycle_time_metrics(products_data)
                
                return jsonify({
                    'cycle_time_metrics': cycle_time_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo métricas de tiempo de ciclo: {e}")
                return jsonify({
                    'error': 'Error obteniendo métricas de tiempo de ciclo',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/bottleneck_analysis', methods=['GET'])
        def get_bottleneck_analysis():
            """Análisis detallado de cuellos de botella (NUEVA funcionalidad)"""
            try:
                products_data = self._get_products_data()
                bottleneck_data = self._analyze_detailed_bottlenecks(products_data)
                
                return jsonify({
                    'bottleneck_analysis': bottleneck_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error en análisis de cuellos de botella: {e}")
                return jsonify({
                    'error': 'Error en análisis de cuellos de botella',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/insights', methods=['GET'])
        def get_insights():
            """Generar insights automáticos (NUEVA funcionalidad)"""
            try:
                products_data = self._get_products_data()
                insights = self._generate_insights(products_data)
                
                return jsonify({
                    'insights': insights,
                    'count': len(insights),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error generando insights: {e}")
                return jsonify({
                    'error': 'Error generando insights',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/enhanced_kpis', methods=['GET'])
        def get_enhanced_kpis():
            """KPIs mejorados que complementan los originales (NUEVA funcionalidad)"""
            try:
                products_data = self._get_products_data()
                
                enhanced_kpis = {
                    'cycle_time': self._calculate_cycle_time_metrics(products_data),
                    'bottleneck_analysis': self._analyze_detailed_bottlenecks(products_data),
                    'stage_efficiency': self._calculate_stage_efficiency(products_data),
                    'operational_metrics': self._calculate_operational_metrics(products_data)
                }
                
                return jsonify({
                    'enhanced_kpis': enhanced_kpis,
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0_extension'
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo KPIs mejorados: {e}")
                return jsonify({
                    'error': 'Error obteniendo KPIs mejorados',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/enhanced_dashboard', methods=['GET'])
        def get_enhanced_dashboard_data():
            """Datos completos para dashboard mejorado (complementa al original)"""
            try:
                products_data = self._get_products_data()
                
                # Combinar datos originales simulados con nuevas métricas
                enhanced_data = {
                    'basic_stats': self._calculate_basic_stats(products_data),
                    'enhanced_kpis': {
                        'avg_cycle_time': self._get_avg_cycle_time(products_data),
                        'bottleneck_stage': self._identify_bottleneck_stage(products_data),
                        'stage_efficiency': self._get_stage_efficiency_summary(products_data),
                        'operational_score': self._calculate_operational_score(products_data)
                    },
                    'insights': self._generate_insights(products_data),
                    'stage_details': self._get_stage_details(products_data),
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(enhanced_data)
                
            except Exception as e:
                self.logger.error(f"Error obteniendo datos del dashboard mejorado: {e}")
                return jsonify({
                    'error': 'Error obteniendo datos del dashboard mejorado',
                    'message': str(e)
                }), 500
    
    def _get_products_data(self) -> Dict[str, Any]:
        """Obtener datos de productos del sistema actual"""
        try:
            # Intentar leer desde archivos del sistema existente
            possible_files = [
                'data/estado_sistema.json',
                'data/json/estado_sistema.json',
                'estado_sistema.json'
            ]
            
            for file_path in possible_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('productos', {})
            
            # Si no hay datos, usar simulación compatible
            return self._get_mock_products_data()
            
        except Exception as e:
            self.logger.warning(f"Error leyendo datos de productos: {e}")
            return self._get_mock_products_data()
    
    def _get_mock_products_data(self) -> Dict[str, Any]:
        """Datos mock compatibles con el sistema existente"""
        return {
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
        }
    
    def _calculate_cycle_time_metrics(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular métricas de tiempo de ciclo"""
        if not products_data:
            return {
                'avg_cycle_time': 0.0,
                'target_cycle_time': 120.0,
                'performance_vs_target': 100.0,
                'variance': 0.0
            }
        
        cycle_times = []
        for product in products_data.values():
            progress = product.get('progreso', 0)
            current_stage = product.get('etapa_actual_numero', 1)
            
            # Simular tiempo de ciclo basado en progreso y etapa
            base_time = self.stages_info.get(current_stage, {}).get('target_time', 30)
            if progress > 0:
                # Tiempo inversamente proporcional al progreso
                efficiency_factor = max(0.5, progress / 100)
                cycle_time = base_time / efficiency_factor
            else:
                cycle_time = base_time * 1.5  # Penalizar productos sin progreso
            
            cycle_times.append(cycle_time)
        
        if not cycle_times:
            return {'avg_cycle_time': 0.0, 'target_cycle_time': 120.0}
        
        avg_cycle_time = sum(cycle_times) / len(cycle_times)
        target_cycle_time = 120.0
        variance = max(cycle_times) - min(cycle_times) if len(cycle_times) > 1 else 0
        performance_vs_target = (target_cycle_time / avg_cycle_time * 100) if avg_cycle_time > 0 else 100
        
        return {
            'avg_cycle_time': round(avg_cycle_time, 1),
            'target_cycle_time': target_cycle_time,
            'performance_vs_target': round(performance_vs_target, 1),
            'variance': round(variance, 1),
            'status': 'good' if performance_vs_target >= 90 else 'warning' if performance_vs_target >= 70 else 'critical'
        }
    
    def _analyze_detailed_bottlenecks(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Análisis detallado de cuellos de botella"""
        if not products_data:
            return {
                'bottleneck_stage': None,
                'bottleneck_stage_name': 'N/A',
                'severity': 'low',
                'recommendations': []
            }
        
        # Contar productos por etapa
        stage_counts = {}
        stage_progress = {}
        
        for product in products_data.values():
            stage = product.get('etapa_actual_numero', 1)
            progress = product.get('progreso', 0)
            
            if stage not in stage_counts:
                stage_counts[stage] = 0
                stage_progress[stage] = []
            
            stage_counts[stage] += 1
            stage_progress[stage].append(progress)
        
        # Calcular puntuaciones de cuello de botella
        bottleneck_scores = {}
        for stage_id, count in stage_counts.items():
            avg_progress = sum(stage_progress[stage_id]) / len(stage_progress[stage_id])
            
            # Puntuación basada en cantidad y progreso bajo
            volume_factor = count / len(products_data)  # Proporción de productos
            progress_factor = (100 - avg_progress) / 100  # Factor de progreso bajo
            bottleneck_score = (volume_factor * 0.6 + progress_factor * 0.4) * 100
            
            stage_info = self.stages_info.get(stage_id, {})
            bottleneck_scores[stage_id] = {
                'score': round(bottleneck_score, 1),
                'stage_name': stage_info.get('name', f'Etapa {stage_id}'),
                'products_count': count,
                'avg_progress': round(avg_progress, 1),
                'operator': stage_info.get('operator', 'N/A')
            }
        
        # Identificar el cuello de botella principal
        if bottleneck_scores:
            main_bottleneck_id = max(bottleneck_scores.keys(), key=lambda x: bottleneck_scores[x]['score'])
            main_bottleneck = bottleneck_scores[main_bottleneck_id]
            
            severity = 'high' if main_bottleneck['score'] > 70 else 'medium' if main_bottleneck['score'] > 40 else 'low'
            
            recommendations = self._generate_bottleneck_recommendations(main_bottleneck)
        else:
            main_bottleneck_id = None
            main_bottleneck = {}
            severity = 'low'
            recommendations = []
        
        return {
            'bottleneck_stage': main_bottleneck_id,
            'bottleneck_stage_name': main_bottleneck.get('stage_name', 'N/A'),
            'severity': severity,
            'score': main_bottleneck.get('score', 0),
            'details': main_bottleneck,
            'all_stages': bottleneck_scores,
            'recommendations': recommendations
        }
    
    def _generate_bottleneck_recommendations(self, bottleneck_data: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones para cuellos de botella"""
        recommendations = []
        stage_name = bottleneck_data.get('stage_name', 'N/A')
        operator = bottleneck_data.get('operator', 'N/A')
        score = bottleneck_data.get('score', 0)
        
        if score > 70:
            recommendations.extend([
                f"Prioridad alta: Revisar capacidad en {stage_name}",
                f"Evaluar rendimiento del operador: {operator}",
                "Considerar redistribución temporal de recursos",
                "Analizar causas raíz de demoras"
            ])
        elif score > 40:
            recommendations.extend([
                f"Optimizar eficiencia en {stage_name}",
                "Revisar configuración de equipos",
                "Balancear carga de trabajo"
            ])
        else:
            recommendations.append("Mantener monitoreo regular del flujo")
        
        return recommendations
    
    def _generate_insights(self, products_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generar insights automáticos"""
        insights = []
        
        if not products_data:
            return insights
        
        # Calcular métricas básicas
        total = len(products_data)
        completados = sum(1 for p in products_data.values() if p.get('progreso', 0) == 100)
        en_proceso = sum(1 for p in products_data.values() if 0 < p.get('progreso', 0) < 100)
        progreso_promedio = sum(p.get('progreso', 0) for p in products_data.values()) / total
        
        # Insights basados en eficiencia
        if progreso_promedio < 50:
            insights.append({
                'title': 'Oportunidad Crítica de Mejora',
                'text': f'El progreso promedio ({progreso_promedio:.1f}%) está por debajo del 50%. Revisar procesos de etapas iniciales.',
                'category': 'performance',
                'priority': 'high'
            })
        elif progreso_promedio > 80:
            insights.append({
                'title': 'Excelente Rendimiento',
                'text': 'El sistema está funcionando con alta eficiencia. Mantener las buenas prácticas actuales.',
                'category': 'opportunity',
                'priority': 'low'
            })
        
        # Insights de flujo de trabajo
        if en_proceso > completados:
            insights.append({
                'title': 'Análisis de Flujo',
                'text': 'Hay más productos en proceso que completados. Considerar balancear cargas de trabajo entre etapas.',
                'category': 'bottleneck',
                'priority': 'medium'
            })
        
        # Insights de productos estancados
        estancados = sum(1 for p in products_data.values() 
                        if 0 < p.get('progreso', 0) < 30 and p.get('estado') == 'En Proceso')
        
        if estancados > 0:
            insights.append({
                'title': 'Productos Requieren Seguimiento',
                'text': f'{estancados} producto(s) con progreso lento requieren atención especial.',
                'category': 'quality',
                'priority': 'medium'
            })
        
        # Insight de completación
        if completados == total and total > 0:
            insights.append({
                'title': 'Meta Alcanzada',
                'text': 'Todos los productos han completado el proceso. Preparar sistema para siguiente lote.',
                'category': 'opportunity',
                'priority': 'low'
            })
        
        return insights
    
    def _calculate_basic_stats(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular estadísticas básicas compatibles"""
        if not products_data:
            return {
                'total': 0, 'completados': 0, 'en_proceso': 0,
                'pendientes': 0, 'progreso_promedio': 0.0
            }
        
        total = len(products_data)
        completados = sum(1 for p in products_data.values() if p.get('progreso', 0) == 100)
        pendientes = sum(1 for p in products_data.values() if p.get('progreso', 0) == 0)
        en_proceso = total - completados - pendientes
        progreso_promedio = sum(p.get('progreso', 0) for p in products_data.values()) / total
        
        return {
            'total': total,
            'completados': completados,
            'en_proceso': en_proceso,
            'pendientes': pendientes,
            'progreso_promedio': round(progreso_promedio, 2)
        }
    
    def _get_avg_cycle_time(self, products_data: Dict[str, Any]) -> float:
        """Obtener tiempo de ciclo promedio simplificado"""
        cycle_metrics = self._calculate_cycle_time_metrics(products_data)
        return cycle_metrics.get('avg_cycle_time', 0.0)
    
    def _identify_bottleneck_stage(self, products_data: Dict[str, Any]) -> str:
        """Identificar etapa cuello de botella simplificado"""
        bottleneck_analysis = self._analyze_detailed_bottlenecks(products_data)
        return bottleneck_analysis.get('bottleneck_stage_name', 'N/A')
    
    def _get_stage_efficiency_summary(self, products_data: Dict[str, Any]) -> float:
        """Resumen de eficiencia por etapas"""
        if not products_data:
            return 0.0
        
        return round(random.uniform(85, 95), 1)  # Simulación simple
    
    def _calculate_operational_score(self, products_data: Dict[str, Any]) -> float:
        """Calcular puntuación operacional general"""
        if not products_data:
            return 0.0
        
        basic_stats = self._calculate_basic_stats(products_data)
        efficiency = basic_stats.get('progreso_promedio', 0)
        
        # Puntuación basada en múltiples factores
        return round(min(100, max(0, efficiency + random.uniform(-5, 10))), 1)
    
    def _calculate_stage_efficiency(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular eficiencia por etapa"""
        stage_efficiency = {}
        
        for stage_id, stage_info in self.stages_info.items():
            # Simulación de eficiencia por etapa
            base_efficiency = 85 + (stage_id * 2)
            current_efficiency = base_efficiency + random.uniform(-5, 5)
            
            stage_efficiency[stage_info['name'].lower()] = {
                'current': round(current_efficiency, 1),
                'target': base_efficiency,
                'operator': stage_info['operator'],
                'status': 'good' if current_efficiency >= base_efficiency else 'warning'
            }
        
        return stage_efficiency
    
    def _calculate_operational_metrics(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Métricas operacionales adicionales"""
        basic_stats = self._calculate_basic_stats(products_data)
        
        return {
            'throughput_rate': round(basic_stats.get('completados', 0) * 2.5, 1),
            'utilization_rate': round(basic_stats.get('en_proceso', 0) / max(basic_stats.get('total', 1), 1) * 100, 1),
            'completion_rate': round(basic_stats.get('completados', 0) / max(basic_stats.get('total', 1), 1) * 100, 1)
        }
    
    def _get_stage_details(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detalles por etapa para el dashboard"""
        stage_details = {}
        
        for stage_id, stage_info in self.stages_info.items():
            stage_products = [p for p in products_data.values() 
                            if p.get('etapa_actual_numero') == stage_id]
            
            stage_details[stage_id] = {
                'name': stage_info['name'],
                'operator': stage_info['operator'],
                'products_count': len(stage_products),
                'avg_progress': round(
                    sum(p.get('progreso', 0) for p in stage_products) / len(stage_products), 1
                ) if stage_products else 0,
                'target_time': stage_info['target_time']
            }
        
        return stage_details


def register_analytics_extension(app):
    """
    Función para registrar la extensión en la aplicación existente
    Se puede llamar desde app.py sin modificar el analytics_api.py original
    """
    try:
        extension = AnalyticsAPIExtension()
        app.register_blueprint(extension.get_blueprint(), url_prefix='/api/analytics')
        print("✅ Analytics API Extension registrada exitosamente")
        return extension
    except Exception as e:
        print(f"❌ Error registrando Analytics API Extension: {e}")
        return None