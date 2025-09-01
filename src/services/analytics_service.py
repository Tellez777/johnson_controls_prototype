#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYTICS SERVICE - Servicio de análisis y métricas
Johnson Controls - Sistema de Seguimiento Industrial
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

from ..utils.config import config, get_jci_config
from ..utils.logger import get_logger
from ..models.product import JCIProduct, ProductStatus, QualityMetrics


@dataclass
class StageMetrics:
    """Métricas por etapa"""
    stage_id: int
    stage_name: str
    total_products: int = 0
    completed_products: int = 0
    average_cycle_time: float = 0.0
    min_cycle_time: float = 0.0
    max_cycle_time: float = 0.0
    quality_score: float = 100.0
    defect_rate: float = 0.0
    efficiency_score: float = 100.0
    bottleneck_score: float = 0.0  # 0-100, donde 100 es el mayor cuello de botella


@dataclass
class ProductionMetrics:
    """Métricas de producción"""
    timestamp: datetime
    total_products: int = 0
    completed_products: int = 0
    in_progress_products: int = 0
    pending_products: int = 0
    completion_rate: float = 0.0
    average_cycle_time: float = 0.0
    target_cycle_time: float = 0.0
    efficiency_rate: float = 0.0
    quality_score: float = 100.0
    throughput_per_hour: float = 0.0
    oee_score: float = 0.0  # Overall Equipment Effectiveness


@dataclass
class QualityAnalytics:
    """Analytics de calidad"""
    overall_quality: float = 100.0
    defect_rate: float = 0.0
    rework_rate: float = 0.0
    quality_trends: List[float] = None
    critical_stages: List[int] = None
    quality_by_stage: Dict[int, float] = None
    
    def __post_init__(self):
        if self.quality_trends is None:
            self.quality_trends = []
        if self.critical_stages is None:
            self.critical_stages = []
        if self.quality_by_stage is None:
            self.quality_by_stage = {}


@dataclass
class PerformanceAnalytics:
    """Analytics de rendimiento"""
    oee_score: float = 0.0  # Overall Equipment Effectiveness
    availability: float = 100.0
    performance_rate: float = 100.0
    quality_rate: float = 100.0
    bottleneck_stage: int = 1
    cycle_time_variance: float = 0.0
    efficiency_trends: List[float] = None
    
    def __post_init__(self):
        if self.efficiency_trends is None:
            self.efficiency_trends = []


