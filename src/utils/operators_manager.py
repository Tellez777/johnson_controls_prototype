"""
Gestor centralizado de operadores dinámicos
Proporciona funciones unificadas para cargar operadores desde múltiples fuentes
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from . import config

logger = logging.getLogger(__name__)


class OperatorsManager:
    """Gestor centralizado para operadores dinámicos"""
    
    def __init__(self):
        self.logger = logger
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = 30  # Cache por 30 segundos
    
    def get_all_operators(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Obtener todos los operadores de todas las fuentes (dinámico)
        
        Args:
            force_refresh: Forzar actualización del cache
            
        Returns:
            Dict con todos los operadores disponibles
        """
        # Verificar cache
        if not force_refresh and self._is_cache_valid():
            return self._cache.copy()
        
        try:
            # Combinar operadores de ambas fuentes
            operators = {}
            
            # 1. Cargar operadores desde stages_config.json (fuente primaria)
            stage_operators = self._load_operators_from_stages()
            operators.update(stage_operators)
            
            # 2. Cargar operadores adicionales desde sistema_estado.json
            state_operators = self._load_operators_from_state()
            operators.update(state_operators)
            
            # Actualizar cache
            self._cache = operators
            self._cache_timestamp = datetime.now()
            
            self.logger.info(f"OPERATORS_MANAGER: Cargados {len(operators)} operadores dinámicamente")
            return operators.copy()
            
        except Exception as e:
            self.logger.error(f"Error cargando operadores dinámicamente: {e}")
            return {}
    
    def get_operator_by_id(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un operador específico por ID"""
        operators = self.get_all_operators()
        return operators.get(operator_id)
    
    def get_operators_for_stage(self, stage_id: int) -> List[Dict[str, Any]]:
        """Obtener operadores que pueden trabajar en una etapa específica"""
        operators = self.get_all_operators()
        stage_operators = []
        
        for op_id, operator in operators.items():
            # Verificar si el operador tiene asignada esta etapa
            assigned_stages = operator.get('assigned_stages', [])
            for stage_info in assigned_stages:
                if stage_info.get('stage_id') == stage_id:
                    stage_operators.append(operator)
                    break
        
        return stage_operators
    
    def find_best_operator_for_stage(self, stage_id: int) -> Optional[Dict[str, Any]]:
        """Encontrar el mejor operador disponible para una etapa"""
        stage_operators = self.get_operators_for_stage(stage_id)
        
        # Filtrar por operadores activos
        active_operators = [op for op in stage_operators if op.get('active', True)]
        
        if active_operators:
            # Por ahora retornamos el primero, pero aquí se podría implementar
            # lógica más sofisticada (carga de trabajo, eficiencia, etc.)
            return active_operators[0]
        
        return None
    
    def _load_operators_from_stages(self) -> Dict[str, Any]:
        """Cargar operadores desde stages_config.json"""
        try:
            stages_file = config.get_data_path("json") / "stages_config.json"
            if not stages_file.exists():
                self.logger.warning(f"Archivo stages_config.json no existe: {stages_file}")
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
                    
                    # Verificar si ya existe (buscar por nombre para evitar duplicados)
                    existing_operator_id = None
                    for existing_id, existing_op in operators.items():
                        if existing_op['name'] == operator_name:
                            existing_operator_id = existing_id
                            break
                    
                    if existing_operator_id:
                        # Agregar esta etapa al operador existente
                        operators[existing_operator_id]['assigned_stages'].append({
                            'stage_id': stage['id'],
                            'stage_name': stage['name'],
                            'station_id': stage.get('station_id', '')
                        })
                    else:
                        # Crear nuevo operador
                        operators[operator_id] = {
                            'id': operator_id,
                            'name': operator_name,
                            'shift': 'Diurno',  # Valor por defecto
                            'stage_type': stage.get('stage_type', 'production'),
                            'station': stage.get('station_id', ''),
                            'active': True,
                            'assigned_stages': [{
                                'stage_id': stage['id'],
                                'stage_name': stage['name'],
                                'station_id': stage.get('station_id', '')
                            }],
                            'created_at': stage.get('created_at', datetime.now().isoformat()),
                            'updated_at': stage.get('updated_at', datetime.now().isoformat()),
                            'source': 'stages_config'
                        }
                        operator_counter += 1
                        
                        self.logger.debug(f"OPERATORS_FROM_STAGES: {operator_id} -> {operator_name}")
            
            return operators
            
        except Exception as e:
            self.logger.error(f"Error cargando operadores desde stages: {e}")
            return {}
    
    def _load_operators_from_state(self) -> Dict[str, Any]:
        """Cargar operadores adicionales desde sistema_estado.json"""
        try:
            state_file = config.get_data_path("json") / "sistema_estado.json"
            if not state_file.exists():
                return {}
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            state_operators = state_data.get('operadores', {})
            
            # Marcar operadores del estado con su fuente
            for op_id, operator in state_operators.items():
                operator['source'] = 'system_state'
                operator['active'] = operator.get('status') == 'active'
                
                # Asegurar que tenga la estructura esperada
                if 'assigned_stages' not in operator:
                    operator['assigned_stages'] = []
            
            self.logger.debug(f"OPERATORS_FROM_STATE: Cargados {len(state_operators)} operadores adicionales")
            return state_operators
            
        except Exception as e:
            self.logger.error(f"Error cargando operadores desde estado: {e}")
            return {}
    
    def _is_cache_valid(self) -> bool:
        """Verificar si el cache es válido"""
        if self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    def invalidate_cache(self):
        """Invalidar el cache para forzar recarga"""
        self._cache = {}
        self._cache_timestamp = None


# Instancia singleton
operators_manager = OperatorsManager()