#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONTROL API - API para control del sistema
Johnson Controls - Sistema de Seguimiento Industrial
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from typing import Dict, Any

from ...utils.logger import get_logger
from ...utils.config import config


class ControlAPI:
    """API de control del sistema"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.blueprint = Blueprint('control_api', __name__)
        self._setup_routes()
    
    def get_blueprint(self):
        """Obtener blueprint de Flask"""
        return self.blueprint
    
    def _setup_routes(self):
        """Configurar rutas de la API"""
        
        @self.blueprint.route('/simulate_scan', methods=['POST'])
        def simulate_scan():
            """Simular escaneo de código de barras"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos JSON requeridos'
                    }), 400
                
                barcode = data.get('barcode')
                if not barcode:
                    return jsonify({
                        'success': False,
                        'message': 'Código de barras requerido'
                    }), 400
                
                # Validar código de barras
                if not self._is_valid_jci_barcode(barcode):
                    return jsonify({
                        'success': False,
                        'message': f'Código de barras inválido: {barcode}'
                    }), 400
                
                # Enviar comando al scanner core
                success = self._send_scanner_command('simular_escaneo', {'codigo': barcode})
                
                if success:
                    self.logger.info(f"Simulación de escaneo enviada: {barcode}")
                    return jsonify({
                        'success': True,
                        'message': f'Simulación iniciada para {barcode}',
                        'timestamp': datetime.now().isoformat(),
                        'barcode': barcode
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando al scanner'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en simulate_scan: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/change_stage', methods=['POST'])
        def change_stage():
            """Cambiar etapa actual del sistema"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos JSON requeridos'
                    }), 400
                
                stage = data.get('stage')
                if stage is None:
                    return jsonify({
                        'success': False,
                        'message': 'Número de etapa requerido'
                    }), 400
                
                # Validar etapa
                if not isinstance(stage, int) or not (1 <= stage <= 6):
                    return jsonify({
                        'success': False,
                        'message': 'Etapa debe ser un número entre 1 y 6'
                    }), 400
                
                # Enviar comando al scanner core
                success = self._send_scanner_command('cambiar_etapa', {'etapa': stage})
                
                if success:
                    stage_names = {
                        1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
                        4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
                    }
                    
                    self.logger.info(f"Cambio de etapa enviado: {stage} ({stage_names[stage]})")
                    return jsonify({
                        'success': True,
                        'message': f'Etapa cambiada a {stage}: {stage_names[stage]}',
                        'stage': stage,
                        'stage_name': stage_names[stage],
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando al scanner'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en change_stage: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/reset_product', methods=['POST'])
        def reset_product():
            """Resetear producto a estado inicial"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos JSON requeridos'
                    }), 400
                
                barcode = data.get('barcode')
                if not barcode:
                    return jsonify({
                        'success': False,
                        'message': 'Código de barras requerido'
                    }), 400
                
                # Enviar comando al scanner core
                success = self._send_scanner_command('reset_producto', {'codigo': barcode})
                
                if success:
                    self.logger.info(f"Reset de producto enviado: {barcode}")
                    return jsonify({
                        'success': True,
                        'message': f'Producto {barcode} reseteado',
                        'barcode': barcode,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando al scanner'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en reset_product: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/emergency_stop', methods=['POST'])
        def emergency_stop():
            """Parada de emergencia del sistema"""
            try:
                reason = request.get_json().get('reason', 'Usuario') if request.get_json() else 'Usuario'
                
                # Enviar comando de parada de emergencia
                success = self._send_scanner_command('emergency_stop', {'reason': reason})
                
                if success:
                    self.logger.warning(f"Parada de emergencia activada por: {reason}")
                    return jsonify({
                        'success': True,
                        'message': 'Parada de emergencia activada',
                        'reason': reason,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando de parada'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en emergency_stop: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/system_restart', methods=['POST'])
        def system_restart():
            """Reiniciar sistema"""
            try:
                # Verificar autorización (en producción sería más robusto)
                auth_token = request.headers.get('Authorization')
                if not self._verify_admin_token(auth_token):
                    return jsonify({
                        'success': False,
                        'message': 'Autorización requerida para reiniciar sistema'
                    }), 401
                
                # Enviar comando de reinicio
                success = self._send_scanner_command('system_restart', {})
                
                if success:
                    self.logger.info("Reinicio del sistema solicitado")
                    return jsonify({
                        'success': True,
                        'message': 'Reinicio del sistema iniciado',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando de reinicio'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en system_restart: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/update_config', methods=['POST'])
        def update_config():
            """Actualizar configuración del sistema"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos de configuración requeridos'
                    }), 400
                
                # Validar configuración
                config_updates = data.get('config', {})
                if not self._validate_config_updates(config_updates):
                    return jsonify({
                        'success': False,
                        'message': 'Configuración inválida'
                    }), 400
                
                # Enviar comando de actualización de configuración
                success = self._send_scanner_command('update_config', {'config': config_updates})
                
                if success:
                    self.logger.info("Actualización de configuración enviada")
                    return jsonify({
                        'success': True,
                        'message': 'Configuración actualizada',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando actualización de configuración'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en update_config: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/test_scanner', methods=['POST'])
        def test_scanner():
            """Probar conexión del escáner"""
            try:
                # Enviar comando de prueba del escáner
                success = self._send_scanner_command('test_scanner', {})
                
                if success:
                    self.logger.info("Prueba de escáner enviada")
                    return jsonify({
                        'success': True,
                        'message': 'Prueba de escáner iniciada',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando comando de prueba'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en test_scanner: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
        
        @self.blueprint.route('/batch_operation', methods=['POST'])
        def batch_operation():
            """Ejecutar operación en lote"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': 'Datos de operación requeridos'
                    }), 400
                
                operation = data.get('operation')
                targets = data.get('targets', [])
                
                if not operation or not targets:
                    return jsonify({
                        'success': False,
                        'message': 'Operación y objetivos requeridos'
                    }), 400
                
                # Validar operación
                valid_operations = ['reset_all', 'advance_all', 'complete_all']
                if operation not in valid_operations:
                    return jsonify({
                        'success': False,
                        'message': f'Operación inválida. Válidas: {valid_operations}'
                    }), 400
                
                # Enviar comando de operación en lote
                success = self._send_scanner_command('batch_operation', {
                    'operation': operation,
                    'targets': targets
                })
                
                if success:
                    self.logger.info(f"Operación en lote enviada: {operation} para {len(targets)} objetivos")
                    return jsonify({
                        'success': True,
                        'message': f'Operación {operation} iniciada para {len(targets)} elementos',
                        'operation': operation,
                        'target_count': len(targets),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Error enviando operación en lote'
                    }), 500
                
            except Exception as e:
                self.logger.error(f"Error en batch_operation: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Error interno del servidor'
                }), 500
    
    def _send_scanner_command(self, command: str, parameters: Dict[str, Any]) -> bool:
        """Enviar comando al scanner core"""
        try:
            import json
            
            command_data = {
                'timestamp': datetime.now().isoformat(),
                'comando': command,
                'parametros': parameters,
                'procesado': False,
                'source': 'web_api'
            }
            
            # Guardar comando en archivo JSON
            commands_file = config.get_json_path('commands')
            commands_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(commands_file, 'w', encoding='utf-8') as f:
                json.dump(command_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Comando enviado: {command}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando comando {command}: {e}")
            return False
    
    def _is_valid_jci_barcode(self, barcode: str) -> bool:
        """Validar código de barras de Johnson Controls"""
        if not barcode or len(barcode) < 8:
            return False
        
        # Patrones de códigos JCI
        jci_patterns = ['JCI', 'HVAC', 'BATT', 'INT', 'SWT']
        
        # Verificar si contiene algún patrón JCI
        barcode_upper = barcode.upper()
        if any(pattern in barcode_upper for pattern in jci_patterns):
            return True
        
        # Verificar formato alfanumérico general
        return barcode.replace('-', '').replace('_', '').isalnum()
    
    def _verify_admin_token(self, auth_token: str) -> bool:
        """Verificar token de administrador (simplificado para prototipo)"""
        # En producción, esto sería más robusto con JWT, OAuth, etc.
        valid_tokens = ['admin_token_jci_2024', 'Bearer admin_token_jci_2024']
        return auth_token in valid_tokens
    
    def _validate_config_updates(self, config_updates: Dict[str, Any]) -> bool:
        """Validar actualizaciones de configuración"""
        try:
            # Validaciones básicas
            if not isinstance(config_updates, dict):
                return False
            
            # Validar claves permitidas
            allowed_keys = [
                'log_level', 'auto_update_interval', 'backup_enabled',
                'scanner_port', 'web_port', 'debug_mode'
            ]
            
            for key in config_updates:
                if key not in allowed_keys:
                    self.logger.warning(f"Clave de configuración no permitida: {key}")
                    return False
            
            # Validaciones específicas
            if 'log_level' in config_updates:
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
                if config_updates['log_level'] not in valid_levels:
                    return False
            
            if 'web_port' in config_updates:
                port = config_updates['web_port']
                if not isinstance(port, int) or not (1024 <= port <= 65535):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando configuración: {e}")
            return False