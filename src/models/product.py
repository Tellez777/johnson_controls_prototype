#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRODUCT MODELS - Modelos de productos para Johnson Controls
Sistema de Seguimiento Industrial
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class ProductStatus(Enum):
    """Estados posibles del producto"""
    PENDING = "Pendiente"
    IN_PROGRESS = "En Proceso"
    COMPLETED = "Completado"
    ON_HOLD = "En Espera"
    REJECTED = "Rechazado"
    REWORK = "Retrabajo"


class StageStatus(Enum):
    """Estados de una etapa específica"""
    NOT_STARTED = "No Iniciado"
    IN_PROGRESS = "En Proceso"
    COMPLETED = "Completado"
    SKIPPED = "Omitido"
    FAILED = "Falló"


@dataclass
class QualityMetrics:
    """Métricas de calidad para un producto"""
    defect_count: int = 0
    rework_count: int = 0
    quality_score: float = 100.0
    inspector_id: str = ""
    inspection_notes: str = ""
    passed_inspection: bool = True


@dataclass
class StageExecution:
    """Ejecución de una etapa específica"""
    stage_id: int
    stage_name: str
    operator_id: str
    operator_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    status: StageStatus = StageStatus.NOT_STARTED
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)
    notes: str = ""
    station_id: str = ""
    
    def start_stage(self, operator_id: str, operator_name: str, station_id: str = ""):
        """Iniciar la etapa"""
        self.start_time = datetime.now()
        self.operator_id = operator_id
        self.operator_name = operator_name
        self.station_id = station_id
        self.status = StageStatus.IN_PROGRESS
    
    def complete_stage(self, quality_metrics: Optional[QualityMetrics] = None):
        """Completar la etapa"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
        
        if quality_metrics:
            self.quality_metrics = quality_metrics
        
        self.status = StageStatus.COMPLETED
    
    def fail_stage(self, reason: str = ""):
        """Marcar etapa como fallida"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
        
        self.status = StageStatus.FAILED
        self.notes = reason


