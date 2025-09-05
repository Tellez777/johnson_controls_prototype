#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STAGE MODEL - Modelo de etapa dinamica
Johnson Controls - Sistema de Seguimiento Industrial
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class StageType(Enum):
    """Tipo de etapa"""
    PRODUCTION = "production"
    QUALITY = "quality"
    ASSEMBLY = "assembly"
    FINISHING = "finishing"
    STORAGE = "storage"
    CUSTOM = "custom"


@dataclass
class Stage:
    """Modelo de etapa din�mica"""
    id: int
    name: str
    description: str = ""
    stage_type: StageType = StageType.PRODUCTION
    operator_id: str = ""
    operator_name: str = ""
    station_id: str = ""
    target_time_minutes: int = 30
    quality_threshold: float = 85.0
    is_active: bool = True
    is_required: bool = True
    order_position: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'stage_type': self.stage_type.value,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'station_id': self.station_id,
            'target_time_minutes': self.target_time_minutes,
            'quality_threshold': self.quality_threshold,
            'is_active': self.is_active,
            'is_required': self.is_required,
            'order_position': self.order_position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Stage':
        """Crear desde diccionario"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            stage_type=StageType(data.get('stage_type', 'production')),
            operator_id=data.get('operator_id', ''),
            operator_name=data.get('operator_name', ''),
            station_id=data.get('station_id', ''),
            target_time_minutes=data.get('target_time_minutes', 30),
            quality_threshold=data.get('quality_threshold', 85.0),
            is_active=data.get('is_active', True),
            is_required=data.get('is_required', True),
            order_position=data.get('order_position', 0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )


class DynamicStageManager:
    """Gestor de etapas din�micas"""
    
    def __init__(self):
        self.stages: Dict[int, Stage] = {}
        self._load_default_stages()
    
    def _load_default_stages(self):
        """Cargar etapas predeterminadas de Johnson Controls"""
        default_stages = [
            Stage(1, "Soldadura", "Proceso de soldadura", StageType.PRODUCTION, 
                  "OP001", "Lucero Mart�nez", "EST-SOL-01", 45),
            Stage(2, "Pulido", "Proceso de pulido", StageType.FINISHING, 
                  "OP002", "Felipe Hern�ndez", "EST-PUL-01", 60),
            Stage(3, "Presi�n", "Pruebas de presi�n", StageType.QUALITY, 
                  "OP003", "Fernando Garc�a", "EST-PRE-01", 35),
            Stage(4, "Calidad", "Control de calidad", StageType.QUALITY, 
                  "QC001", "Control de Calidad", "EST-CAL-01", 25),
            Stage(5, "Pintura", "Proceso de pintura", StageType.FINISHING, 
                  "OP004", "Acabados Finales", "EST-PIN-01", 80),
            Stage(6, "Almac�n", "Almacenamiento final", StageType.STORAGE, 
                  "WH001", "Almac�n General", "EST-ALM-01", 15)
        ]
        
        for stage in default_stages:
            stage.order_position = stage.id
            self.stages[stage.id] = stage
    
    def get_all_stages(self) -> List[Stage]:
        """Obtener todas las etapas ordenadas"""
        return sorted(self.stages.values(), key=lambda s: s.order_position)
    
    def get_active_stages(self) -> List[Stage]:
        """Obtener solo etapas activas ordenadas"""
        return sorted([s for s in self.stages.values() if s.is_active], 
                     key=lambda s: s.order_position)
    
    def get_stage(self, stage_id: int) -> Optional[Stage]:
        """Obtener etapa por ID"""
        return self.stages.get(stage_id)
    
    def get_stage_by_name(self, name: str) -> Optional[Stage]:
        """Obtener etapa por nombre"""
        for stage in self.stages.values():
            if stage.name.lower() == name.lower():
                return stage
        return None
    
    def add_stage(self, name: str, description: str = "", stage_type: StageType = StageType.CUSTOM,
                  operator_id: str = "", operator_name: str = "", station_id: str = "",
                  target_time_minutes: int = 30, quality_threshold: float = 85.0) -> Stage:
        """Agregar nueva etapa"""
        # Encontrar pr�ximo ID disponible
        new_id = max(self.stages.keys()) + 1 if self.stages else 1
        
        # Encontrar pr�xima posici�n
        max_position = max([s.order_position for s in self.stages.values()]) if self.stages else 0
        
        stage = Stage(
            id=new_id,
            name=name,
            description=description,
            stage_type=stage_type,
            operator_id=operator_id,
            operator_name=operator_name,
            station_id=station_id,
            target_time_minutes=target_time_minutes,
            quality_threshold=quality_threshold,
            order_position=max_position + 1
        )
        
        self.stages[new_id] = stage
        return stage
    
    def update_stage(self, stage_id: int, **kwargs) -> Optional[Stage]:
        """Actualizar etapa existente"""
        if stage_id not in self.stages:
            return None
        
        stage = self.stages[stage_id]
        
        # Actualizar campos permitidos
        allowed_fields = ['name', 'description', 'stage_type', 'operator_id', 'operator_name',
                         'station_id', 'target_time_minutes', 'quality_threshold', 'is_active',
                         'is_required', 'order_position']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'stage_type' and isinstance(value, str):
                    setattr(stage, field, StageType(value))
                else:
                    setattr(stage, field, value)
        
        stage.updated_at = datetime.now()
        return stage
    
    def delete_stage(self, stage_id: int) -> bool:
        """Eliminar etapa"""
        if stage_id in self.stages:
            del self.stages[stage_id]
            self._reorder_stages()
            return True
        return False
    
    def reorder_stages(self, stage_order: List[int]) -> bool:
        """Reordenar etapas"""
        if set(stage_order) != set(self.stages.keys()):
            return False
        
        for position, stage_id in enumerate(stage_order, 1):
            if stage_id in self.stages:
                self.stages[stage_id].order_position = position
                self.stages[stage_id].updated_at = datetime.now()
        
        return True
    
    def _reorder_stages(self):
        """Reordenar posiciones despu�s de eliminaci�n"""
        sorted_stages = sorted(self.stages.values(), key=lambda s: s.order_position)
        for position, stage in enumerate(sorted_stages, 1):
            stage.order_position = position
    
    def get_next_stage(self, current_stage_id: int) -> Optional[Stage]:
        """Obtener siguiente etapa activa"""
        current_stage = self.get_stage(current_stage_id)
        if not current_stage:
            return None
        
        active_stages = self.get_active_stages()
        current_index = next((i for i, s in enumerate(active_stages) if s.id == current_stage_id), -1)
        
        if current_index != -1 and current_index < len(active_stages) - 1:
            return active_stages[current_index + 1]
        
        return None
    
    def get_previous_stage(self, current_stage_id: int) -> Optional[Stage]:
        """Obtener etapa anterior activa"""
        current_stage = self.get_stage(current_stage_id)
        if not current_stage:
            return None
        
        active_stages = self.get_active_stages()
        current_index = next((i for i, s in enumerate(active_stages) if s.id == current_stage_id), -1)
        
        if current_index > 0:
            return active_stages[current_index - 1]
        
        return None
    
    def is_last_stage(self, stage_id: int) -> bool:
        """Verificar si es la �ltima etapa activa"""
        active_stages = self.get_active_stages()
        return len(active_stages) > 0 and active_stages[-1].id == stage_id
    
    def is_first_stage(self, stage_id: int) -> bool:
        """Verificar si es la primera etapa activa"""
        active_stages = self.get_active_stages()
        return len(active_stages) > 0 and active_stages[0].id == stage_id
    
    def get_stage_count(self) -> int:
        """Obtener n�mero total de etapas activas"""
        return len([s for s in self.stages.values() if s.is_active])
    
    def validate_stage_id(self, stage_id: int) -> bool:
        """Validar si un ID de etapa es v�lido y activo"""
        stage = self.get_stage(stage_id)
        return stage is not None and stage.is_active
    
    def export_stages(self) -> Dict[str, Any]:
        """Exportar configuraci�n de etapas"""
        return {
            'stages': [stage.to_dict() for stage in self.get_all_stages()],
            'metadata': {
                'total_stages': len(self.stages),
                'active_stages': len(self.get_active_stages()),
                'exported_at': datetime.now().isoformat()
            }
        }
    
    def import_stages(self, data: Dict[str, Any]) -> bool:
        """Importar configuraci�n de etapas"""
        try:
            stages_data = data.get('stages', [])
            new_stages = {}
            
            for stage_data in stages_data:
                stage = Stage.from_dict(stage_data)
                new_stages[stage.id] = stage
            
            self.stages = new_stages
            self._reorder_stages()
            return True
        except Exception:
            return False


# Instancia global del gestor de etapas
stage_manager = DynamicStageManager()