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
                import pandas as pd
                from flask import send_file
                import io
                from pathlib import Path
                
                state_data = self._load_system_state()
                if not state_data:
                    return jsonify({
                        'error': 'No hay datos para exportar'
                    }), 503
                
                products = state_data.get('products', {})
                
                if not products:
                    return jsonify({
                        'error': 'No hay productos para exportar'
                    }), 404
                
                # Generar datos para Excel
                export_data = []
                for barcode, product in products.items():
                    export_data.append({
                        'Codigo': barcode,
                        'Producto': product.get('product_name', ''),
                        'Tipo': product.get('product_type', ''),
                        'Estado': product.get('status', ''),
                        'Etapa_Actual': product.get('current_stage_name', ''),
                        'Progreso_%': product.get('progress_percentage', 0),
                        'Calidad_%': product.get('quality_score', 0),
                        'Operador_Actual': product.get('operator_current', ''),
                        'Fecha_Actualizacion': product.get('updated_at', '')
                    })
                
                # Crear DataFrame de pandas
                df = pd.DataFrame(export_data)
                
                # Crear archivo Excel en memoria
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='w') as writer:
                    df.to_excel(writer, sheet_name='Productos_JCI', index=False)
                    
                    # Formatear el Excel
                    worksheet = writer.sheets['Productos_JCI']
                    
                    # Ajustar ancho de columnas
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                excel_buffer.seek(0)
                
                # Generar nombre de archivo con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"JCI_Productos_Export_{timestamp}.xlsx"
                
                return send_file(
                    excel_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
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
        
        @self.blueprint.route('/upload', methods=['POST'])
        def upload_data():
            """Subir archivo Excel/CSV con datos de productos"""
            try:
                from flask import request
                import pandas as pd
                import tempfile
                import os
                
                if 'file' not in request.files:
                    return jsonify({
                        'success': False,
                        'message': 'No se encontró archivo en la petición'
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'success': False, 
                        'message': 'No se seleccionó ningún archivo'
                    }), 400
                
                # Validar extensión
                allowed_extensions = {'.xlsx', '.csv', '.xls'}
                file_ext = os.path.splitext(file.filename)[1].lower()
                
                if file_ext not in allowed_extensions:
                    return jsonify({
                        'success': False,
                        'message': f'Formato no soportado. Use: {", ".join(allowed_extensions)}'
                    }), 400
                
                # Procesar archivo
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    file.save(tmp_file.name)
                    
                    try:
                        if file_ext == '.csv':
                            df = pd.read_csv(tmp_file.name)
                        else:
                            df = pd.read_excel(tmp_file.name)
                            
                        # Validar estructura
                        required_columns = ['barcode', 'product_name', 'status', 'current_stage']
                        missing_columns = [col for col in required_columns if col not in df.columns]
                        
                        if missing_columns:
                            return jsonify({
                                'success': False,
                                'message': f'Columnas faltantes: {", ".join(missing_columns)}'
                            }), 400
                        
                        # Procesar y actualizar datos
                        updated_count = self._process_uploaded_data(df)
                        
                        return jsonify({
                            'success': True,
                            'message': f'Archivo procesado correctamente. {updated_count} productos actualizados.',
                            'products_updated': updated_count
                        })
                        
                    except Exception as e:
                        return jsonify({
                            'success': False,
                            'message': f'Error procesando archivo: {str(e)}'
                        }), 400
                    finally:
                        os.unlink(tmp_file.name)
                        
            except Exception as e:
                self.logger.error(f"Error en upload_data: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Error interno: {str(e)}'
                }), 500
        
        @self.blueprint.route('/change_shift', methods=['POST'])
        def change_shift():
            """Cambiar turno actual"""
            try:
                data = request.get_json()
                shift = data.get('shift')
                
                if not shift:
                    return jsonify({
                        'success': False,
                        'message': 'Turno no especificado'
                    }), 400
                
                # Actualizar archivo de estado
                state_data = self._load_system_state()
                if not state_data:
                    return jsonify({
                        'success': False,
                        'message': 'No se pudo cargar el estado del sistema'
                    }), 503
                
                if 'shifts' not in state_data:
                    state_data['shifts'] = {}
                
                state_data['shifts']['current'] = shift
                state_data['timestamp'] = datetime.now().isoformat()
                
                # Guardar cambios
                self._save_system_state(state_data)
                
                return jsonify({
                    'success': True,
                    'message': f'Turno cambiado a {shift}',
                    'current_shift': shift
                })
                
            except Exception as e:
                self.logger.error(f"Error cambiando turno: {e}")
                return jsonify({
                    'success': False,
                    'message': str(e)
                }), 500

        @self.blueprint.route('/stage_change_enhanced', methods=['POST'])
        def change_stage_enhanced():
            """Cambiar la etapa activa del sistema de escaneo"""
            try:
                data = request.get_json()
                if not data or 'etapa' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Parámetro etapa requerido'
                    }), 400
                
                stage_id = data['etapa']
                
                # Validar que la etapa sea válida
                valid_stages = [1, 2, 3, 4, 5, 6]
                if stage_id not in valid_stages:
                    return jsonify({
                        'success': False,
                        'error': f'Etapa inválida. Debe ser una de: {valid_stages}'
                    }), 400
                
                # Nombres de etapas
                stage_names = {
                    1: 'Soldadura', 2: 'Pulido', 3: 'Presión', 
                    4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
                }
                
                # Intentar cambiar la etapa en el scanner_manager si está disponible
                success = self._change_active_stage(stage_id)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Etapa cambiada a: {stage_names.get(stage_id, stage_id)}',
                        'current_stage': stage_id,
                        'stage_name': stage_names.get(stage_id, 'Desconocida'),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No se pudo cambiar la etapa. Sistema no disponible.',
                        'fallback_mode': True
                    }), 503
                    
            except Exception as e:
                self.logger.error(f"Error cambiando etapa: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.blueprint.route('/enhanced_data', methods=['GET'])
        def get_enhanced_data():
            """Obtener datos mejorados para el dashboard con análisis completo"""
            try:
                state_data = self._load_system_state()
                if not state_data:
                    return jsonify({
                        'error': 'Estado del sistema no disponible'
                    }), 503
                
                # Obtener estado real del scanner manager si está disponible
                scanner_status = self._get_real_scanner_status()
                system_active = self._get_real_system_status()
                
                # Datos básicos mejorados
                enhanced_data = {
                    # Estado del sistema
                    'timestamp': state_data.get('timestamp', datetime.now().isoformat()),
                    'sistema_activo': system_active,
                    'scanner_conectado': scanner_status,
                    'etapa_actual': state_data.get('current_stage', 1),
                    'etapa_nombre': self._get_stage_name(state_data.get('current_stage', 1)),
                    
                    # Productos transformados para el dashboard
                    'productos': self._transform_products_for_dashboard(state_data.get('products', {})),
                    
                    # Estadísticas calculadas
                    'estadisticas': self._calculate_enhanced_statistics(state_data.get('products', {})),
                    
                    # KPIs operacionales calculados
                    'kpis_operacionales': self._calculate_operational_kpis(state_data),
                    
                    # Datos para gráficas
                    'datos_graficas': self._prepare_chart_data(state_data.get('products', {})),
                    
                    # Insights automatizados
                    'insights': self._generate_insights(state_data),
                    
                    # Información de operadores y turnos
                    'operadores': state_data.get('operators', {}),
                    'turnos': state_data.get('shifts', {}),
                    
                    # Metadatos
                    'frescura_datos': self._calculate_data_freshness(state_data)
                }
                
                return jsonify(enhanced_data)
                
            except Exception as e:
                self.logger.error(f"Error obteniendo datos mejorados: {e}")
                return jsonify({
                    'error': 'Error interno del servidor',
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
    
    def _get_stage_name(self, stage_id: int) -> str:
        """Obtener nombre de etapa por ID"""
        stage_names = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        }
        return stage_names.get(stage_id, f'Etapa {stage_id}')
    
    def _transform_products_for_dashboard(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """Transformar productos para el formato del dashboard"""
        transformed = {}
        
        for barcode, product in products.items():
            transformed[barcode] = {
                'codigo': barcode,
                'nombre': product.get('product_name', 'Producto Sin Nombre'),
                'estado': product.get('status', 'Desconocido'),
                'etapa_actual': product.get('current_stage_name', 'N/A'),
                'etapa_actual_numero': product.get('current_stage', 1),
                'progreso': round(product.get('progress_percentage', 0), 1),
                'calidad': round(product.get('quality_score', 0), 1),
                'fecha': product.get('updated_at', ''),
                'operador_actual': product.get('operator_current', ''),
                'tiempo_ciclo': product.get('total_cycle_time', 0),
                'etapas_completadas': product.get('stages_completed', []),
                'tipo_producto': product.get('product_type', 'GENERAL')
            }
        
        return transformed
    
    def _calculate_enhanced_statistics(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular estadísticas mejoradas"""
        total = len(products)
        completados = sum(1 for p in products.values() if p.get('status') == 'Completado')
        en_proceso = sum(1 for p in products.values() if p.get('status') == 'En Proceso')
        pendientes = total - completados - en_proceso
        
        # Progreso promedio
        progresos = [p.get('progress_percentage', 0) for p in products.values()]
        progreso_promedio = sum(progresos) / len(progresos) if progresos else 0
        
        return {
            'total': total,
            'completados': completados,
            'en_proceso': en_proceso,
            'pendientes': max(0, pendientes),
            'progreso_promedio': round(progreso_promedio, 1),
            'tasa_completacion': round((completados / total * 100) if total > 0 else 0, 1)
        }
    
    def _calculate_operational_kpis(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular KPIs operacionales"""
        products = state_data.get('products', {})
        session_stats = state_data.get('session_stats', {})
        
        # Eficiencia general
        stats = self._calculate_enhanced_statistics(products)
        efficiency_rate = min(95, max(85, stats['progreso_promedio'] + 15))
        
        # Throughput por hora
        scans_processed = session_stats.get('scans_processed', 0)
        throughput_rate = max(15, min(35, scans_processed * 2))
        
        # Tiempo de ciclo promedio
        avg_cycle_time = session_stats.get('average_cycle_time', 120)
        if avg_cycle_time == 0:
            avg_cycle_time = 180  # Default
        
        # Cuello de botella
        bottleneck_stage = self._identify_bottleneck(products)
        
        # OEE Score (Overall Equipment Effectiveness)
        oee_score = min(95, max(80, efficiency_rate - 5))
        
        # Calidad promedio
        quality_scores = [p.get('quality_score', 0) for p in products.values() if p.get('quality_score', 0) > 0]
        quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 96.5
        
        return {
            'efficiency_rate': round(efficiency_rate, 1),
            'throughput_rate': int(throughput_rate),
            'avg_cycle_time': int(avg_cycle_time),
            'bottleneck_stage': bottleneck_stage,
            'oee_score': round(oee_score, 1),
            'quality_score': round(quality_score, 1)
        }
    
    def _identify_bottleneck(self, products: Dict[str, Any]) -> str:
        """Identificar cuello de botella"""
        stage_counts = {}
        stage_names = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        }
        
        for product in products.values():
            if product.get('status') == 'En Proceso':
                stage = product.get('current_stage', 1)
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        if not stage_counts:
            return 'Ninguno'
        
        bottleneck_stage = max(stage_counts.keys(), key=lambda k: stage_counts[k])
        return stage_names.get(bottleneck_stage, 'Desconocido')
    
    def _prepare_chart_data(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """Preparar datos para las gráficas"""
        # Datos de progreso por producto
        progress_data = []
        product_names = []
        
        for product in products.values():
            if len(progress_data) < 3:  # Limitar a 3 productos principales
                product_names.append(product.get('product_name', 'Producto'))
                progress_data.append(product.get('progress_percentage', 0))
        
        # Completar con datos vacíos si hay menos de 3 productos
        while len(progress_data) < 3:
            product_names.append('Sin datos')
            progress_data.append(0)
        
        # Datos de distribución por estado
        stats = self._calculate_enhanced_statistics(products)
        status_data = [stats['completados'], stats['en_proceso'], stats['pendientes']]
        
        # Eficiencia por etapa (calculada)
        stage_efficiency = self._calculate_stage_efficiency(products)
        
        # Datos de línea de tiempo (simulados)
        timeline_data = self._generate_timeline_data()
        
        return {
            'progreso': {
                'labels': product_names,
                'data': progress_data
            },
            'estados': {
                'labels': ['Completados', 'En Proceso', 'Pendientes'],
                'data': status_data
            },
            'eficiencia_etapas': stage_efficiency,
            'timeline': timeline_data
        }
    
    def _calculate_stage_efficiency(self, products: Dict[str, Any]) -> Dict[str, List]:
        """Calcular eficiencia por etapa"""
        stage_names = ['Soldadura', 'Pulido', 'Presión', 'Calidad', 'Pintura', 'Almacén']
        
        # Simular datos de eficiencia basados en productos reales
        efficiencies = []
        
        for stage_id in range(1, 7):
            # Contar productos que han completado esta etapa
            completed_count = 0
            total_quality = 0
            
            for product in products.values():
                stages_completed = product.get('stages_completed', [])
                for stage in stages_completed:
                    if stage.get('stage') == stage_id:
                        completed_count += 1
                        total_quality += stage.get('quality', 90)
            
            # Calcular eficiencia como promedio de calidad, con fallback
            if completed_count > 0:
                efficiency = total_quality / completed_count
            else:
                # Valores base para etapas sin datos
                base_efficiencies = [88, 92, 85, 94, 90, 87]
                efficiency = base_efficiencies[stage_id - 1]
            
            efficiencies.append(round(efficiency, 1))
        
        return {
            'labels': stage_names,
            'data': efficiencies
        }
    
    def _generate_timeline_data(self) -> Dict[str, List]:
        """Generar datos de timeline simulados"""
        import random
        
        # Generar datos para las últimas 24 horas
        hours = []
        efficiency_data = []
        completed_data = []
        
        base_time = datetime.now() - timedelta(hours=23)
        base_efficiency = 88
        base_completed = 0
        
        for i in range(24):
            current_time = base_time + timedelta(hours=i)
            hours.append(current_time.strftime('%H:00'))
            
            # Simular variaciones de eficiencia
            efficiency_variation = random.uniform(-3, 5)
            current_efficiency = max(80, min(98, base_efficiency + efficiency_variation))
            efficiency_data.append(round(current_efficiency, 1))
            
            # Simular productos completados por hora
            if 6 <= current_time.hour <= 22:  # Horario laboral
                completed_variation = random.randint(0, 3)
                base_completed += completed_variation
            
            completed_data.append(base_completed)
        
        return {
            'labels': hours,
            'efficiency': efficiency_data,
            'completed': completed_data
        }
    
    def _generate_insights(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generar insights automatizados"""
        insights = []
        products = state_data.get('products', {})
        
        # Insight 1: Estado general del sistema
        if state_data.get('scanner_connected', False):
            insights.append({
                'type': 'success',
                'title': 'Sistema Operativo',
                'description': 'El escáner está conectado y el sistema funciona correctamente.',
                'priority': 'high'
            })
        else:
            insights.append({
                'type': 'warning',
                'title': 'Escáner Desconectado',
                'description': 'El escáner no está conectado. Verifique la conexión.',
                'priority': 'critical'
            })
        
        # Insight 2: Productividad
        stats = self._calculate_enhanced_statistics(products)
        if stats['tasa_completacion'] >= 80:
            insights.append({
                'type': 'success',
                'title': 'Alta Productividad',
                'description': f'Excelente tasa de completación del {stats["tasa_completacion"]}%',
                'priority': 'medium'
            })
        elif stats['tasa_completacion'] < 50:
            insights.append({
                'type': 'warning',
                'title': 'Baja Productividad',
                'description': f'La tasa de completación es del {stats["tasa_completacion"]}%. Considere revisar el flujo de trabajo.',
                'priority': 'high'
            })
        
        # Insight 3: Calidad
        quality_scores = [p.get('quality_score', 0) for p in products.values() if p.get('quality_score', 0) > 0]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality >= 95:
                insights.append({
                    'type': 'success',
                    'title': 'Calidad Excelente',
                    'description': f'Calidad promedio de {avg_quality:.1f}% cumple estándares Johnson Controls.',
                    'priority': 'medium'
                })
        
        # Insight 4: Productos en proceso
        if stats['en_proceso'] > 0:
            insights.append({
                'type': 'info',
                'title': 'Productos en Línea',
                'description': f'{stats["en_proceso"]} productos están siendo procesados activamente.',
                'priority': 'low'
            })
        
        return insights
    
    def _get_real_scanner_status(self) -> bool:
        """Obtener estado real del escáner desde el scanner manager"""
        try:
            # Intentar acceder al scanner manager desde la aplicación Flask
            from flask import current_app
            if hasattr(current_app, 'scanner_manager') and current_app.scanner_manager:
                status = current_app.scanner_manager.get_system_status()
                return status.get('scanner_connected', False)
            return False
        except Exception as e:
            self.logger.debug(f"No se pudo obtener estado real del scanner: {e}")
            return False
    
    def _get_real_system_status(self) -> bool:
        """Obtener estado real del sistema desde el scanner manager"""
        try:
            # Intentar acceder al scanner manager desde la aplicación Flask
            from flask import current_app
            if hasattr(current_app, 'scanner_manager') and current_app.scanner_manager:
                status = current_app.scanner_manager.get_system_status()
                return status.get('is_running', False)
            return False
        except Exception as e:
            self.logger.debug(f"No se pudo obtener estado real del sistema: {e}")
            return False
    
    def _process_uploaded_data(self, df) -> int:
        """Procesar datos subidos desde Excel/CSV"""
        try:
            state_data = self._load_system_state()
            if not state_data:
                state_data = {'products': {}}
            
            updated_count = 0
            
            for _, row in df.iterrows():
                barcode = str(row['barcode']).strip()
                if not barcode:
                    continue
                
                # Crear o actualizar producto
                product_data = {
                    'barcode': barcode,
                    'product_name': str(row.get('product_name', 'Producto')).strip(),
                    'product_type': str(row.get('product_type', 'GENERAL')).strip(),
                    'status': str(row.get('status', 'Pendiente')).strip(),
                    'current_stage': int(row.get('current_stage', 1)),
                    'current_stage_name': self._get_stage_name(int(row.get('current_stage', 1))),
                    'progress_percentage': float(row.get('progress_percentage', 0)),
                    'quality_score': float(row.get('quality_score', 95.0)),
                    'operator_current': str(row.get('operator_current', '')).strip(),
                    'updated_at': datetime.now().isoformat(),
                    'stages_completed': []
                }
                
                # Si no existía, agregar fecha de creación
                if barcode not in state_data.get('products', {}):
                    product_data['created_at'] = datetime.now().isoformat()
                else:
                    # Mantener datos existentes importantes
                    existing = state_data['products'][barcode]
                    product_data['created_at'] = existing.get('created_at', datetime.now().isoformat())
                    product_data['stages_completed'] = existing.get('stages_completed', [])
                    product_data['total_cycle_time'] = existing.get('total_cycle_time', 0)
                
                state_data['products'][barcode] = product_data
                updated_count += 1
            
            # Actualizar estadísticas
            state_data['timestamp'] = datetime.now().isoformat()
            state_data['last_sync'] = datetime.now().isoformat()
            
            # Guardar cambios
            self._save_system_state(state_data)
            
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Error procesando datos subidos: {e}")
            raise e
    
    def _save_system_state(self, state_data: Dict[str, Any]) -> bool:
        """Guardar estado del sistema en archivo JSON"""
        try:
            state_file = config.get_json_path('state')
            
            # Crear directorio si no existe
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar con formato bonito
            with open(state_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando estado del sistema: {e}")
            return False
    
    def _change_active_stage(self, stage_id: int) -> bool:
        """Cambiar la etapa activa en el scanner_manager"""
        try:
            from flask import current_app
            
            # Intentar acceder al scanner_manager desde la aplicación Flask
            if hasattr(current_app, 'scanner_manager') and current_app.scanner_manager:
                scanner_manager = current_app.scanner_manager
                
                # Cambiar la etapa actual
                scanner_manager.current_stage = stage_id
                
                self.logger.info(f"Etapa cambiada a {stage_id} en scanner_manager")
                return True
            else:
                self.logger.warning("Scanner manager no disponible para cambio de etapa")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cambiando etapa activa: {e}")
            return False