@dataclass
class JCIProduct:
    """Modelo completo de producto para Johnson Controls"""
    
    # Identificación básica
    barcode: str
    part_number: str
    product_name: str
    product_family: str
    
    # Información de manufactura
    work_order: str
    batch_number: str
    serial_number: str
    customer_code: str
    
    # Control de calidad
    revision: str
    specification: str
    target_cycle_time: int  # segundos
    
    # Estado del producto
    status: ProductStatus = ProductStatus.PENDING
    progress_percentage: float = 0.0
    current_stage: int = 1
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Ejecución de etapas
    stage_executions: Dict[int, StageExecution] = field(default_factory=dict)
    
    # Métricas generales
    total_cycle_time: int = 0
    efficiency_score: float = 0.0
    quality_score: float = 100.0
    
    # Información adicional
    priority: str = "Normal"  # Normal, High, Critical
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Inicialización post-creación"""
        if not self.stage_executions:
            # Inicializar las 6 etapas estándar de Johnson Controls
            self._initialize_stages()
    
    def _initialize_stages(self):
        """Inicializar las etapas del proceso"""
        jci_stages = [
            (1, "Soldadura", "OP001", "Lucero Martínez"),
            (2, "Pulido", "OP002", "Felipe Hernández"),
            (3, "Presión", "OP003", "Fernando García"),
            (4, "Calidad", "QC001", "Control de Calidad"),
            (5, "Pintura", "OP004", "Acabados Finales"),
            (6, "Almacén", "WH001", "Almacén General")
        ]
        
        for stage_id, stage_name, op_id, op_name in jci_stages:
            self.stage_executions[stage_id] = StageExecution(
                stage_id=stage_id,
                stage_name=stage_name,
                operator_id=op_id,
                operator_name=op_name
            )
    
    def start_production(self):
        """Iniciar la producción del producto"""
        self.started_at = datetime.now()
        self.last_updated = datetime.now()
        self.status = ProductStatus.IN_PROGRESS
    
    def complete_current_stage(self, quality_metrics: Optional[QualityMetrics] = None):
        """Completar la etapa actual"""
        if self.current_stage in self.stage_executions:
            stage = self.stage_executions[self.current_stage]
            stage.complete_stage(quality_metrics)
            
            # Actualizar métricas del producto
            self._update_product_metrics()
            
            # Avanzar a la siguiente etapa
            if self.current_stage < 6:
                self.current_stage += 1
            else:
                # Producto completado
                self._complete_product()
    
    def start_current_stage(self, station_id: str = ""):
        """Iniciar la etapa actual"""
        if self.current_stage in self.stage_executions:
            stage = self.stage_executions[self.current_stage]
            stage.start_stage(stage.operator_id, stage.operator_name, station_id)
            
            if self.status == ProductStatus.PENDING:
                self.start_production()
    
    def _complete_product(self):
        """Marcar producto como completado"""
        self.completed_at = datetime.now()
        self.status = ProductStatus.COMPLETED
        self.progress_percentage = 100.0
        self.last_updated = datetime.now()
        
        # Calcular tiempo total de ciclo
        if self.started_at and self.completed_at:
            self.total_cycle_time = int((self.completed_at - self.started_at).total_seconds())
        
        # Calcular eficiencia
        if self.target_cycle_time > 0:
            self.efficiency_score = min(100.0, (self.target_cycle_time / max(1, self.total_cycle_time)) * 100)
    
    def _update_product_metrics(self):
        """Actualizar métricas del producto"""
        completed_stages = sum(1 for stage in self.stage_executions.values() 
                              if stage.status == StageStatus.COMPLETED)
        
        self.progress_percentage = (completed_stages / len(self.stage_executions)) * 100
        
        # Calcular calidad promedio
        quality_scores = [stage.quality_metrics.quality_score 
                         for stage in self.stage_executions.values()
                         if stage.status == StageStatus.COMPLETED]
        
        if quality_scores:
            self.quality_score = sum(quality_scores) / len(quality_scores)
        
        self.last_updated = datetime.now()
    
    def get_current_stage_info(self) -> Dict[str, Any]:
        """Obtener información de la etapa actual"""
        if self.current_stage in self.stage_executions:
            stage = self.stage_executions[self.current_stage]
            return {
                'stage_id': stage.stage_id,
                'stage_name': stage.stage_name,
                'operator_name': stage.operator_name,
                'station_id': stage.station_id,
                'status': stage.status.value
            }
        return {}
    
    def get_cycle_time_by_stage(self) -> Dict[str, int]:
        """Obtener tiempo de ciclo por etapa"""
        return {
            stage.stage_name: stage.duration_seconds
            for stage in self.stage_executions.values()
            if stage.duration_seconds > 0
        }
    
    def is_overdue(self) -> bool:
        """Verificar si el producto está retrasado"""
        if self.started_at and self.status != ProductStatus.COMPLETED:
            elapsed = (datetime.now() - self.started_at).total_seconds()
            return elapsed > self.target_cycle_time
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            'barcode': self.barcode,
            'part_number': self.part_number,
            'product_name': self.product_name,
            'product_family': self.product_family,
            'work_order': self.work_order,
            'batch_number': self.batch_number,
            'serial_number': self.serial_number,
            'customer_code': self.customer_code,
            'revision': self.revision,
            'specification': self.specification,
            'target_cycle_time': self.target_cycle_time,
            'status': self.status.value,
            'progress_percentage': self.progress_percentage,
            'current_stage': self.current_stage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'total_cycle_time': self.total_cycle_time,
            'efficiency_score': self.efficiency_score,
            'quality_score': self.quality_score,
            'priority': self.priority,
            'notes': self.notes,
            'tags': self.tags,
            'stage_executions': {
                str(k): {
                    'stage_id': v.stage_id,
                    'stage_name': v.stage_name,
                    'operator_id': v.operator_id,
                    'operator_name': v.operator_name,
                    'start_time': v.start_time.isoformat() if v.start_time else None,
                    'end_time': v.end_time.isoformat() if v.end_time else None,
                    'duration_seconds': v.duration_seconds,
                    'status': v.status.value,
                    'quality_score': v.quality_metrics.quality_score,
                    'defect_count': v.quality_metrics.defect_count,
                    'notes': v.notes,
                    'station_id': v.station_id
                } for k, v in self.stage_executions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JCIProduct':
        """Crear instancia desde diccionario"""
        # Extraer datos básicos
        product = cls(
            barcode=data['barcode'],
            part_number=data['part_number'],
            product_name=data['product_name'],
            product_family=data['product_family'],
            work_order=data['work_order'],
            batch_number=data['batch_number'],
            serial_number=data['serial_number'],
            customer_code=data['customer_code'],
            revision=data['revision'],
            specification=data['specification'],
            target_cycle_time=data['target_cycle_time']
        )
        
        # Restaurar estado
        product.status = ProductStatus(data['status'])
        product.progress_percentage = data['progress_percentage']
        product.current_stage = data['current_stage']
        product.total_cycle_time = data['total_cycle_time']
        product.efficiency_score = data['efficiency_score']
        product.quality_score = data['quality_score']
        product.priority = data['priority']
        product.notes = data['notes']
        product.tags = data['tags']
        
        # Restaurar timestamps
        if data.get('created_at'):
            product.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            product.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            product.completed_at = datetime.fromisoformat(data['completed_at'])
        if data.get('last_updated'):
            product.last_updated = datetime.fromisoformat(data['last_updated'])
        
        return product


# Productos de ejemplo para Johnson Controls
JCI_SAMPLE_PRODUCTS = [
    {
        'barcode': 'JCI240001A',
        'part_number': 'HVAC-CTL-2024-001',
        'product_name': 'Controlador HVAC Inteligente',
        'product_family': 'Controles HVAC',
        'work_order': 'WO-2024-0156',
        'batch_number': 'BTH-240001',
        'serial_number': 'SN240001001',
        'customer_code': 'FORD-MX',
        'revision': 'Rev-C',
        'specification': 'JCI-SPEC-HVAC-2024-A',
        'target_cycle_time': 420  # 7 minutos
    },
    {
        'barcode': 'JCI240002B',
        'part_number': 'BATT-SYS-2024-002',
        'product_name': 'Sistema de Gestión de Batería',
        'product_family': 'Sistemas de Energía',
        'work_order': 'WO-2024-0157',
        'batch_number': 'BTH-240002',
        'serial_number': 'SN240002001',
        'customer_code': 'GM-MX',
        'revision': 'Rev-B',
        'specification': 'JCI-SPEC-BATT-2024-B',
        'target_cycle_time': 380  # 6.3 minutos
    },
    {
        'barcode': 'fewygfyu3',
        'part_number': 'HVAC-CTL-TEST-001',
        'product_name': 'Controlador HVAC Premium',
        'product_family': 'Controles HVAC',
        'work_order': 'WO-TEST-0001',
        'batch_number': 'BTH-TEST001',
        'serial_number': 'SNTEST001',
        'customer_code': 'TEST-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-HVAC-TEST-A',
        'target_cycle_time': 300  # 5 minutos
    },
    {
        'barcode': 'fwe24gvfd',
        'part_number': 'BATT-SYS-TEST-002',
        'product_name': 'Sistema Batería Industrial',
        'product_family': 'Sistemas de Energía',
        'work_order': 'WO-TEST-0002',
        'batch_number': 'BTH-TEST002',
        'serial_number': 'SNTEST002',
        'customer_code': 'TEST-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-BATT-TEST-A',
        'target_cycle_time': 280  # 4.7 minutos
    },
    {
        'barcode': 'fdgffdwwd3',
        'part_number': 'IOT-SWT-TEST-003',
        'product_name': 'Switch Inteligente IoT',
        'product_family': 'Dispositivos IoT',
        'work_order': 'WO-TEST-0003',
        'batch_number': 'BTH-TEST003',
        'serial_number': 'SNTEST003',
        'customer_code': 'TEST-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-IOT-TEST-A',
        'target_cycle_time': 250  # 4.2 minutos
    },
    {
        'barcode': 'JCI240003C',
        'part_number': 'INT-SWT-2024-003',
        'product_name': 'Switch Inteligente Interior',
        'product_family': 'Controles Interiores',
        'work_order': 'WO-2024-0158',
        'batch_number': 'BTH-240003',
        'serial_number': 'SN240003001',
        'customer_code': 'STEL-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-INT-2024-C',
        'target_cycle_time': 300  # 5 minutos
    },
    # 6 productos adicionales para ampliar el catálogo
    {
        'barcode': 'ther4mosta7',
        'part_number': 'THERM-ADV-2024-004',
        'product_name': 'Termostato Avanzado Digital',
        'product_family': 'Controles de Temperatura',
        'work_order': 'WO-2024-0159',
        'batch_number': 'BTH-240004',
        'serial_number': 'SN240004001',
        'customer_code': 'NISSAN-MX',
        'revision': 'Rev-B',
        'specification': 'JCI-SPEC-THERM-2024-B',
        'target_cycle_time': 350  # 5.8 minutos
    },
    {
        'barcode': 'sens0r9air2',
        'part_number': 'AIR-SENS-2024-005',
        'product_name': 'Sensor Calidad de Aire CO2',
        'product_family': 'Sensores Ambientales',
        'work_order': 'WO-2024-0160',
        'batch_number': 'BTH-240005',
        'serial_number': 'SN240005001',
        'customer_code': 'VW-MX',
        'revision': 'Rev-C',
        'specification': 'JCI-SPEC-AIR-2024-C',
        'target_cycle_time': 220  # 3.7 minutos
    },
    {
        'barcode': 'act8uator5v',
        'part_number': 'ACT-HVAC-2024-006',
        'product_name': 'Actuador HVAC Eléctrico',
        'product_family': 'Actuadores',
        'work_order': 'WO-2024-0161',
        'batch_number': 'BTH-240006',
        'serial_number': 'SN240006001',
        'customer_code': 'BMW-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-ACT-2024-A',
        'target_cycle_time': 290  # 4.8 minutos
    },
    {
        'barcode': 'disp1ay4led',
        'part_number': 'DISP-LED-2024-007',
        'product_name': 'Display LED Multifunción',
        'product_family': 'Interfaces Usuario',
        'work_order': 'WO-2024-0162',
        'batch_number': 'BTH-240007',
        'serial_number': 'SN240007001',
        'customer_code': 'TESLA-MX',
        'revision': 'Rev-D',
        'specification': 'JCI-SPEC-DISP-2024-D',
        'target_cycle_time': 410  # 6.8 minutos
    },
    {
        'barcode': 'valve6flow3',
        'part_number': 'VALVE-FLOW-2024-008',
        'product_name': 'Válvula Control de Flujo',
        'product_family': 'Válvulas de Control',
        'work_order': 'WO-2024-0163',
        'batch_number': 'BTH-240008',
        'serial_number': 'SN240008001',
        'customer_code': 'AUDI-MX',
        'revision': 'Rev-B',
        'specification': 'JCI-SPEC-VALVE-2024-B',
        'target_cycle_time': 365  # 6.1 minutos
    },
    {
        'barcode': 'relay8power1',
        'part_number': 'RELAY-PWR-2024-009',
        'product_name': 'Relay de Potencia Industrial',
        'product_family': 'Componentes Eléctricos',
        'work_order': 'WO-2024-0164',
        'batch_number': 'BTH-240009',
        'serial_number': 'SN240009001',
        'customer_code': 'MERC-MX',
        'revision': 'Rev-A',
        'specification': 'JCI-SPEC-RELAY-2024-A',
        'target_cycle_time': 180  # 3.0 minutos
    }
]