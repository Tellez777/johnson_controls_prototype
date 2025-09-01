#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATA API - API para acceso a datos del sistema
Johnson Controls - Sistema de Seguimiento Industrial
"""

import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Any, Optional

from ...utils.logger import get_logger
from ...utils.config import config


class DataAPI:
    """API de datos del sistema"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.blueprint = Blueprint('data_api', __name__)
        self._setup_routes()
    
    def get_blueprint(self):
        """Obtener blueprint de Flask"""
        return self.blueprint
    
    def _setup_routes(self):
        """Configurar rutas de la API"""
        
        @self.blueprint.route('/system_state', methods=['GET'])
        def get_system_state():
            """Obtener estado completo del sistema"""
            try:
                state_data = self._load_system_state()
                
                if not state_data:
                    return jsonify({
                        'error': 'Estado del sistema no disponible',
                        'message': 'Scanner core no está ejecutándose',
                        'timestamp': datetime.now().isoformat()
                    }), 503
                
                # Agregar metadatos adicionales
                state_data['api_timestamp'] = datetime.now().isoformat()
                state_data['data_freshness'] = self._calculate_data_freshness(state_data)
                
                return jsonify(state_data)
                
            except Exception as e:
                self.logger.error(f"Error obteniendo estado del sistema: {e}")
                return jsonify({
                    'error': 'Error interno',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.blueprint.route('/products', methods=['GET'])
        def get_products():
            """Obtener lista de productos"""
            try:
                # Parámetros de filtrado
                status_filter = request.args.get('status')
                stage_filter = request.args.get('stage')
                limit = request.args.get('limit', type=int)
                
                state_data = self._load_system_state()
                if not state_data or 'products' not in state_data:
                    return jsonify({
                        'products': [],
                        'total': 0,
                        'filters_applied': {
                            'status': status_filter,
                            'stage': stage_filter,
                            'limit': limit
                        },
                        'timestamp': datetime.now().isoformat()
                    })
                
                products = list(state_data['products'].values())
                
                # Aplicar filtros
                if status_filter:
                    products = [p for p in products if p.get('status') == status_filter]
                
                if stage_filter:
                    stage_num = int(stage_filter)
                    products = [p for p in products if p.get('current_stage') == stage_num]
                
                # Aplicar límite
                if limit:
                    products = products[:limit]
                
                return jsonify({
                    'products': products,
                    'total': len(products),
                    'filters_applied': {
                        'status': status_filter,
                        'stage': stage_filter,
                        'limit': limit
                    },
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo productos: {e}")
                return jsonify({
                    'error': 'Error obteniendo productos',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/products/<barcode>', methods=['GET'])
        def get_product(barcode):
            """Obtener producto específico por código de barras"""
            try:
                state_data = self._load_system_state()
                
                if not state_data or 'products' not in state_data:
                    return jsonify({
                        'error': 'Datos no disponibles',
                        'barcode': barcode
                    }), 503
                
                product = state_data['products'].get(barcode)
                if not product:
                    return jsonify({
                        'error': 'Producto no encontrado',
                        'barcode': barcode,
                        'available_products': list(state_data['products'].keys())
                    }), 404
                
                # Agregar información adicional
                product['data_timestamp'] = datetime.now().isoformat()
                product['stage_progress'] = self._calculate_stage_progress(product)
                
                return jsonify(product)
                
            except Exception as e:
                self.logger.error(f"Error obteniendo producto {barcode}: {e}")
                return jsonify({
                    'error': 'Error interno',
                    'barcode': barcode,
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/statistics', methods=['GET'])
        def get_statistics():
            """Obtener estadísticas del sistema"""
            try:
                state_data = self._load_system_state()
                
                if not state_data:
                    return jsonify({
                        'error': 'Estadísticas no disponibles'
                    }), 503
                
                # Estadísticas básicas desde el estado
                basic_stats = state_data.get('statistics', {})
                
                # Calcular estadísticas adicionales
                products = state_data.get('products', {})
                advanced_stats = self._calculate_advanced_statistics(products)
                
                # Estadísticas de tiempo
                time_stats = self._calculate_time_statistics(products)
                
                return jsonify({
                    'basic': basic_stats,
                    'advanced': advanced_stats,
                    'time_analysis': time_stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo estadísticas: {e}")
                return jsonify({
                    'error': 'Error obteniendo estadísticas',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/stages/<int:stage_id>', methods=['GET'])
        def get_stage_info(stage_id):
            """Obtener información de etapa específica"""
            try:
                if not (1 <= stage_id <= 6):
                    return jsonify({
                        'error': 'ID de etapa inválido',
                        'valid_range': '1-6'
                    }), 400
                
                state_data = self._load_system_state()
                products = state_data.get('products', {}) if state_data else {}
                
                stage_info = self._analyze_stage(stage_id, products)
                
                return jsonify(stage_info)
                
            except Exception as e:
                self.logger.error(f"Error obteniendo info de etapa {stage_id}: {e}")
                return jsonify({
                    'error': 'Error obteniendo información de etapa',
                    'stage_id': stage_id,
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/export/excel', methods=['GET'])
        def export_excel():
            """Exportar datos a Excel"""
            try:
                # En una implementación completa, esto generaría y devolvería un archivo Excel
                # Por ahora, devolvemos información sobre la exportación
                
                state_data = self._load_system_state()
                if not state_data:
                    return jsonify({
                        'error': 'No hay datos para exportar'
                    }), 503
                
                export_info = {
                    'status': 'ready',
                    'total_products': len(state_data.get('products', {})),
                    'export_timestamp': datetime.now().isoformat(),
                    'available_formats': ['xlsx', 'csv'],
                    'download_url': '/api/data/download/latest_export.xlsx',
                    'message': 'Exportación lista para descarga'
                }
                
                return jsonify(export_info)
                
            except Exception as e:
                self.logger.error(f"Error exportando a Excel: {e}")
                return jsonify({
                    'error': 'Error en exportación',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/history', methods=['GET'])
        def get_history():
            """Obtener historial de datos"""
            try:
                # Parámetros de consulta
                hours = request.args.get('hours', 24, type=int)
                product_filter = request.args.get('product')
                
                # Simular historial (en implementación real vendría de base de datos)
                history_data = self._generate_mock_history(hours, product_filter)
                
                return jsonify({
                    'history': history_data,
                    'period_hours': hours,
                    'product_filter': product_filter,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo historial: {e}")
                return jsonify({
                    'error': 'Error obteniendo historial',
                    'message': str(e)
                }), 500
        
        @self.blueprint.route('/health', methods=['GET'])
        def data_health():
            """Verificar salud de los datos"""
            try:
                health_status = {
                    'status': 'healthy',
                    'checks': {
                        'state_file_exists': self._check_state_file(),
                        'data_is_recent': self._check_data_freshness(),
                        'products_loaded': self._check_products_loaded(),
                        'excel_file_accessible': self._check_excel_file()
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                # Determinar estado general
                all_healthy = all(health_status['checks'].values())
                health_status['status'] = 'healthy' if all_healthy else 'degraded'
                
                status_code = 200 if all_healthy else 503
                
                return jsonify(health_status), status_code
                
            except Exception as e:
                self.logger.error(f"Error verificando salud de datos: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
    
    def _load_system_state(self) -> Optional[Dict[str, Any]]:
        """Cargar estado del sistema desde archivo JSON"""
        try:
            state_file = config.get_json_path('state')
            
            if not state_file.exists():
                self.logger.warning(f"Archivo de estado no existe: {state_file}")
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Error cargando estado del sistema: {e}")
            return None
    
    def _calculate_data_freshness(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular frescura de los datos"""
        try:
            timestamp_str = state_data.get('timestamp')
            if not timestamp_str:
                return {'status': 'unknown', 'age_seconds': None}
            
            data_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age_seconds = (datetime.now() - data_timestamp).total_seconds()
            
            if age_seconds < 10:
                status = 'very_fresh'
            elif age_seconds < 30:
                status = 'fresh'
            elif age_seconds < 60:
                status = 'acceptable'
            else:
                status = 'stale'
            
            return {
                'status': status,
                'age_seconds': int(age_seconds),
                'last_update': timestamp_str
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando frescura de datos: {e}")
            return {'status': 'error', 'age_seconds': None}
    
    def _calculate_stage_progress(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular progreso por etapas de un producto"""
        try:
            stage_executions = product.get('stage_executions', {})
            
            progress = {
                'total_stages': 6,
                'completed_stages': 0,
                'current_stage': product.get('current_stage', 1),
                'stages_detail': {}
            }
            
            for stage_id in range(1, 7):
                stage_key = str(stage_id)
                stage_data = stage_executions.get(stage_key, {})
                
                is_completed = stage_data.get('status') == 'Completado'
                if is_completed:
                    progress['completed_stages'] += 1
                
                progress['stages_detail'][stage_id] = {
                    'completed': is_completed,
                    'duration': stage_data.get('duration_seconds', 0),
                    'quality': stage_data.get('quality_score', 0)
                }
            
            progress['completion_percentage'] = (progress['completed_stages'] / 6) * 100
            
            return progress
            
        except Exception as e:
            self.logger.error(f"Error calculando progreso de etapas: {e}")
            return {}
    
    def _calculate_advanced_statistics(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular estadísticas avanzadas"""
        try:
            if not products:
                return {}
            
            # Análisis por familia de productos
            family_stats = {}
            quality_scores = []
            cycle_times = []
            
            for product in products.values():
                # Estadísticas por familia
                family = product.get('product_family', 'Unknown')
                if family not in family_stats:
                    family_stats[family] = {'count': 0, 'completed': 0}
                
                family_stats[family]['count'] += 1
                if product.get('status') == 'Completado':
                    family_stats[family]['completed'] += 1
                
                # Calidad y tiempos
                quality_score = product.get('quality_score', 0)
                if quality_score > 0:
                    quality_scores.append(quality_score)
                
                cycle_time = product.get('total_cycle_time', 0)
                if cycle_time > 0:
                    cycle_times.append(cycle_time)
            
            # Cálculos estadísticos
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0
            
            return {
                'family_distribution': family_stats,
                'average_quality_score': round(avg_quality, 2),
                'average_cycle_time_seconds': round(avg_cycle_time, 0),
                'quality_analysis': self._analyze_quality_distribution(quality_scores),
                'performance_metrics': {
                    'products_analyzed': len(products),
                    'quality_samples': len(quality_scores),
                    'timing_samples': len(cycle_times)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando estadísticas avanzadas: {e}")
            return {}
    
    def _calculate_time_statistics(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular estadísticas de tiempo"""
        try:
            now = datetime.now()
            time_buckets = {
                'last_hour': [],
                'last_4_hours': [],
                'last_24_hours': [],
                'older': []
            }
            
            for product in products.values():
                last_updated_str = product.get('last_updated')
                if not last_updated_str:
                    time_buckets['older'].append(product)
                    continue
                
                try:
                    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                    age_hours = (now - last_updated).total_seconds() / 3600
                    
                    if age_hours <= 1:
                        time_buckets['last_hour'].append(product)
                    elif age_hours <= 4:
                        time_buckets['last_4_hours'].append(product)
                    elif age_hours <= 24:
                        time_buckets['last_24_hours'].append(product)
                    else:
                        time_buckets['older'].append(product)
                        
                except Exception:
                    time_buckets['older'].append(product)
            
            return {
                'activity_last_hour': len(time_buckets['last_hour']),
                'activity_last_4_hours': len(time_buckets['last_4_hours']),
                'activity_last_24_hours': len(time_buckets['last_24_hours']),
                'inactive_products': len(time_buckets['older']),
                'analysis_timestamp': now.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando estadísticas de tiempo: {e}")
            return {}
    
    def _analyze_stage(self, stage_id: int, products: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar etapa específica"""
        try:
            stage_names = {
                1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
                4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
            }
            
            stage_name = stage_names[stage_id]
            products_in_stage = []
            completed_in_stage = []
            
            for product in products.values():
                if product.get('current_stage') == stage_id:
                    products_in_stage.append(product)
                
                stage_executions = product.get('stage_executions', {})
                stage_data = stage_executions.get(str(stage_id), {})
                
                if stage_data.get('status') == 'Completado':
                    completed_in_stage.append({
                        'barcode': product.get('barcode'),
                        'duration': stage_data.get('duration_seconds', 0),
                        'quality': stage_data.get('quality_score', 0)
                    })
            
            # Calcular métricas de la etapa
            durations = [p['duration'] for p in completed_in_stage if p['duration'] > 0]
            qualities = [p['quality'] for p in completed_in_stage if p['quality'] > 0]
            
            return {
                'stage_id': stage_id,
                'stage_name': stage_name,
                'products_currently_in_stage': len(products_in_stage),
                'products_completed_stage': len(completed_in_stage),
                'average_duration_seconds': sum(durations) / len(durations) if durations else 0,
                'average_quality_score': sum(qualities) / len(qualities) if qualities else 0,
                'performance_metrics': {
                    'min_duration': min(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'quality_samples': len(qualities),
                    'duration_samples': len(durations)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando etapa {stage_id}: {e}")
            return {'error': str(e)}
    
    def _analyze_quality_distribution(self, quality_scores: List[float]) -> Dict[str, Any]:
        """Analizar distribución de calidad"""
        if not quality_scores:
            return {}
        
        excellent = sum(1 for score in quality_scores if score >= 95)
        good = sum(1 for score in quality_scores if 85 <= score < 95)
        acceptable = sum(1 for score in quality_scores if 75 <= score < 85)
        poor = sum(1 for score in quality_scores if score < 75)
        
        total = len(quality_scores)
        
        return {
            'excellent_count': excellent,
            'excellent_percentage': round(excellent / total * 100, 1),
            'good_count': good,
            'good_percentage': round(good / total * 100, 1),
            'acceptable_count': acceptable,
            'acceptable_percentage': round(acceptable / total * 100, 1),
            'poor_count': poor,
            'poor_percentage': round(poor / total * 100, 1)
        }
    
    def _generate_mock_history(self, hours: int, product_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Generar historial simulado"""
        history = []
        base_time = datetime.now() - timedelta(hours=hours)
        
        # Simular algunos eventos históricos
        for i in range(min(hours * 2, 50)):  # Máximo 50 eventos
            event_time = base_time + timedelta(minutes=i * (hours * 60 / 50))
            
            event = {
                'timestamp': event_time.isoformat(),
                'event_type': 'scan_completed',
                'product_barcode': f'JCI24000{(i % 3) + 1}{"A" if i % 3 == 0 else "B" if i % 3 == 1 else "C"}',
                'stage': (i % 6) + 1,
                'operator': f'OP00{(i % 3) + 1}',
                'quality_score': 95 + (i % 10) - 5,
                'duration_seconds': 60 + (i % 30)
            }
            
            # Aplicar filtro si se especifica
            if not product_filter or event['product_barcode'] == product_filter:
                history.append(event)
        
        return history
    
    def _check_state_file(self) -> bool:
        """Verificar si el archivo de estado existe"""
        return config.get_json_path('state').exists()
    
    def _check_data_freshness(self) -> bool:
        """Verificar si los datos están frescos"""
        try:
            state_data = self._load_system_state()
            if not state_data:
                return False
            
            freshness = self._calculate_data_freshness(state_data)
            return freshness['status'] in ['very_fresh', 'fresh', 'acceptable']
            
        except Exception:
            return False
    
    def _check_products_loaded(self) -> bool:
        """Verificar si hay productos cargados"""
        try:
            state_data = self._load_system_state()
            return bool(state_data and state_data.get('products'))
            
        except Exception:
            return False
    
    def _check_excel_file(self) -> bool:
        """Verificar acceso al archivo Excel"""
        try:
            excel_file = config.get_excel_path('data')
            return excel_file.exists()
            
        except Exception:
            return False