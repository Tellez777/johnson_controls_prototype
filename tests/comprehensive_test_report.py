#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REPORTE COMPREHENSIVO DE PRUEBAS DEL SISTEMA
Johnson Controls - Sistema de Seguimiento Industrial

Resumen ejecutivo de todas las pruebas realizadas y estado del sistema.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger


class ComprehensiveTestReport:
    """Generador de reporte comprehensivo de pruebas"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.report_data = {}
        
    def load_test_results(self):
        """Cargar resultados de pruebas desde archivos"""
        try:
            logs_dir = Path("data/logs")
            
            # Buscar el archivo de reporte más reciente
            test_reports = list(logs_dir.glob("test_report_*.json"))
            
            if test_reports:
                # Ordenar por fecha y tomar el más reciente
                latest_report = max(test_reports, key=lambda p: p.stat().st_mtime)
                
                with open(latest_report, 'r', encoding='utf-8') as f:
                    self.report_data = json.load(f)
                
                self.logger.info(f"Reporte cargado: {latest_report}")
                return True
            else:
                self.logger.warning("No se encontraron reportes de pruebas")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cargando resultados: {e}")
            return False
    
    def analyze_test_results(self):
        """Analizar resultados de pruebas y generar conclusiones"""
        if not self.report_data:
            return None
        
        summary = self.report_data.get('summary', {})
        test_details = self.report_data.get('test_details', [])
        
        # Análisis por categorías
        categories = {
            'CRUD': ['Creación', 'Lectura', 'Actualización', 'Eliminación'],
            'Etapas': ['Secuencia', 'Validación', 'Transiciones'],
            'Escaneo': ['exitoso', 'inexistente', 'validación'],
            'Operadores': ['Asignación', 'gestión'],
            'Escenarios': ['Múltiples', 'Cambio', 'simultáneos'],
            'Consistencia': ['Consistencia', 'datos'],
            'Rendimiento': ['Rendimiento', 'tiempo']
        }
        
        category_results = {}
        
        for category, keywords in categories.items():
            category_tests = []
            for test in test_details:
                test_name = test['test_name'].lower()
                if any(keyword.lower() in test_name for keyword in keywords):
                    category_tests.append(test)
            
            if category_tests:
                passed = sum(1 for t in category_tests if t['passed'])
                total = len(category_tests)
                success_rate = (passed / total * 100) if total > 0 else 0
                
                category_results[category] = {
                    'tests_count': total,
                    'passed': passed,
                    'failed': total - passed,
                    'success_rate': round(success_rate, 1),
                    'status': 'Excelente' if success_rate >= 90 else 
                             'Bueno' if success_rate >= 75 else
                             'Regular' if success_rate >= 50 else 'Crítico'
                }
        
        return {
            'overall_summary': summary,
            'category_analysis': category_results,
            'failed_tests': [t for t in test_details if not t['passed']],
            'slowest_tests': sorted(test_details, key=lambda x: x.get('execution_time', 0), reverse=True)[:3]
        }
    
    def generate_executive_summary(self, analysis):
        """Generar resumen ejecutivo"""
        if not analysis:
            return "No hay datos de análisis disponibles."
        
        summary = analysis['overall_summary']
        categories = analysis['category_analysis']
        failed_tests = analysis['failed_tests']
        
        # Determinar estado general del sistema
        success_rate = summary.get('success_rate', 0)
        
        if success_rate >= 95:
            system_status = "EXCELENTE"
            recommendation = "Sistema funcionando óptimamente. Continuar con monitoreo regular."
        elif success_rate >= 85:
            system_status = "BUENO"
            recommendation = "Sistema en buen estado con problemas menores. Revisar fallos específicos."
        elif success_rate >= 70:
            system_status = "REGULAR"
            recommendation = "Sistema funcional pero con problemas que requieren atención."
        else:
            system_status = "CRÍTICO"
            recommendation = "Sistema con problemas serios que requieren atención inmediata."
        
        report = f"""
==========================================================
REPORTE EJECUTIVO - PRUEBAS DE CONSISTENCIA DEL SISTEMA
Johnson Controls - Sistema de Seguimiento Industrial
==========================================================

RESUMEN GENERAL:
- Total de Pruebas: {summary.get('total_tests', 0)}
- Pruebas Exitosas: {summary.get('tests_passed', 0)}
- Pruebas Fallidas: {summary.get('tests_failed', 0)}
- Tasa de Exito: {success_rate}%
- Tiempo Total: {summary.get('total_duration', 0)}s
- Estado del Sistema: {system_status}

ANALISIS POR CATEGORIAS:
"""
        
        for category, results in categories.items():
            status_icon = "[OK]" if results['success_rate'] >= 90 else "[WARN]" if results['success_rate'] >= 75 else "[FAIL]"
            report += f"  {status_icon} {category}: {results['success_rate']}% ({results['passed']}/{results['tests_count']}) - {results['status']}\n"
        
        if failed_tests:
            report += f"\nPRUEBAS FALLIDAS:\n"
            for test in failed_tests:
                report += f"  - {test['test_name']}: {test['details']}\n"
        
        report += f"\nRECOMENDACIONES:\n"
        report += f"  {recommendation}\n"
        
        # Problemas específicos identificados
        if failed_tests:
            report += f"\nACCIONES REQUERIDAS:\n"
            for test in failed_tests:
                if 'operador' in test['test_name'].lower():
                    report += f"  - Revisar configuracion de operadores y asignacion automatica\n"
                elif 'escaneo' in test['test_name'].lower():
                    report += f"  - Verificar funcionalidad de escaneo y validacion de codigos\n"
                elif 'etapa' in test['test_name'].lower():
                    report += f"  - Revisar logica de transicion entre etapas\n"
        
        report += f"\nMETRICAS DE RENDIMIENTO:\n"
        slowest = analysis.get('slowest_tests', [])
        if slowest:
            for i, test in enumerate(slowest[:3], 1):
                time_ms = test.get('execution_time', 0) * 1000
                report += f"  {i}. {test['test_name']}: {time_ms:.1f}ms\n"
        
        report += f"\nReporte generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"==========================================================\n"
        
        return report
    
    def save_executive_report(self, report_content):
        """Guardar reporte ejecutivo"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"data/logs/executive_report_{timestamp}.txt"
            
            Path("data/logs").mkdir(parents=True, exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"Reporte ejecutivo guardado: {report_file}")
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error guardando reporte: {e}")
            return None
    
    def generate_complete_report(self):
        """Generar reporte completo"""
        print("Generando reporte comprehensivo de pruebas...")
        
        # Cargar datos
        if not self.load_test_results():
            print("ERROR: No se pudieron cargar los resultados de pruebas")
            return None
        
        # Analizar resultados
        analysis = self.analyze_test_results()
        if not analysis:
            print("ERROR: No se pudo analizar los resultados")
            return None
        
        # Generar resumen ejecutivo
        executive_summary = self.generate_executive_summary(analysis)
        
        # Mostrar en consola
        print(executive_summary)
        
        # Guardar archivo
        report_file = self.save_executive_report(executive_summary)
        
        return {
            'analysis': analysis,
            'executive_summary': executive_summary,
            'report_file': report_file
        }


def main():
    """Función principal"""
    reporter = ComprehensiveTestReport()
    result = reporter.generate_complete_report()
    
    if result:
        print(f"\nReporte completo generado exitosamente")
        if result['report_file']:
            print(f"Archivo guardado: {result['report_file']}")
    else:
        print(f"\nError generando reporte")


if __name__ == "__main__":
    main()