class AnalyticsService:
    """Servicio principal de analytics"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.jci_config = get_jci_config()
        
        # Estado del servicio
        self.is_running = False
        self.analytics_thread = None
        
        # Datos históricos
        self.stage_metrics: Dict[int, StageMetrics] = {}
        self.production_history: deque = deque(maxlen=1000)  # Últimas 1000 mediciones
        self.quality_history: deque = deque(maxlen=500)
        self.performance_history: deque = deque(maxlen=500)
        
        # Métricas en tiempo real
        self.current_metrics: Optional[ProductionMetrics] = None
        self.current_quality: Optional[QualityAnalytics] = None
        self.current_performance: Optional[PerformanceAnalytics] = None
        
        # Cache de productos para análisis
        self.products_cache: Dict[str, JCIProduct] = {}
        
        # Configuración de análisis
        self.analysis_interval = 30  # segundos
        self.trend_window = 100  # número de mediciones para tendencias
        
        self.logger.info("Analytics Service inicializado")
    
    def initialize(self) -> bool:
        """Inicializar servicio de analytics"""
        try:
            # Inicializar métricas por etapa
            self._initialize_stage_metrics()
            
            # Cargar datos históricos si existen
            self._load_historical_data()
            
            self.logger.info("Analytics Service inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando Analytics Service: {e}")
            return False
    
    def start(self):
        """Iniciar servicio de analytics"""
        if not self.is_running:
            self.is_running = True
            self.analytics_thread = threading.Thread(
                target=self._analytics_loop,
                daemon=True
            )
            self.analytics_thread.start()
            self.logger.info("Analytics Service iniciado")
    
    def stop(self):
        """Detener servicio de analytics"""
        self.is_running = False
        if self.analytics_thread and self.analytics_thread.is_alive():
            self.analytics_thread.join(timeout=5)
        self.logger.info("Analytics Service detenido")
    
    def _initialize_stage_metrics(self):
        """Inicializar métricas por etapa"""
        stages = [
            (1, "Soldadura"),
            (2, "Pulido"),
            (3, "Presión"),
            (4, "Calidad"),
            (5, "Pintura"),
            (6, "Almacén")
        ]
        
        for stage_id, stage_name in stages:
            self.stage_metrics[stage_id] = StageMetrics(
                stage_id=stage_id,
                stage_name=stage_name
            )
    
    def _analytics_loop(self):
        """Bucle principal de análisis"""
        self.logger.info("Iniciando bucle de analytics")
        
        while self.is_running:
            try:
                # Realizar análisis completo
                self._perform_analysis()
                
                # Guardar métricas históricas
                self._save_historical_metrics()
                
                # Detectar anomalías y alertas
                self._detect_anomalies()
                
                time.sleep(self.analysis_interval)
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Error en bucle de analytics: {e}")
                    time.sleep(5)
        
        self.logger.info("Bucle de analytics terminado")
    
    def _perform_analysis(self):
        """Realizar análisis completo"""
        # Cargar productos actuales
        self._update_products_cache()
        
        # Calcular métricas de producción
        self.current_metrics = self._calculate_production_metrics()
        
        # Calcular analytics de calidad
        self.current_quality = self._calculate_quality_analytics()
        
        # Calcular analytics de rendimiento
        self.current_performance = self._calculate_performance_analytics()
        
        # Actualizar métricas por etapa
        self._update_stage_metrics()
        
        self.logger.debug("Análisis completo realizado")
    
    def _update_products_cache(self):
        """Actualizar cache de productos desde el sistema"""
        # En un sistema real, esto cargaría desde el data sync service
        # Por ahora simularemos algunos productos
        from ..models.product import JCI_SAMPLE_PRODUCTS, JCIProduct
        
        # Simular algunos productos en diferentes estados
        if not self.products_cache:
            for i, sample_data in enumerate(JCI_SAMPLE_PRODUCTS):
                product = JCIProduct(**sample_data)
                
                # Simular diferentes estados de progreso
                if i == 0:  # Primer producto completado
                    product.status = ProductStatus.COMPLETED
                    product.progress_percentage = 100.0
                    product.current_stage = 6
                    product.started_at = datetime.now() - timedelta(minutes=15)
                    product.completed_at = datetime.now() - timedelta(minutes=2)
                    product.total_cycle_time = 780  # 13 minutos
                elif i == 1:  # Segundo producto en proceso
                    product.status = ProductStatus.IN_PROGRESS
                    product.progress_percentage = 66.7
                    product.current_stage = 4
                    product.started_at = datetime.now() - timedelta(minutes=8)
                
                self.products_cache[product.barcode] = product
    
    def _calculate_production_metrics(self) -> ProductionMetrics:
        """Calcular métricas de producción"""
        products = list(self.products_cache.values())
        
        if not products:
            return ProductionMetrics(timestamp=datetime.now())
        
        # Contar productos por estado
        completed = sum(1 for p in products if p.status == ProductStatus.COMPLETED)
        in_progress = sum(1 for p in products if p.status == ProductStatus.IN_PROGRESS)
        pending = sum(1 for p in products if p.status == ProductStatus.PENDING)
        total = len(products)
        
        # Calcular tiempos de ciclo
        cycle_times = [p.total_cycle_time for p in products if p.total_cycle_time > 0]
        avg_cycle_time = statistics.mean(cycle_times) if cycle_times else 0.0
        
        # Tiempo objetivo promedio
        target_cycle_time = statistics.mean([p.target_cycle_time for p in products])
        
        # Calcular eficiencia
        efficiency_rate = 0.0
        if avg_cycle_time > 0 and target_cycle_time > 0:
            efficiency_rate = min(100.0, (target_cycle_time / avg_cycle_time) * 100)
        
        # Calcular calidad promedio
        quality_scores = [p.quality_score for p in products if p.quality_score > 0]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 100.0
        
        # Calcular throughput (productos por hora)
        # Simulado basado en completados y tiempo objetivo
        throughput_per_hour = 60 * 60 / target_cycle_time if target_cycle_time > 0 else 0.0
        
        # Calcular OEE (Overall Equipment Effectiveness)
        availability = 95.0  # Simulado - en producción vendría de sensores
        performance_rate = efficiency_rate
        quality_rate = min(100.0, avg_quality)
        oee_score = (availability * performance_rate * quality_rate) / 10000
        
        return ProductionMetrics(
            timestamp=datetime.now(),
            total_products=total,
            completed_products=completed,
            in_progress_products=in_progress,
            pending_products=pending,
            completion_rate=(completed / total * 100) if total > 0 else 0.0,
            average_cycle_time=avg_cycle_time,
            target_cycle_time=target_cycle_time,
            efficiency_rate=efficiency_rate,
            quality_score=avg_quality,
            throughput_per_hour=throughput_per_hour,
            oee_score=oee_score
        )
    
    def _calculate_quality_analytics(self) -> QualityAnalytics:
        """Calcular analytics de calidad"""
        products = list(self.products_cache.values())
        
        if not products:
            return QualityAnalytics()
        
        # Calidad general
        quality_scores = [p.quality_score for p in products if p.quality_score > 0]
        overall_quality = statistics.mean(quality_scores) if quality_scores else 100.0
        
        # Calcular tasa de defectos
        total_defects = 0
        total_rework = 0
        stage_quality = defaultdict(list)
        
        for product in products:
            for stage_execution in product.stage_executions.values():
                if stage_execution.quality_metrics:
                    qm = stage_execution.quality_metrics
                    total_defects += qm.defect_count
                    total_rework += qm.rework_count
                    stage_quality[stage_execution.stage_id].append(qm.quality_score)
        
        total_opportunities = len(products) * 6  # 6 etapas por producto
        defect_rate = (total_defects / total_opportunities * 100) if total_opportunities > 0 else 0.0
        rework_rate = (total_rework / total_opportunities * 100) if total_opportunities > 0 else 0.0
        
        # Calidad por etapa
        quality_by_stage = {}
        critical_stages = []
        
        for stage_id, scores in stage_quality.items():
            if scores:
                avg_quality = statistics.mean(scores)
                quality_by_stage[stage_id] = avg_quality
                
                # Identificar etapas críticas (calidad < 90%)
                if avg_quality < 90.0:
                    critical_stages.append(stage_id)
        
        # Agregar tendencia de calidad histórica
        quality_trends = []
        if len(self.quality_history) > 0:
            quality_trends = [qa.overall_quality for qa in list(self.quality_history)[-20:]]
        
        return QualityAnalytics(
            overall_quality=overall_quality,
            defect_rate=defect_rate,
            rework_rate=rework_rate,
            quality_trends=quality_trends,
            critical_stages=critical_stages,
            quality_by_stage=quality_by_stage
        )
    
    def _calculate_performance_analytics(self) -> PerformanceAnalytics:
        """Calcular analytics de rendimiento"""
        if not self.current_metrics:
            return PerformanceAnalytics()
        
        # OEE ya calculado en métricas de producción
        oee_score = self.current_metrics.oee_score
        
        # Simular availability y performance rate
        availability = 95.0  # Simulado
        performance_rate = self.current_metrics.efficiency_rate
        quality_rate = min(100.0, self.current_metrics.quality_score)
        
        # Identificar cuello de botella
        bottleneck_stage = self._identify_bottleneck()
        
        # Calcular varianza de tiempo de ciclo
        products = list(self.products_cache.values())
        cycle_times = [p.total_cycle_time for p in products if p.total_cycle_time > 0]
        cycle_time_variance = statistics.pvariance(cycle_times) if len(cycle_times) > 1 else 0.0
        
        # Tendencias de eficiencia
        efficiency_trends = []
        if len(self.production_history) > 0:
            efficiency_trends = [pm.efficiency_rate for pm in list(self.production_history)[-20:]]
        
        return PerformanceAnalytics(
            oee_score=oee_score,
            availability=availability,
            performance_rate=performance_rate,
            quality_rate=quality_rate,
            bottleneck_stage=bottleneck_stage,
            cycle_time_variance=cycle_time_variance,
            efficiency_trends=efficiency_trends
        )
    
    def _identify_bottleneck(self) -> int:
        """Identificar cuello de botella del proceso"""
        # Analizar métricas por etapa para identificar el cuello de botella
        max_cycle_time = 0.0
        bottleneck_stage = 1
        
        for stage_id, metrics in self.stage_metrics.items():
            if metrics.average_cycle_time > max_cycle_time:
                max_cycle_time = metrics.average_cycle_time
                bottleneck_stage = stage_id
        
        return bottleneck_stage
    
    def _update_stage_metrics(self):
        """Actualizar métricas por etapa"""
        stage_data = defaultdict(lambda: {'times': [], 'quality': [], 'completed': 0, 'total': 0})
        
        for product in self.products_cache.values():
            for stage_id, execution in product.stage_executions.items():
                stage_data[stage_id]['total'] += 1
                
                if execution.duration_seconds > 0:
                    stage_data[stage_id]['times'].append(execution.duration_seconds)
                    stage_data[stage_id]['quality'].append(execution.quality_metrics.quality_score)
                    stage_data[stage_id]['completed'] += 1
        
        # Actualizar métricas
        for stage_id, data in stage_data.items():
            if stage_id in self.stage_metrics:
                metrics = self.stage_metrics[stage_id]
                metrics.total_products = data['total']
                metrics.completed_products = data['completed']
                
                if data['times']:
                    metrics.average_cycle_time = statistics.mean(data['times'])
                    metrics.min_cycle_time = min(data['times'])
                    metrics.max_cycle_time = max(data['times'])
                
                if data['quality']:
                    metrics.quality_score = statistics.mean(data['quality'])
                    
                    # Calcular tasa de defectos
                    defective = sum(1 for q in data['quality'] if q < 90)
                    metrics.defect_rate = (defective / len(data['quality']) * 100) if data['quality'] else 0.0
                
                # Calcular eficiencia
                target_time = 70  # Tiempo objetivo por etapa (segundos)
                if metrics.average_cycle_time > 0:
                    metrics.efficiency_score = min(100.0, (target_time / metrics.average_cycle_time) * 100)
    
    def _save_historical_metrics(self):
        """Guardar métricas en historial"""
        if self.current_metrics:
            self.production_history.append(self.current_metrics)
        
        if self.current_quality:
            self.quality_history.append(self.current_quality)
        
        if self.current_performance:
            self.performance_history.append(self.current_performance)
    
    def _detect_anomalies(self):
        """Detectar anomalías en los datos"""
        if not self.current_metrics:
            return
        
        alerts = []
        
        # Alertas de eficiencia
        if self.current_metrics.efficiency_rate < 70:
            alerts.append({
                'type': 'efficiency',
                'severity': 'high',
                'message': f'Eficiencia baja: {self.current_metrics.efficiency_rate:.1f}%'
            })
        
        # Alertas de calidad
        if self.current_quality and self.current_quality.overall_quality < 85:
            alerts.append({
                'type': 'quality',
                'severity': 'high',
                'message': f'Calidad baja: {self.current_quality.overall_quality:.1f}%'
            })
        
        # Alertas de OEE
        if self.current_metrics.oee_score < 60:
            alerts.append({
                'type': 'oee',
                'severity': 'medium',
                'message': f'OEE bajo: {self.current_metrics.oee_score:.1f}%'
            })
        
        # Log alertas
        for alert in alerts:
            self.logger.warning(f"ALERTA {alert['severity'].upper()}: {alert['message']}")
    
    def _load_historical_data(self):
        """Cargar datos históricos si existen"""
        # En una implementación completa, esto cargaría desde archivos/DB
        self.logger.info("Datos históricos cargados (simulado)")
    
    # API pública para obtener métricas
    
    def get_current_metrics(self) -> Optional[ProductionMetrics]:
        """Obtener métricas actuales de producción"""
        return self.current_metrics
    
    def get_quality_analytics(self) -> Optional[QualityAnalytics]:
        """Obtener analytics de calidad"""
        return self.current_quality
    
    def get_performance_analytics(self) -> Optional[PerformanceAnalytics]:
        """Obtener analytics de rendimiento"""
        return self.current_performance
    
    def get_stage_metrics(self) -> Dict[int, StageMetrics]:
        """Obtener métricas por etapa"""
        return self.stage_metrics.copy()
    
    def get_production_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Obtener tendencias de producción"""
        # Filtrar últimas N horas
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        trends = []
        for metrics in self.production_history:
            if metrics.timestamp >= cutoff_time:
                trends.append({
                    'timestamp': metrics.timestamp.isoformat(),
                    'completion_rate': metrics.completion_rate,
                    'efficiency_rate': metrics.efficiency_rate,
                    'quality_score': metrics.quality_score,
                    'oee_score': metrics.oee_score
                })
        
        return trends
    
    def get_kpi_summary(self) -> Dict[str, Any]:
        """Obtener resumen de KPIs principales"""
        if not self.current_metrics:
            return {}
        
        return {
            'oee': round(self.current_metrics.oee_score, 1),
            'efficiency': round(self.current_metrics.efficiency_rate, 1),
            'quality': round(self.current_metrics.quality_score, 1),
            'throughput': round(self.current_metrics.throughput_per_hour, 1),
            'completion_rate': round(self.current_metrics.completion_rate, 1),
            'bottleneck_stage': self.current_performance.bottleneck_stage if self.current_performance else 1
        }
    
    def record_stage_completion(self, product: JCIProduct, stage_id: int, quality_metrics: QualityMetrics):
        """Registrar completado de etapa para análisis"""
        # Esta función sería llamada por el scanner manager
        # Para actualizar los datos de análisis en tiempo real
        
        self.logger.debug(f"Registrando completado de etapa {stage_id} para producto {product.barcode}")
        
        # Actualizar cache de productos
        self.products_cache[product.barcode] = product
        
        # Forzar recálculo de métricas si es necesario
        if len(self.products_cache) % 5 == 0:  # Cada 5 actualizaciones
            self._perform_analysis()