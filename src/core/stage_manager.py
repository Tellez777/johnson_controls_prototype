#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STAGE MANAGER - Gestor central de etapas dinamicas
Johnson Controls - Sistema de Seguimiento Industrial
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.stage import DynamicStageManager, Stage, StageType
from ..utils.config import config
from ..utils.logger import get_logger


class StageManager:
    """Gestor central de etapas con persistencia"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.dynamic_manager = DynamicStageManager()
        self.config_file = Path("data/json/stages_config.json")
        
        # Cargar configuracion persistente si existe
        self.load_stages_config()
    
    def load_stages_config(self) -> bool:
        """Cargar configuracion de etapas desde archivo"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if self.dynamic_manager.import_stages(data):
                    self.logger.info(f"Configuracion de etapas cargada desde {self.config_file}")
                    return True
                else:
                    self.logger.warning("Error importando configuracion de etapas, usando default")
            else:
                self.logger.info("No existe configuracion de etapas, usando configuracion por defecto")
                self.save_stages_config()  # Guardar configuracion por defecto
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cargando configuracion de etapas: {e}")
            return False
    
    def save_stages_config(self) -> bool:
        """Guardar configuracion de etapas a archivo"""
        try:
            # Crear directorio si no existe
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = self.dynamic_manager.export_stages()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Configuracion de etapas guardada en {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error guardando configuracion de etapas: {e}")
            return False
    
    def get_all_stages(self) -> List[Dict[str, Any]]:
        """Obtener todas las etapas como diccionarios"""
        return [stage.to_dict() for stage in self.dynamic_manager.get_all_stages()]
    
    def get_active_stages(self) -> List[Dict[str, Any]]:
        """Obtener solo etapas activas como diccionarios"""
        return [stage.to_dict() for stage in self.dynamic_manager.get_active_stages()]
    
    def get_stage(self, stage_id: int) -> Optional[Dict[str, Any]]:
        """Obtener etapa por ID como diccionario"""
        stage = self.dynamic_manager.get_stage(stage_id)
        return stage.to_dict() if stage else None
    
    def get_stage_name(self, stage_id: int) -> str:
        """Obtener nombre de etapa por ID"""
        stage = self.dynamic_manager.get_stage(stage_id)
        return stage.name if stage else f"Etapa {stage_id}"
    
    def add_stage(self, name: str, description: str = "", stage_type: str = "custom",
                  operator_id: str = "", operator_name: str = "", station_id: str = "",
                  target_time_minutes: int = 30, quality_threshold: float = 85.0) -> Dict[str, Any]:
        """Agregar nueva etapa"""
        try:
            stage_type_enum = StageType(stage_type)
            stage = self.dynamic_manager.add_stage(
                name=name,
                description=description,
                stage_type=stage_type_enum,
                operator_id=operator_id,
                operator_name=operator_name,
                station_id=station_id,
                target_time_minutes=target_time_minutes,
                quality_threshold=quality_threshold
            )
            
            # Guardar cambios
            self.save_stages_config()
            
            self.logger.info(f"Nueva etapa agregada: {name} (ID: {stage.id})")
            return stage.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error agregando etapa: {e}")
            raise
    
    def update_stage(self, stage_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Actualizar etapa existente"""
        try:
            stage = self.dynamic_manager.update_stage(stage_id, **kwargs)
            if stage:
                self.save_stages_config()
                self.logger.info(f"Etapa actualizada: {stage.name} (ID: {stage_id})")
                return stage.to_dict()
            else:
                self.logger.warning(f"No se encontr� etapa con ID: {stage_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error actualizando etapa {stage_id}: {e}")
            raise
    
    def delete_stage(self, stage_id: int) -> bool:
        """Eliminar etapa"""
        try:
            stage = self.dynamic_manager.get_stage(stage_id)
            if not stage:
                self.logger.warning(f"No se encontr� etapa con ID: {stage_id}")
                return False
            
            stage_name = stage.name
            success = self.dynamic_manager.delete_stage(stage_id)
            
            if success:
                self.save_stages_config()
                self.logger.info(f"Etapa eliminada: {stage_name} (ID: {stage_id})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error eliminando etapa {stage_id}: {e}")
            return False
    
    def reorder_stages(self, stage_order: List[int]) -> bool:
        """Reordenar etapas"""
        try:
            success = self.dynamic_manager.reorder_stages(stage_order)
            if success:
                self.save_stages_config()
                self.logger.info(f"Etapas reordenadas: {stage_order}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error reordenando etapas: {e}")
            return False
    
    def get_next_stage(self, current_stage_id: int) -> Optional[Dict[str, Any]]:
        """Obtener siguiente etapa"""
        stage = self.dynamic_manager.get_next_stage(current_stage_id)
        return stage.to_dict() if stage else None
    
    def get_previous_stage(self, current_stage_id: int) -> Optional[Dict[str, Any]]:
        """Obtener etapa anterior"""
        stage = self.dynamic_manager.get_previous_stage(current_stage_id)
        return stage.to_dict() if stage else None
    
    def is_last_stage(self, stage_id: int) -> bool:
        """Verificar si es la ultima etapa"""
        return self.dynamic_manager.is_last_stage(stage_id)
    
    def is_first_stage(self, stage_id: int) -> bool:
        """Verificar si es la primera etapa"""
        return self.dynamic_manager.is_first_stage(stage_id)
    
    def get_stage_count(self) -> int:
        """Obtener numero total de etapas activas"""
        return self.dynamic_manager.get_stage_count()
    
    def validate_stage_id(self, stage_id: int) -> bool:
        """Validar si un ID de etapa es valido"""
        return self.dynamic_manager.validate_stage_id(stage_id)
    
    def get_stage_progression_info(self, current_stage_id: int) -> Dict[str, Any]:
        """Obtener informacion de progresion de etapa"""
        active_stages = self.dynamic_manager.get_active_stages()
        total_stages = len(active_stages)
        
        current_position = next((i + 1 for i, s in enumerate(active_stages) 
                               if s.id == current_stage_id), 0)
        
        return {
            'current_stage_id': current_stage_id,
            'current_position': current_position,
            'total_stages': total_stages,
            'progress_percentage': (current_position / total_stages * 100) if total_stages > 0 else 0,
            'is_first': self.is_first_stage(current_stage_id),
            'is_last': self.is_last_stage(current_stage_id),
            'next_stage': self.get_next_stage(current_stage_id),
            'previous_stage': self.get_previous_stage(current_stage_id)
        }
    
    def get_stages_summary(self) -> Dict[str, Any]:
        """Obtener resumen de etapas"""
        all_stages = self.dynamic_manager.get_all_stages()
        active_stages = self.dynamic_manager.get_active_stages()
        
        stage_types = {}
        for stage in all_stages:
            stage_type = stage.stage_type.value
            stage_types[stage_type] = stage_types.get(stage_type, 0) + 1
        
        return {
            'total_stages': len(all_stages),
            'active_stages': len(active_stages),
            'inactive_stages': len(all_stages) - len(active_stages),
            'stage_types': stage_types,
            'stages_by_type': {
                stage_type.value: [s.to_dict() for s in all_stages if s.stage_type == stage_type]
                for stage_type in StageType
            }
        }
    
    def reset_to_defaults(self) -> bool:
        """Resetear a configuracion por defecto"""
        try:
            # Crear nuevo gestor dinamico (carga defaults automaticamente)
            self.dynamic_manager = DynamicStageManager()
            
            # Guardar nueva configuracion
            self.save_stages_config()
            
            self.logger.info("Configuracion de etapas reseteada a valores por defecto")
            return True
            
        except Exception as e:
            self.logger.error(f"Error reseteando configuracion de etapas: {e}")
            return False
    
    def backup_configuration(self, backup_name: str = None) -> str:
        """Crear respaldo de la configuracion actual"""
        try:
            if not backup_name:
                backup_name = f"stages_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_file = Path("data/backup") / f"{backup_name}.json"
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = self.dynamic_manager.export_stages()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Respaldo de etapas creado: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Error creando respaldo: {e}")
            raise
    
    def restore_configuration(self, backup_file: str) -> bool:
        """Restaurar configuracion desde respaldo"""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                self.logger.error(f"Archivo de respaldo no existe: {backup_file}")
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if self.dynamic_manager.import_stages(data):
                self.save_stages_config()
                self.logger.info(f"Configuracion restaurada desde: {backup_file}")
                return True
            else:
                self.logger.error("Error importando configuracion de respaldo")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restaurando configuracion: {e}")
            return False


# Instancia global del gestor de etapas
global_stage_manager = StageManager()