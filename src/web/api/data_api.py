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
from ...core.stage_manager import global_stage_manager


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
                if not global_stage_manager.validate_stage_id(stage_id):
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
                self.logger.info("ENDPOINT_DEBUG: stage_change_enhanced endpoint llamado")
                data = request.get_json()
                self.logger.info(f"ENDPOINT_DEBUG: Data recibida: {data}")
                if not data or 'etapa' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Parámetro etapa requerido'
                    }), 400
                
                stage_id = data['etapa']
                
                # Validar que la etapa sea válida
                active_stages = global_stage_manager.get_active_stages()
                valid_stages = [s['id'] for s in active_stages]
                if stage_id not in valid_stages:
                    return jsonify({
                        'success': False,
                        'error': f'Etapa inválida. Debe ser una de: {valid_stages}'
                    }), 400
                
                # Nombres de etapas
                stage_names = {s['id']: s['name'] for s in global_stage_manager.get_active_stages()}
                
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

        @self.blueprint.route('/stage_control', methods=['POST'])
        def stage_control():
            """NUEVO ENDPOINT - Control directo de etapa sin cache"""
            try:
                print("DIRECT_DEBUG: Endpoint stage_control ejecutado!")
                self.logger.error("DIRECT_DEBUG: Endpoint stage_control ejecutado!")
                
                data = request.get_json()
                print(f"DIRECT_DEBUG: Data: {data}")
                self.logger.error(f"DIRECT_DEBUG: Data: {data}")
                
                if not data or 'stage' not in data:
                    return jsonify({'success': False, 'error': 'stage parameter required'}), 400
                
                stage_id = int(data['stage'])
                print(f"DIRECT_DEBUG: Cambiando a etapa {stage_id}")
                self.logger.error(f"DIRECT_DEBUG: Cambiando a etapa {stage_id}")
                
                # Acceso directo al scanner manager
                from flask import current_app
                if hasattr(current_app, 'scanner_manager') and current_app.scanner_manager:
                    old_stage = current_app.scanner_manager.current_stage
                    current_app.scanner_manager.current_stage = stage_id
                    new_stage = current_app.scanner_manager.current_stage
                    
                    print(f"DIRECT_DEBUG: Etapa cambiada de {old_stage} a {new_stage}")
                    self.logger.error(f"DIRECT_DEBUG: Etapa cambiada de {old_stage} a {new_stage}")
                    
                    return jsonify({
                        'success': True, 
                        'old_stage': old_stage,
                        'new_stage': new_stage,
                        'stage_id': stage_id,
                        'message': f'Etapa cambiada a {stage_id}'
                    })
                else:
                    print("DIRECT_DEBUG: Scanner manager no encontrado")
                    self.logger.error("DIRECT_DEBUG: Scanner manager no encontrado")
                    return jsonify({'success': False, 'error': 'Scanner manager not found'}), 503
                    
            except Exception as e:
                print(f"DIRECT_DEBUG: Error: {e}")
                self.logger.error(f"DIRECT_DEBUG: Error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.blueprint.route('/stages', methods=['GET'])
        def get_stages():
            """Obtener lista de etapas configuradas"""
            try:
                stages = global_stage_manager.get_all_stages()
                active_stages = global_stage_manager.get_active_stages()
                
                return jsonify({
                    'success': True,
                    'stages': stages,
                    'active_stages': active_stages,
                    'total_stages': len(stages),
                    'active_count': len(active_stages)
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo etapas: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.blueprint.route('/stages', methods=['POST'])
        def add_stage():
            """Agregar nueva etapa al sistema"""
            try:
                data = request.get_json()
                
                if not data or 'name' not in data:
                    return jsonify({'success': False, 'error': 'Nombre de etapa requerido'}), 400
                
                stage_name = data['name'].strip()
                if not stage_name:
                    return jsonify({'success': False, 'error': 'Nombre de etapa no puede estar vacío'}), 400
                
                # Agregar etapa usando el gestor dinámico
                new_stage = global_stage_manager.add_stage(
                    name=stage_name,
                    description=data.get('description', ''),
                    stage_type=data.get('stage_type', 'custom'),
                    operator_id=data.get('operator_id', ''),
                    operator_name=data.get('operator_name', ''),
                    station_id=data.get('station_id', ''),
                    target_time_minutes=data.get('target_time_minutes', 30),
                    quality_threshold=data.get('quality_threshold', 85.0)
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Etapa "{stage_name}" agregada exitosamente',
                    'stage': new_stage,
                    'total_stages': global_stage_manager.get_stage_count()
                })
                
            except Exception as e:
                self.logger.error(f"Error agregando etapa: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.blueprint.route('/stages/<int:stage_id>', methods=['DELETE'])
        def delete_stage(stage_id):
            """Eliminar etapa del sistema (totalmente dinamico)"""
            try:
                # Verificar si la etapa existe
                stage_info = global_stage_manager.get_stage(stage_id)
                if not stage_info:
                    return jsonify({
                        'success': False, 
                        'error': f'Etapa con ID {stage_id} no encontrada'
                    }), 404
                
                # Reasignar productos de la etapa a eliminar a la primera etapa activa
                state_data = self._load_system_state()
                products = state_data.get('products', {})
                products_in_stage = [p for p in products.values() 
                                   if p.get('current_stage') == stage_id]
                
                if products_in_stage:
                    # Obtener la primera etapa activa como destino para reasignar productos
                    active_stages = global_stage_manager.get_active_stages()
                    target_stages = [s for s in active_stages if s['id'] != stage_id]
                    
                    if target_stages:
                        target_stage_id = target_stages[0]['id']
                        target_stage_name = target_stages[0]['name']
                        
                        # Reasignar productos a la primera etapa activa
                        for product in products_in_stage:
                            product['current_stage'] = target_stage_id
                            product['previous_stage'] = stage_id
                        
                        # Guardar estado actualizado
                        self._save_system_state(state_data)
                        
                        self.logger.info(f"Reasignados {len(products_in_stage)} productos de etapa {stage_id} a etapa {target_stage_id} ({target_stage_name})")
                    else:
                        return jsonify({
                            'success': False,
                            'error': 'No se puede eliminar la unica etapa activa del sistema'
                        }), 400
                
                # Usar el gestor dinámico para eliminar la etapa
                stage_name = stage_info['name']
                success = global_stage_manager.delete_stage(stage_id)
                
                if success:
                    message = f'Etapa "{stage_name}" eliminada exitosamente'
                    if products_in_stage:
                        message += f'. {len(products_in_stage)} productos fueron reasignados automáticamente'
                    
                    return jsonify({
                        'success': True,
                        'message': message,
                        'deleted_stage_id': stage_id,
                        'reassigned_products': len(products_in_stage) if products_in_stage else 0,
                        'total_stages': global_stage_manager.get_stage_count()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Error eliminando la etapa del sistema'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error eliminando etapa {stage_id}: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.blueprint.route('/stages/<int:stage_id>', methods=['PUT'])
        def update_stage(stage_id):
            """Actualizar información de una etapa"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({'success': False, 'error': 'Datos requeridos'}), 400
                
                # Cargar estado actual
                state_data = self._load_system_state()
                stages = state_data.get('stages', self._get_default_stages())
                
                # Buscar la etapa
                stage_to_update = None
                for stage in stages:
                    if stage['id'] == stage_id:
                        stage_to_update = stage
                        break
                
                if not stage_to_update:
                    return jsonify({
                        'success': False,
                        'error': f'Etapa con ID {stage_id} no encontrada'
                    }), 404
                
                # Actualizar campos permitidos
                if 'name' in data and data['name'].strip():
                    stage_to_update['name'] = data['name'].strip()
                
                if 'description' in data:
                    stage_to_update['description'] = data['description'].strip()
                
                if 'active' in data:
                    stage_to_update['active'] = bool(data['active'])
                
                stage_to_update['updated_at'] = datetime.now().isoformat()
                
                # Guardar cambios
                state_data['stages'] = stages
                state_data['timestamp'] = datetime.now().isoformat()
                self._save_system_state(state_data)
                
                return jsonify({
                    'success': True,
                    'message': f'Etapa actualizada exitosamente',
                    'stage': stage_to_update
                })
                
            except Exception as e:
                self.logger.error(f"Error actualizando etapa {stage_id}: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

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
                    'operadores': self._generate_operators_from_stages(),
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

        @self.blueprint.route('/operators', methods=['GET'])
        def get_operators():
            """Obtener lista de operadores"""
            try:
                # Usar el nuevo gestor unificado de operadores
                from ...utils.operators_manager import operators_manager
                operators = operators_manager.get_all_operators()
                
                return jsonify({
                    'success': True,
                    'operators': operators,
                    'total_operators': len(operators),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo operadores: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Error obteniendo operadores',
                    'message': str(e)
                }), 500

        @self.blueprint.route('/operators', methods=['POST'])
        def add_operator():
            """Agregar nuevo operador"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos del operador requeridos'
                    }), 400

                # Validar datos requeridos
                required_fields = ['name', 'shift', 'station']
                missing_fields = [field for field in required_fields if not data.get(field)]
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'message': f'Campos requeridos faltantes: {", ".join(missing_fields)}'
                    }), 400

                # Cargar estado actual
                state_data = self._load_system_state()
                operators = state_data.get('operadores', {})
                
                # Generar ID único para el operador (evita colisiones)
                existing_ids = set(operators.keys())
                counter = 1
                while f"OP{counter:03d}" in existing_ids:
                    counter += 1
                operator_id = f"OP{counter:03d}"
                
                # Crear nuevo operador
                new_operator = {
                    'id': operator_id,
                    'name': data['name'],
                    'shift': data['shift'],
                    'station': data['station'],
                    'status': data.get('status', 'active'),
                    'skills': data.get('skills', []),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                # Agregar campos opcionales si están presentes
                optional_fields = ['contact', 'certifications', 'performance_rating']
                for field in optional_fields:
                    if field in data:
                        new_operator[field] = data[field]
                
                operators[operator_id] = new_operator
                state_data['operadores'] = operators
                
                # Guardar cambios
                if self._save_system_state(state_data):
                    # Invalidar caché del gestor de operadores
                    from ...utils.operators_manager import operators_manager
                    operators_manager.invalidate_cache()
                    
                    self.logger.info(f"Operador {operator_id} agregado: {data['name']}")
                    return jsonify({
                        'success': True,
                        'message': f'Operador {data["name"]} agregado exitosamente',
                        'operator': new_operator
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error guardando operador'
                    }), 500
                    
            except Exception as e:
                import traceback
                self.logger.error(f"Error agregando operador: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor',
                    'error': str(e)
                }), 500

        @self.blueprint.route('/operators/<operator_id>', methods=['PUT'])
        def update_operator(operator_id):
            """Actualizar operador existente"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos del operador requeridos'
                    }), 400

                # Cargar estado actual
                state_data = self._load_system_state()
                operators = state_data.get('operadores', {})
                
                if operator_id not in operators:
                    return jsonify({
                        'success': False,
                        'message': 'Operador no encontrado'
                    }), 404

                # Actualizar operador
                operator = operators[operator_id]
                operator.update({
                    'name': data.get('name', operator['name']),
                    'shift': data.get('shift', operator['shift']),
                    'station': data.get('station', operator['station']),
                    'status': data.get('status', operator['status']),
                    'skills': data.get('skills', operator.get('skills', [])),
                    'updated_at': datetime.now().isoformat()
                })
                
                state_data['operadores'] = operators
                
                # Guardar cambios
                if self._save_system_state(state_data):
                    # Invalidar caché del gestor de operadores
                    from ...utils.operators_manager import operators_manager
                    operators_manager.invalidate_cache()
                    
                    self.logger.info(f"Operador {operator_id} actualizado")
                    return jsonify({
                        'success': True,
                        'message': f'Operador {operator["name"]} actualizado exitosamente',
                        'operator': operator
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error guardando cambios del operador'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Error actualizando operador: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500

        @self.blueprint.route('/operators/<operator_id>', methods=['DELETE'])
        def delete_operator(operator_id):
            """Eliminar operador"""
            try:
                # Cargar estado actual
                state_data = self._load_system_state()
                operators = state_data.get('operadores', {})
                
                if operator_id not in operators:
                    return jsonify({
                        'success': False,
                        'message': 'Operador no encontrado'
                    }), 404

                operator_name = operators[operator_id]['name']
                del operators[operator_id]
                state_data['operadores'] = operators
                
                # Guardar cambios
                if self._save_system_state(state_data):
                    # Invalidar caché del gestor de operadores
                    from ...utils.operators_manager import operators_manager
                    operators_manager.invalidate_cache()
                    
                    self.logger.info(f"Operador {operator_id} eliminado")
                    return jsonify({
                        'success': True,
                        'message': f'Operador {operator_name} eliminado exitosamente',
                        'deleted_operator_id': operator_id
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error eliminando operador'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Error eliminando operador: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500

        @self.blueprint.route('/products/reset', methods=['POST'])
        def reset_products():
            """Reiniciar productos a estado inicial para pruebas"""
            try:
                data = request.get_json() or {}
                
                # Obtener lista de productos a reiniciar
                products_to_reset = data.get('products', [])
                reset_all = data.get('reset_all', False)
                
                # Cargar estado actual
                state_data = self._load_system_state()
                if not state_data or 'products' not in state_data:
                    return jsonify({
                        'success': False,
                        'message': 'Error cargando datos del sistema'
                    }), 500
                
                reset_count = 0
                
                # Si reset_all es True, reiniciar todos los productos
                if reset_all:
                    products_to_reset = list(state_data['products'].keys())
                
                # Reiniciar productos especificados
                for barcode in products_to_reset:
                    if barcode in state_data['products']:
                        product = state_data['products'][barcode]
                        
                        # Reiniciar a estado inicial - usar primera etapa activa
                        active_stages = global_stage_manager.get_active_stages()
                        initial_stage = active_stages[0]['id'] if active_stages else 20
                        product['current_stage'] = initial_stage
                        product['progress_percentage'] = 0.0
                        product['status'] = 'Pendiente'
                        product['started_at'] = None
                        product['completed_at'] = None
                        product['last_updated'] = datetime.now().isoformat()
                        product['total_cycle_time'] = 0
                        product['efficiency_score'] = 0.0
                        product['quality_score'] = 100.0
                        
                        # Reiniciar todas las stage_executions
                        for stage_id in product.get('stage_executions', {}):
                            stage_exec = product['stage_executions'][stage_id]
                            stage_exec['status'] = 'No Iniciado'
                            stage_exec['start_time'] = None
                            stage_exec['end_time'] = None
                            stage_exec['duration_seconds'] = 0
                            stage_exec['quality_score'] = 100.0
                            stage_exec['defect_count'] = 0
                            stage_exec['notes'] = ''
                            stage_exec['operator_id'] = ''
                        
                        # Reiniciar stage_progress
                        product['stage_progress'] = {
                            'completed_stages': 0,
                            'completion_percentage': 0.0,
                            'current_stage': 1,
                            'stages_detail': {
                                str(stage_id): {
                                    'completed': False,
                                    'duration': 0,
                                    'quality': 100.0
                                } for stage_id in product.get('stage_executions', {})
                            },
                            'total_stages': len(product.get('stage_executions', {}))
                        }
                        
                        reset_count += 1
                        self.logger.info(f"Producto reiniciado: {barcode}")
                
                # Guardar cambios
                if self._save_system_state(state_data):
                    return jsonify({
                        'success': True,
                        'message': f'Se reiniciaron {reset_count} productos exitosamente',
                        'reset_count': reset_count,
                        'products_reset': products_to_reset
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error guardando cambios'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Error reiniciando productos: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor',
                    'error': str(e)
                }), 500
        
        @self.blueprint.route('/products', methods=['POST'])
        def create_product():
            """Crear nuevo producto en el sistema"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos JSON requeridos'
                    }), 400
                
                # Campos requeridos
                required_fields = ['barcode', 'product_name']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({
                            'success': False,
                            'message': f'Campo requerido: {field}'
                        }), 400
                
                barcode = data['barcode']
                
                # Cargar estado actual
                state_data = self._load_system_state()
                if not state_data:
                    return jsonify({
                        'success': False,
                        'message': 'Error cargando datos del sistema'
                    }), 500
                
                # Verificar que el producto no exista ya
                if 'products' in state_data and barcode in state_data['products']:
                    return jsonify({
                        'success': False,
                        'message': f'El producto {barcode} ya existe'
                    }), 409
                
                # Obtener etapa inicial dinámica (primera etapa activa)
                active_stages = global_stage_manager.get_active_stages()
                if not active_stages:
                    return jsonify({
                        'success': False,
                        'message': 'No hay etapas activas configuradas'
                    }), 500
                
                initial_stage = active_stages[0]['id']
                
                # Crear estructura del producto
                new_product = {
                    'barcode': barcode,
                    'product_name': data['product_name'],
                    'batch_number': data.get('batch_number', f'BTH-{barcode[-6:]}'),
                    'part_number': data.get('part_number', f'PART-{barcode}'),
                    'serial_number': data.get('serial_number', f'SN{barcode}'),
                    'work_order': data.get('work_order', f'WO-{datetime.now().strftime("%Y%m%d")}-{barcode[-4:]}'),
                    'product_family': data.get('product_family', 'Producto Personalizado'),
                    'customer_code': data.get('customer_code', 'CUSTOM'),
                    'specification': data.get('specification', f'JCI-SPEC-{barcode}-A'),
                    'revision': data.get('revision', 'Rev-A'),
                    'priority': data.get('priority', 'Normal'),
                    'current_stage': initial_stage,
                    'status': 'Pendiente',
                    'progress_percentage': 0.0,
                    'efficiency_score': 0.0,
                    'quality_score': 100.0,
                    'target_cycle_time': data.get('target_cycle_time', 300),
                    'total_cycle_time': 0,
                    'created_at': datetime.now().isoformat(),
                    'started_at': None,
                    'completed_at': None,
                    'last_updated': datetime.now().isoformat(),
                    'notes': data.get('notes', ''),
                    'tags': data.get('tags', [])
                }
                
                # Crear stage_executions dinámicamente para todas las etapas
                stages = global_stage_manager.get_active_stages()
                stage_executions = {}
                for stage in stages:
                    stage_executions[str(stage['id'])] = {
                        'stage_id': stage['id'],
                        'stage_name': stage['name'],
                        'operator_name': stage.get('operator_name', ''),
                        'operator_id': '',
                        'station_id': '',
                        'status': 'No Iniciado',
                        'start_time': None,
                        'end_time': None,
                        'duration_seconds': 0,
                        'quality_score': 100.0,
                        'defect_count': 0,
                        'notes': ''
                    }
                
                new_product['stage_executions'] = stage_executions
                
                # Agregar el producto al estado
                if 'products' not in state_data:
                    state_data['products'] = {}
                
                state_data['products'][barcode] = new_product
                state_data['last_updated'] = datetime.now().isoformat()
                
                # Guardar estado actualizado
                state_file = config.get_json_path('state')
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                
                # También actualizar el archivo Excel si existe
                self._update_excel_file(new_product)
                
                self.logger.info(f"Producto creado exitosamente: {barcode}")
                
                return jsonify({
                    'success': True,
                    'message': f'Producto {barcode} creado exitosamente',
                    'product': new_product,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                import traceback
                self.logger.error(f"Error creando producto: {e}")
                self.logger.error(f"Traceback completo: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor',
                    'error': str(e),
                    'traceback': traceback.format_exc()
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
                'total_stages': global_stage_manager.get_stage_count(),
                'completed_stages': 0,
                'current_stage': product.get('current_stage', 1),
                'stages_detail': {}
            }
            
            active_stages = global_stage_manager.get_active_stages()
            for stage_data in active_stages:
                stage_id = stage_data['id']
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
            
            total_stages = global_stage_manager.get_stage_count()
            progress['completion_percentage'] = (progress['completed_stages'] / total_stages * 100) if total_stages > 0 else 0
            
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
        
        stage_names = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión', 
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        }
        
        for barcode, product in products.items():
            # Detectar formato del producto
            if 'stage_executions' in product:
                # Formato nuevo (JCIProduct)
                current_stage = product.get('current_stage', 1)
                current_stage_name = stage_names.get(current_stage, f'Etapa {current_stage}')
                
                # Encontrar operador actual basado en la etapa actual
                current_operator = ''
                stage_executions = product.get('stage_executions', {})
                if str(current_stage) in stage_executions:
                    current_operator = stage_executions[str(current_stage)].get('operator_name', '')
                
                # Convertir stage_executions a stages_completed para compatibilidad
                stages_completed = []
                for stage_id, execution in stage_executions.items():
                    if execution.get('status') == 'Completado':
                        stages_completed.append({
                            'stage': int(stage_id),
                            'name': execution.get('stage_name', ''),
                            'completed_at': execution.get('end_time', ''),
                            'operator': execution.get('operator_name', ''),
                            'quality': execution.get('quality_score', 100.0)
                        })
                
                transformed[barcode] = {
                    'codigo': barcode,
                    'nombre': product.get('product_name', 'Producto Sin Nombre'),
                    'estado': product.get('status', 'Desconocido'),
                    'etapa_actual': current_stage_name,
                    'etapa_actual_numero': current_stage,
                    'progreso': round(product.get('progress_percentage', 0), 1),
                    'calidad': round(product.get('quality_score', 0), 1),
                    'fecha': product.get('last_updated', product.get('updated_at', '')),
                    'operador_actual': current_operator,
                    'tiempo_ciclo': product.get('total_cycle_time', 0),
                    'etapas_completadas': stages_completed,
                    'tipo_producto': product.get('product_family', product.get('product_type', 'GENERAL'))
                }
            else:
                # Formato anterior (compatible)
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
        """Calcular KPIs operacionales con datos reales del sistema"""
        products = state_data.get('products', {})
        session_stats = state_data.get('session_stats', {})
        scans_today = state_data.get('scans_today', [])
        
        stats = self._calculate_enhanced_statistics(products)
        
        # 1. EFICIENCIA REAL basada en productos completados vs tiempo esperado
        total_products = len(products)
        completed_products = stats['completados']
        in_progress_products = stats['en_proceso']
        
        # Calcular eficiencia basada en progreso real y metas
        if total_products > 0:
            completion_rate = (completed_products / total_products) * 100
            progress_efficiency = stats['progreso_promedio']
            efficiency_rate = (completion_rate * 0.6 + progress_efficiency * 0.4)
        else:
            efficiency_rate = 0
        
        # 2. THROUGHPUT REAL - productos procesados por hora
        scans_processed = len(scans_today) if scans_today else session_stats.get('scans_processed', 0)
        hours_active = self._calculate_active_hours(state_data)
        throughput_rate = (scans_processed / hours_active) if hours_active > 0 else 0
        
        # 3. TIEMPO DE CICLO basado en transiciones reales entre etapas
        avg_cycle_time = self._calculate_real_cycle_time(products)
        
        # 4. CUELLO DE BOTELLA identificado por productos acumulados
        bottleneck_stage, bottleneck_count = self._identify_detailed_bottleneck(products)
        
        # 5. OEE (Overall Equipment Effectiveness) mejorado
        # Availability = tiempo operativo / tiempo programado
        availability = min(100, (hours_active / 8) * 100) if hours_active > 0 else 0
        # Performance = throughput real / throughput target
        target_throughput = 25  # productos por hora objetivo
        performance = min(100, (throughput_rate / target_throughput) * 100) if target_throughput > 0 else 0
        # Quality = productos sin defectos / productos totales
        quality_rate = self._calculate_quality_rate(products)
        
        oee_score = (availability * performance * quality_rate) / 10000
        
        # 6. CALIDAD basada en productos con problemas
        quality_score = quality_rate
        
        # 7. KPIs adicionales útiles
        stage_efficiency = self._calculate_stage_efficiency(products)
        defect_rate = self._calculate_defect_rate(products)
        on_time_delivery = self._calculate_on_time_delivery(products)
        
        return {
            'efficiency_rate': round(efficiency_rate, 1),
            'throughput_rate': round(throughput_rate, 1),
            'avg_cycle_time': round(avg_cycle_time, 0),
            'bottleneck_stage': bottleneck_stage,
            'bottleneck_count': bottleneck_count,
            'oee_score': round(oee_score, 1),
            'quality_score': round(quality_score, 1),
            'availability': round(availability, 1),
            'performance': round(performance, 1),
            'stage_efficiency': stage_efficiency,
            'defect_rate': round(defect_rate, 2),
            'on_time_delivery': round(on_time_delivery, 1),
            'scans_processed_today': scans_processed,
            'active_hours': round(hours_active, 1)
        }
    
    def _calculate_active_hours(self, state_data: Dict[str, Any]) -> float:
        """Calcular horas activas del sistema hoy"""
        from datetime import datetime, timedelta
        
        # Obtener timestamp de inicio de sistema o usar 8 horas por defecto
        start_time = state_data.get('system_start_time')
        if start_time:
            try:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                now = datetime.now()
                hours_active = (now - start).total_seconds() / 3600
                return min(hours_active, 16)  # Máximo 16 horas por día
            except:
                pass
        return 1.0  # Default mínimo
    
    def _calculate_real_cycle_time(self, products: Dict[str, Any]) -> float:
        """Calcular tiempo de ciclo real basado en datos de productos"""
        cycle_times = []
        
        for product in products.values():
            # Calcular tiempo estimado basado en progreso y etapa actual
            progress = product.get('progress_percentage', 0)
            stage = product.get('current_stage', 1)
            
            if progress > 0:
                # Tiempo base por etapa (minutos)
                stage_times = {1: 45, 2: 60, 3: 35, 4: 25, 5: 80, 6: 15}
                base_time = stage_times.get(stage, 45)
                
                # Estimar tiempo transcurrido basado en progreso
                estimated_time = (progress / 100) * (base_time * stage / 6)
                cycle_times.append(estimated_time)
        
        if cycle_times:
            return sum(cycle_times) / len(cycle_times)
        return 180  # Default 3 horas
    
    def _identify_detailed_bottleneck(self, products: Dict[str, Any]) -> tuple:
        """Identificar cuello de botella detallado"""
        stage_counts = {}
        
        # Obtener etapas dinámicamente
        state_data = self._load_system_state()
        stages = state_data.get('stages', self._get_default_stages())
        stage_names = {stage['id']: stage['name'] for stage in stages}
        
        for product in products.values():
            if product.get('status') == 'En Proceso':
                stage = product.get('current_stage', 1)
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        if not stage_counts:
            return 'Ninguno', 0
        
        bottleneck_stage = max(stage_counts.keys(), key=lambda k: stage_counts[k])
        bottleneck_count = stage_counts[bottleneck_stage]
        stage_name = stage_names.get(bottleneck_stage, 'Desconocido')
        
        return stage_name, bottleneck_count
    
    def _calculate_quality_rate(self, products: Dict[str, Any]) -> float:
        """Calcular tasa de calidad real"""
        quality_scores = []
        
        for product in products.values():
            quality = product.get('quality_score', 0)
            if quality > 0:
                quality_scores.append(quality)
            else:
                # Asignar calidad basada en progreso y etapa
                progress = product.get('progress_percentage', 0)
                stage = product.get('current_stage', 1)
                
                # Productos en etapas tempranas tienen calidad más alta por defecto
                base_quality = max(85, 100 - (stage * 2) - (100 - progress) * 0.1)
                quality_scores.append(base_quality)
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 95.0
    
    def _calculate_stage_efficiency(self, products: Dict[str, Any]) -> Dict[str, float]:
        """Calcular eficiencia por etapa dinámicamente"""
        stage_data = {}
        
        # Obtener etapas dinámicamente
        state_data = self._load_system_state()
        stages = state_data.get('stages', self._get_default_stages())
        
        for stage in stages:
            stage_num = stage['id']
            stage_name = stage['name']
            
            products_in_stage = [p for p in products.values() 
                               if p.get('current_stage', 1) == stage_num]
            
            if products_in_stage:
                # Calcular eficiencia promedio para productos en esta etapa
                stage_progress = [p.get('progress_percentage', 0) for p in products_in_stage]
                efficiency = sum(stage_progress) / len(stage_progress)
            else:
                efficiency = 0
            
            stage_data[stage_name.lower()] = round(efficiency, 1)
        
        return stage_data
    
    def _calculate_defect_rate(self, products: Dict[str, Any]) -> float:
        """Calcular tasa de defectos"""
        total_products = len(products)
        if total_products == 0:
            return 0.0
        
        defective_products = 0
        for product in products.values():
            quality = product.get('quality_score', 95)
            # Considerar defectuoso si calidad < 85%
            if quality < 85:
                defective_products += 1
        
        return (defective_products / total_products) * 100
    
    def _calculate_on_time_delivery(self, products: Dict[str, Any]) -> float:
        """Calcular entrega a tiempo"""
        completed_products = [p for p in products.values() 
                            if p.get('status') == 'Completado']
        
        if not completed_products:
            return 0.0
        
        on_time_count = 0
        for product in completed_products:
            # Simular si se entregó a tiempo basado en tiempo de ciclo
            cycle_time = self._estimate_product_cycle_time(product)
            expected_time = 480  # 8 horas en minutos
            
            if cycle_time <= expected_time * 1.1:  # 10% de tolerancia
                on_time_count += 1
        
        return (on_time_count / len(completed_products)) * 100
    
    def _estimate_product_cycle_time(self, product: Dict[str, Any]) -> float:
        """Estimar tiempo de ciclo de un producto"""
        stage = product.get('current_stage', 6)
        # Tiempo base acumulado por etapas
        stage_times = {1: 45, 2: 105, 3: 140, 4: 165, 5: 245, 6: 260}
        return stage_times.get(stage, 260)
    
    def _identify_bottleneck(self, products: Dict[str, Any]) -> str:
        """Identificar cuello de botella (método legacy)"""
        stage_name, _ = self._identify_detailed_bottleneck(products)
        return stage_name
    
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
        """Generar insights inteligentes y oportunidades de mejora basados en datos reales"""
        insights = []
        products = state_data.get('products', {})
        stats = self._calculate_enhanced_statistics(products)
        kpis = self._calculate_operational_kpis(state_data)
        
        # 1. INSIGHTS DE SISTEMA Y CONECTIVIDAD
        scanner_connected = state_data.get('scanner_connected', False)
        if scanner_connected:
            insights.append({
                'type': 'success',
                'title': 'Sistema Operativo',
                'description': f'Escáner conectado. Throughput actual: {kpis["throughput_rate"]} productos/hora.',
                'priority': 'low',
                'action': None
            })
        else:
            insights.append({
                'type': 'error',
                'title': 'Sistema Desconectado',
                'description': 'El escáner está desconectado. Productividad: 0%.',
                'priority': 'critical',
                'action': 'Verificar conexión física del escáner en puerto COM5'
            })
        
        # 2. INSIGHTS DE PRODUCTIVIDAD Y EFICIENCIA
        efficiency = kpis.get('efficiency_rate', 0)
        if efficiency >= 90:
            insights.append({
                'type': 'success',
                'title': 'Alta Eficiencia',
                'description': f'Eficiencia excepcional del {efficiency}%. Sistema funcionando óptimamente.',
                'priority': 'low',
                'action': 'Mantener las prácticas actuales'
            })
        elif efficiency >= 75:
            insights.append({
                'type': 'info',
                'title': 'Eficiencia Buena',
                'description': f'Eficiencia del {efficiency}%. Oportunidad de mejora del {90-efficiency:.1f}%.',
                'priority': 'medium',
                'action': f'Optimizar etapa más lenta: {kpis["bottleneck_stage"]}'
            })
        elif efficiency >= 50:
            insights.append({
                'type': 'warning',
                'title': 'Eficiencia Baja',
                'description': f'Eficiencia del {efficiency}%. Impacto en entregas.',
                'priority': 'high',
                'action': f'Revisar urgentemente etapa: {kpis["bottleneck_stage"]}'
            })
        else:
            insights.append({
                'type': 'error',
                'title': 'Eficiencia Crítica',
                'description': f'Eficiencia del {efficiency}%. Sistema requiere intervención inmediata.',
                'priority': 'critical',
                'action': 'Parar producción y revisar procesos'
            })
        
        # 3. INSIGHTS DE CUELLOS DE BOTELLA
        bottleneck_stage = kpis.get('bottleneck_stage', 'Ninguno')
        bottleneck_count = kpis.get('bottleneck_count', 0)
        if bottleneck_count > 0:
            if bottleneck_count >= 3:
                insights.append({
                    'type': 'error',
                    'title': 'Cuello de Botella Crítico',
                    'description': f'{bottleneck_count} productos acumulados en etapa "{bottleneck_stage}". Flujo bloqueado.',
                    'priority': 'critical',
                    'action': f'Asignar recursos adicionales a etapa {bottleneck_stage}'
                })
            elif bottleneck_count >= 2:
                insights.append({
                    'type': 'warning',
                    'title': 'Cuello de Botella Detectado',
                    'description': f'{bottleneck_count} productos acumulados en "{bottleneck_stage}".',
                    'priority': 'high',
                    'action': f'Monitorear y optimizar etapa {bottleneck_stage}'
                })
        
        # 4. INSIGHTS DE CALIDAD
        quality_score = kpis.get('quality_score', 0)
        defect_rate = kpis.get('defect_rate', 0)
        if quality_score >= 98:
            insights.append({
                'type': 'success',
                'title': 'Calidad Excepcional',
                'description': f'Calidad del {quality_score:.1f}% supera estándares JCI (>95%).',
                'priority': 'low',
                'action': 'Documentar mejores prácticas actuales'
            })
        elif quality_score >= 95:
            insights.append({
                'type': 'info',
                'title': 'Calidad Excelente',
                'description': f'Calidad del {quality_score:.1f}% cumple estándares JCI.',
                'priority': 'low',
                'action': None
            })
        elif quality_score >= 90:
            insights.append({
                'type': 'warning',
                'title': 'Calidad Bajo Estándar',
                'description': f'Calidad del {quality_score:.1f}% por debajo del mínimo (95%). Defectos: {defect_rate:.1f}%',
                'priority': 'high',
                'action': 'Revisar procesos de control de calidad'
            })
        else:
            insights.append({
                'type': 'error',
                'title': 'Calidad Crítica',
                'description': f'Calidad del {quality_score:.1f}% inaceptable. Defectos: {defect_rate:.1f}%',
                'priority': 'critical',
                'action': 'Detener producción hasta resolver problemas de calidad'
            })
        
        # 5. INSIGHTS DE OEE (OVERALL EQUIPMENT EFFECTIVENESS)
        oee_score = kpis.get('oee_score', 0)
        availability = kpis.get('availability', 0)
        performance = kpis.get('performance', 0)
        if oee_score >= 85:
            insights.append({
                'type': 'success',
                'title': 'OEE Clase Mundial',
                'description': f'OEE del {oee_score:.1f}% es clase mundial (>85%). Disponibilidad: {availability:.1f}%, Rendimiento: {performance:.1f}%',
                'priority': 'low',
                'action': 'Mantener nivel de excelencia operacional'
            })
        elif oee_score >= 60:
            insights.append({
                'type': 'info',
                'title': 'OEE Aceptable',
                'description': f'OEE del {oee_score:.1f}% es aceptable. Oportunidad de mejora: {85-oee_score:.1f} puntos.',
                'priority': 'medium',
                'action': f'Mejorar factor más bajo: {"Disponibilidad" if availability < performance else "Rendimiento"}'
            })
        else:
            insights.append({
                'type': 'warning',
                'title': 'OEE Bajo',
                'description': f'OEE del {oee_score:.1f}% requiere mejora urgente (objetivo: >60%).',
                'priority': 'high',
                'action': 'Analizar pérdidas de disponibilidad y rendimiento'
            })
        
        # 6. INSIGHTS DE TIEMPO DE ENTREGA
        on_time_delivery = kpis.get('on_time_delivery', 0)
        if on_time_delivery >= 95:
            insights.append({
                'type': 'success',
                'title': 'Entregas Puntuales',
                'description': f'{on_time_delivery:.1f}% de entregas a tiempo. Excelente cumplimiento.',
                'priority': 'low',
                'action': None
            })
        elif on_time_delivery < 80:
            insights.append({
                'type': 'warning',
                'title': 'Retrasos en Entregas',
                'description': f'Solo {on_time_delivery:.1f}% de entregas a tiempo. Riesgo para clientes.',
                'priority': 'high',
                'action': 'Reducir tiempo de ciclo promedio'
            })
        
        # 7. OPORTUNIDADES ESPECÍFICAS
        # Analizar productos individuales para oportunidades
        products_stuck = [p for p in products.values() 
                         if p.get('progress_percentage', 0) < 50 and p.get('status') == 'En Proceso']
        if len(products_stuck) > 0:
            insights.append({
                'type': 'info',
                'title': 'Productos Estancados',
                'description': f'{len(products_stuck)} productos con progreso <50% necesitan atención.',
                'priority': 'medium',
                'action': 'Revisar productos con bajo progreso individual'
            })
        
        # 8. INSIGHTS DE TENDENCIAS (si hay datos históricos)
        scans_today = kpis.get('scans_processed_today', 0)
        active_hours = kpis.get('active_hours', 0)
        if scans_today > 0 and active_hours > 4:
            daily_rate = scans_today / active_hours * 8  # Proyección de 8 horas
            if daily_rate >= 100:
                insights.append({
                    'type': 'success',
                    'title': 'Tendencia Positiva',
                    'description': f'Proyección: {daily_rate:.0f} escaneos diarios. Ritmo excelente.',
                    'priority': 'low',
                    'action': None
                })
        
        # 9. RECOMENDACIONES OPERACIONALES
        if len(products) > 8:
            insights.append({
                'type': 'info',
                'title': 'Carga de Trabajo Alta',
                'description': f'{len(products)} productos en sistema. Considerar priorización.',
                'priority': 'medium',
                'action': 'Establecer prioridades por cliente o fecha de entrega'
            })
        
        return sorted(insights, key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x['priority']], reverse=True)
    
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
            self.logger.info(f"STAGE_CHANGE_DEBUG: Iniciando cambio de etapa a {stage_id}")
            from flask import current_app
            
            # Debug: Verificar current_app
            self.logger.debug(f"STAGE_CHANGE_DEBUG: current_app = {current_app}")
            self.logger.debug(f"STAGE_CHANGE_DEBUG: hasattr(current_app, 'scanner_manager') = {hasattr(current_app, 'scanner_manager')}")
            
            # Intentar acceder al scanner_manager desde la aplicación Flask
            if hasattr(current_app, 'scanner_manager') and current_app.scanner_manager:
                scanner_manager = current_app.scanner_manager
                
                # Debug: Estado antes del cambio
                old_stage = scanner_manager.current_stage
                self.logger.info(f"STAGE_CHANGE_DEBUG: Cambiando etapa de {old_stage} a {stage_id}")
                
                # Cambiar la etapa actual
                scanner_manager.current_stage = stage_id
                
                # Debug: Verificar el cambio
                new_stage = scanner_manager.current_stage
                self.logger.info(f"STAGE_CHANGE_DEBUG: Etapa cambiada exitosamente. Valor actual: {new_stage}")
                
                self.logger.info(f"Etapa cambiada a {stage_id} en scanner_manager")
                return True
            else:
                if hasattr(current_app, 'scanner_manager'):
                    self.logger.warning(f"STAGE_CHANGE_DEBUG: Scanner manager existe pero es None: {current_app.scanner_manager}")
                else:
                    self.logger.warning("STAGE_CHANGE_DEBUG: current_app no tiene atributo scanner_manager")
                self.logger.warning("Scanner manager no disponible para cambio de etapa")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cambiando etapa activa: {e}")
            self.logger.error(f"STAGE_CHANGE_DEBUG: Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"STAGE_CHANGE_DEBUG: Traceback: {traceback.format_exc()}")
            return False
    
    def _get_default_stages(self) -> List[Dict[str, Any]]:
        """Obtener etapas por defecto del sistema"""
        return [
            {
                'id': 1,
                'name': 'Soldadura',
                'description': 'Proceso de soldadura de componentes',
                'active': True,
                'is_default': True,
                'order': 1
            },
            {
                'id': 2,
                'name': 'Pulido',
                'description': 'Acabado y pulido de superficies',
                'active': True,
                'is_default': True,
                'order': 2
            },
            {
                'id': 3,
                'name': 'Presión',
                'description': 'Pruebas de presión y estanqueidad',
                'active': True,
                'is_default': True,
                'order': 3
            },
            {
                'id': 4,
                'name': 'Calidad',
                'description': 'Control y verificación de calidad',
                'active': True,
                'is_default': True,
                'order': 4
            },
            {
                'id': 5,
                'name': 'Pintura',
                'description': 'Aplicación de acabado final',
                'active': True,
                'is_default': True,
                'order': 5
            },
            {
                'id': 6,
                'name': 'Almacén',
                'description': 'Almacenamiento y preparación para envío',
                'active': True,
                'is_default': True,
                'order': 6
            }
        ]
    
    def _generate_operators_from_stages(self) -> Dict[str, Any]:
        """Generar operadores dinámicamente desde las etapas configuradas"""
        try:
            # Cargar etapas desde stages_config.json
            stages_file = config.get_data_path("json") / "stages_config.json"
            self.logger.info(f"DEBUG OPERADORES: Buscando archivo {stages_file}")
            if not stages_file.exists():
                self.logger.warning(f"DEBUG OPERADORES: Archivo no existe {stages_file}")
                return {}
            
            with open(stages_file, 'r', encoding='utf-8') as f:
                stages_data = json.load(f)
            
            operators = {}
            operator_counter = 1
            
            for stage in stages_data.get('stages', []):
                if stage.get('operator_name') and stage.get('operator_name').strip():
                    operator_name = stage['operator_name'].strip()
                    operator_id = stage.get('operator_id', '').strip()
                    
                    # Si no tiene operator_id, generar uno basado en el nombre
                    if not operator_id:
                        operator_id = f"OP{operator_counter:03d}"
                    
                    # Crear operador si no existe (buscar por nombre para evitar duplicados)
                    existing_operator_id = None
                    for existing_id, existing_op in operators.items():
                        if existing_op['name'] == operator_name:
                            existing_operator_id = existing_id
                            break
                    
                    if existing_operator_id:
                        # Usar operador existente
                        operator_id = existing_operator_id
                    else:
                        # Crear nuevo operador
                        operators[operator_id] = {
                            'id': operator_id,
                            'name': operator_name,
                            'station': stage.get('station_id', ''),
                            'shift': 'Diurno',  # Valor por defecto
                            'stage_type': stage.get('stage_type', 'production'),
                            'assigned_stages': [],
                            'active': stage.get('is_active', True),
                            'created_at': stage.get('created_at', datetime.now().isoformat()),
                            'updated_at': stage.get('updated_at', datetime.now().isoformat())
                        }
                        operator_counter += 1
                    
                    # Agregar etapa a la lista de etapas asignadas (evitar duplicados)
                    stage_already_assigned = any(
                        assigned_stage['stage_id'] == stage['id'] 
                        for assigned_stage in operators[operator_id]['assigned_stages']
                    )
                    if not stage_already_assigned:
                        operators[operator_id]['assigned_stages'].append({
                            'stage_id': stage['id'],
                            'stage_name': stage['name'],
                            'station_id': stage.get('station_id', '')
                        })
            
            self.logger.info(f"DEBUG OPERADORES: Generados {len(operators)} operadores desde etapas")
            for op_id, op_data in operators.items():
                self.logger.info(f"DEBUG OPERADORES: {op_id} -> {op_data['name']}")
            return operators
            
        except Exception as e:
            self.logger.error(f"Error generando operadores desde etapas: {e}")
            return {}
    
    def _update_excel_file(self, product: Dict[str, Any]):
        """Actualizar archivo Excel con nuevo producto (opcional)"""
        try:
            # Esta funcionalidad es opcional, se puede implementar posteriormente
            # si se desea mantener sincronizado el archivo Excel
            pass
        except Exception as e:
            self.logger.warning(f"No se pudo actualizar Excel con producto {product['barcode']}: {e}")
    
    def _check_state_file(self) -> bool:
        """Verificar que el archivo de estado existe"""
        try:
            state_file = config.get_json_path('state')
            return state_file.exists()
        except Exception:
            return False
    
    def _check_data_freshness(self) -> bool:
        """Verificar que los datos son recientes"""
        try:
            state_data = self._load_system_state()
            if not state_data:
                return False
            freshness = self._calculate_data_freshness(state_data)
            return freshness['status'] in ['very_fresh', 'fresh', 'acceptable']
        except Exception:
            return False
    
    def _check_products_loaded(self) -> bool:
        """Verificar que hay productos cargados"""
        try:
            state_data = self._load_system_state()
            if not state_data:
                return False
            return 'products' in state_data and len(state_data['products']) > 0
        except Exception:
            return False
    
    def _check_excel_file(self) -> bool:
        """Verificar que el archivo Excel es accesible"""
        try:
            excel_file = config.get_excel_path('main')
            return excel_file.exists()
        except Exception:
            return False