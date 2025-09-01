#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEM VALIDATOR - Validador completo del sistema Johnson Controls
Valida instalación, configuración y funcionalidad
"""

import sys
import os
import json
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SystemValidator:
    """Validador completo del sistema Johnson Controls"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'pending',
            'categories': {},
            'recommendations': [],
            'errors': [],
            'warnings': []
        }
        
        self.base_path = Path(__file__).parent
    
    def validate_all(self) -> dict:
        """Ejecutar todas las validaciones"""
        print("🔍 JOHNSON CONTROLS - VALIDACIÓN COMPLETA DEL SISTEMA")
        print("=" * 60)
        
        validation_categories = [
            ('🐍 Python Environment', self._validate_python_environment),
            ('📁 Directory Structure', self._validate_directory_structure),
            ('📦 Dependencies', self._validate_dependencies),
            ('⚙️  Configuration Files', self._validate_configuration),
            ('🧩 Code Modules', self._validate_code_modules),
            ('🔌 Hardware Interfaces', self._validate_hardware),
            ('🌐 Web Components', self._validate_web_components),
            ('📊 Data Files', self._validate_data_files),
            ('🔒 Security & Permissions', self._validate_security),
            ('🧪 System Functionality', self._validate_functionality)
        ]
        
        passed_categories = 0
        total_categories = len(validation_categories)
        
        for category_name, validation_func in validation_categories:
            try:
                print(f"\n{category_name}")
                print("-" * 40)
                
                result = validation_func()
                self.results['categories'][category_name] = result
                
                if result['status'] == 'pass':
                    passed_categories += 1
                    print(f"✅ {category_name}: PASSED")
                elif result['status'] == 'warning':
                    print(f"⚠️  {category_name}: WARNING")
                else:
                    print(f"❌ {category_name}: FAILED")
                
                # Mostrar detalles
                for detail in result.get('details', []):
                    print(f"   • {detail}")
                
            except Exception as e:
                self.results['categories'][category_name] = {
                    'status': 'error',
                    'details': [f'Validation error: {str(e)}'],
                    'score': 0
                }
                print(f"❌ {category_name}: ERROR - {e}")
        
        # Determinar estado general
        pass_rate = passed_categories / total_categories
        if pass_rate >= 0.9:
            self.results['overall_status'] = 'excellent'
            status_icon = "🎉"
            status_text = "EXCELENTE"
        elif pass_rate >= 0.7:
            self.results['overall_status'] = 'good'
            status_icon = "✅"
            status_text = "BUENO"
        elif pass_rate >= 0.5:
            self.results['overall_status'] = 'acceptable'
            status_icon = "⚠️"
            status_text = "ACEPTABLE"
        else:
            self.results['overall_status'] = 'poor'
            status_icon = "❌"
            status_text = "DEFICIENTE"
        
        # Generar recomendaciones
        self._generate_recommendations()
        
        # Mostrar resumen final
        print("\n" + "=" * 60)
        print(f"📊 RESULTADO FINAL: {status_icon} {status_text}")
        print(f"📈 Categorías Aprobadas: {passed_categories}/{total_categories} ({pass_rate*100:.1f}%)")
        print("=" * 60)
        
        if self.results['recommendations']:
            print("\n💡 RECOMENDACIONES:")
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        return self.results
    
    def _validate_python_environment(self) -> dict:
        """Validar ambiente Python"""
        details = []
        score = 0
        
        # Versión de Python
        if sys.version_info >= (3, 8):
            details.append(f"Python {sys.version.split()[0]} ✅")
            score += 25
        else:
            details.append(f"Python {sys.version.split()[0]} ❌ (Se requiere 3.8+)")
        
        # Pip disponible
        try:
            subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                          capture_output=True, check=True)
            details.append("pip disponible ✅")
            score += 25
        except:
            details.append("pip no disponible ❌")
        
        # Virtualenv (opcional)
        if hasattr(sys, 'prefix') and sys.prefix != sys.base_prefix:
            details.append("Virtual environment activo ✅")
            score += 25
        else:
            details.append("Virtual environment no detectado ⚠️")
        
        # Módulos estándar críticos
        critical_modules = ['json', 'os', 'pathlib', 'datetime', 'threading']
        missing = []
        
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        
        if not missing:
            details.append("Módulos estándar disponibles ✅")
            score += 25
        else:
            details.append(f"Módulos faltantes: {missing} ❌")
        
        return {
            'status': 'pass' if score >= 75 else 'warning' if score >= 50 else 'fail',
            'score': score,
            'details': details
        }
    
    def _validate_directory_structure(self) -> dict:
        """Validar estructura de directorios"""
        required_structure = {
            'src': ['core', 'hardware', 'web', 'models', 'services', 'utils'],
            'src/web': ['api'],
            'config': [],
            'data': ['json', 'excel', 'logs', 'backup'],
            'tests': []
        }
        
        details = []
        score = 0
        total_items = sum(len(v) + 1 for v in required_structure.values())
        
        for base_dir, subdirs in required_structure.items():
            base_path = self.base_path / base_dir
            
            if base_path.exists():
                details.append(f"{base_dir}/ ✅")
                score += 1
                
                for subdir in subdirs:
                    sub_path = base_path / subdir
                    if sub_path.exists():
                        details.append(f"  {subdir}/ ✅")
                        score += 1
                    else:
                        details.append(f"  {subdir}/ ❌")
            else:
                details.append(f"{base_dir}/ ❌")
        
        pass_rate = score / total_items
        
        return {
            'status': 'pass' if pass_rate >= 0.8 else 'warning' if pass_rate >= 0.6 else 'fail',
            'score': int(pass_rate * 100),
            'details': details
        }
    
    def _validate_dependencies(self) -> dict:
        """Validar dependencias"""
        # Dependencias críticas
        critical_deps = {
            'flask': 'Flask web framework',
            'flask_cors': 'CORS support',
            'serial': 'Serial communication',
            'openpyxl': 'Excel file handling'
        }
        
        # Dependencias opcionales
        optional_deps = {
            'numpy': 'Numerical computations',
            'pandas': 'Data analysis',
            'requests': 'HTTP requests'
        }
        
        details = []
        score = 0
        
        # Verificar críticas
        critical_available = 0
        for module, description in critical_deps.items():
            try:
                spec = importlib.util.find_spec(module)
                if spec is not None:
                    details.append(f"{description} ({module}) ✅")
                    critical_available += 1
                else:
                    details.append(f"{description} ({module}) ❌")
            except:
                details.append(f"{description} ({module}) ❌")
        
        score = (critical_available / len(critical_deps)) * 80
        
        # Verificar opcionales (bonus)
        optional_available = 0
        for module, description in optional_deps.items():
            try:
                spec = importlib.util.find_spec(module)
                if spec is not None:
                    details.append(f"{description} ({module}) ✅ (opcional)")
                    optional_available += 1
            except:
                pass
        
        bonus_score = (optional_available / len(optional_deps)) * 20
        score += bonus_score
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 40 else 'fail',
            'score': int(score),
            'details': details
        }
    
    def _validate_configuration(self) -> dict:
        """Validar archivos de configuración"""
        config_files = [
            ('requirements.txt', True),
            ('config/development.json', True),
            ('config/production.json', False),
            ('config/johnson_controls.json', False),
            ('.gitignore', False)
        ]
        
        details = []
        score = 0
        required_count = sum(1 for _, required in config_files if required)
        
        for config_file, required in config_files:
            file_path = self.base_path / config_file
            
            if file_path.exists():
                details.append(f"{config_file} ✅")
                score += 1
                
                # Validar contenido para archivos JSON
                if config_file.endswith('.json'):
                    try:
                        with open(file_path, 'r') as f:
                            json.load(f)
                        details.append(f"  Sintaxis JSON válida ✅")
                    except json.JSONDecodeError:
                        details.append(f"  Sintaxis JSON inválida ❌")
                        
            else:
                status_icon = "❌" if required else "⚠️"
                details.append(f"{config_file} {status_icon}")
        
        pass_rate = score / len(config_files)
        
        return {
            'status': 'pass' if score >= required_count else 'warning' if pass_rate >= 0.5 else 'fail',
            'score': int(pass_rate * 100),
            'details': details
        }
    
    def _validate_code_modules(self) -> dict:
        """Validar módulos de código"""
        core_modules = [
            'src/utils/config.py',
            'src/utils/logger.py',
            'src/models/product.py',
            'src/services/notification_service.py',
            'main.py'
        ]
        
        details = []
        score = 0
        
        for module_path in core_modules:
            file_path = self.base_path / module_path
            
            if file_path.exists():
                details.append(f"{module_path} ✅")
                score += 1
                
                # Verificar sintaxis Python básica
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Compilar código para verificar sintaxis
                    compile(content, str(file_path), 'exec')
                    details.append(f"  Sintaxis Python válida ✅")
                    
                except SyntaxError as e:
                    details.append(f"  Error de sintaxis: línea {e.lineno} ❌")
                except Exception as e:
                    details.append(f"  Error de validación: {e} ⚠️")
            else:
                details.append(f"{module_path} ❌")
        
        pass_rate = score / len(core_modules)
        
        return {
            'status': 'pass' if pass_rate >= 0.8 else 'warning' if pass_rate >= 0.6 else 'fail',
            'score': int(pass_rate * 100),
            'details': details
        }
    
    def _validate_hardware(self) -> dict:
        """Validar interfaces de hardware"""
        details = []
        score = 0
        
        # Verificar pyserial
        try:
            import serial
            import serial.tools.list_ports
            details.append("PySerial disponible ✅")
            score += 30
            
            # Listar puertos disponibles
            ports = list(serial.tools.list_ports.comports())
            if ports:
                details.append(f"Puertos serie disponibles: {len(ports)} ✅")
                score += 30
                for port in ports[:3]:  # Mostrar máximo 3
                    details.append(f"  {port.device}: {port.description}")
            else:
                details.append("Sin puertos serie disponibles ⚠️")
                score += 10
                
        except ImportError:
            details.append("PySerial no disponible ❌")
        
        # Verificar módulo de scanner
        scanner_path = self.base_path / 'src/hardware/zebra_scanner.py'
        if scanner_path.exists():
            details.append("Módulo Zebra Scanner disponible ✅")
            score += 40
        else:
            details.append("Módulo Zebra Scanner no disponible ❌")
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 40 else 'fail',
            'score': score,
            'details': details
        }
    
    def _validate_web_components(self) -> dict:
        """Validar componentes web"""
        details = []
        score = 0
        
        # Verificar Flask
        try:
            import flask
            details.append("Flask disponible ✅")
            score += 25
        except ImportError:
            details.append("Flask no disponible ❌")
        
        # Verificar Flask-CORS
        try:
            import flask_cors
            details.append("Flask-CORS disponible ✅")
            score += 15
        except ImportError:
            details.append("Flask-CORS no disponible ❌")
        
        # Verificar archivos web
        web_files = [
            'src/web/app.py',
            'src/web/api/data_api.py',
            'src/web/api/control_api.py'
        ]
        
        existing_files = 0
        for web_file in web_files:
            if (self.base_path / web_file).exists():
                existing_files += 1
        
        if existing_files == len(web_files):
            details.append("Todos los módulos web disponibles ✅")
            score += 60
        elif existing_files > 0:
            details.append(f"Módulos web parcialmente disponibles ({existing_files}/{len(web_files)}) ⚠️")
            score += 30
        else:
            details.append("Módulos web no disponibles ❌")
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 40 else 'fail',
            'score': score,
            'details': details
        }
    
    def _validate_data_files(self) -> dict:
        """Validar archivos de datos"""
        details = []
        score = 0
        
        # Verificar directorios de datos
        data_dirs = ['data/json', 'data/excel', 'data/logs', 'data/backup']
        existing_dirs = sum(1 for d in data_dirs if (self.base_path / d).exists())
        
        if existing_dirs == len(data_dirs):
            details.append("Todos los directorios de datos disponibles ✅")
            score += 40
        elif existing_dirs > 0:
            details.append(f"Directorios de datos parciales ({existing_dirs}/{len(data_dirs)}) ⚠️")
            score += 20
        
        # Verificar permisos de escritura
        try:
            test_file = self.base_path / 'data/test_write.tmp'
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(test_file, 'w') as f:
                f.write("test")
            
            test_file.unlink()  # Eliminar archivo de prueba
            details.append("Permisos de escritura OK ✅")
            score += 60
            
        except Exception as e:
            details.append(f"Sin permisos de escritura: {e} ❌")
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 40 else 'fail',
            'score': score,
            'details': details
        }
    
    def _validate_security(self) -> dict:
        """Validar aspectos de seguridad"""
        details = []
        score = 50  # Base score
        
        # Verificar .gitignore
        gitignore_path = self.base_path / '.gitignore'
        if gitignore_path.exists():
            details.append(".gitignore presente ✅")
            score += 20
        else:
            details.append(".gitignore ausente ⚠️")
        
        # Verificar archivos sensibles no expuestos
        sensitive_patterns = ['*.log', '*.tmp', '__pycache__', '*.pyc']
        exposed_files = []
        
        for pattern in sensitive_patterns:
            files = list(self.base_path.glob(f"**/{pattern}"))
            if files:
                exposed_files.extend(files)
        
        if not exposed_files:
            details.append("Sin archivos sensibles expuestos ✅")
            score += 30
        else:
            details.append(f"Archivos sensibles encontrados: {len(exposed_files)} ⚠️")
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 50 else 'fail',
            'score': score,
            'details': details
        }
    
    def _validate_functionality(self) -> dict:
        """Validar funcionalidad básica"""
        details = []
        score = 0
        
        # Prueba de importación de main
        try:
            sys.path.insert(0, str(self.base_path))
            
            # Intentar importar componente principal
            try:
                from main import main
                details.append("Módulo principal importable ✅")
                score += 50
            except ImportError:
                try:
                    from safe_main import main
                    details.append("Módulo seguro importable ✅")
                    score += 40
                except ImportError:
                    details.append("Módulos principales no importables ❌")
        except Exception as e:
            details.append(f"Error en importación: {e} ❌")
        
        # Prueba de configuración básica
        try:
            config_path = self.base_path / 'config/development.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                required_sections = ['hardware', 'web', 'system']
                missing_sections = [s for s in required_sections if s not in config]
                
                if not missing_sections:
                    details.append("Configuración completa ✅")
                    score += 50
                else:
                    details.append(f"Secciones faltantes en config: {missing_sections} ⚠️")
                    score += 25
        except Exception as e:
            details.append(f"Error validando configuración: {e} ❌")
        
        return {
            'status': 'pass' if score >= 70 else 'warning' if score >= 40 else 'fail',
            'score': score,
            'details': details
        }
    
    def _generate_recommendations(self):
        """Generar recomendaciones basadas en los resultados"""
        recommendations = []
        
        # Analizar resultados por categoría
        for category, result in self.results['categories'].items():
            if result['status'] == 'fail':
                if 'Dependencies' in category:
                    recommendations.append("Ejecutar: pip install -r requirements.txt")
                elif 'Directory' in category:
                    recommendations.append("Ejecutar: python setup_project.py")
                elif 'Configuration' in category:
                    recommendations.append("Crear archivos de configuración necesarios")
                elif 'Python' in category:
                    recommendations.append("Actualizar Python a versión 3.8 o superior")
        
        # Recomendaciones generales
        if self.results['overall_status'] in ['poor', 'acceptable']:
            recommendations.append("Ejecutar configuración completa: python quick_start.py")
        
        self.results['recommendations'] = list(set(recommendations))  # Eliminar duplicados
    
    def save_report(self, filename: str = None):
        """Guardar reporte de validación"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{timestamp}.json"
        
        report_path = self.base_path / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Reporte guardado: {report_path}")
        return report_path


def main():
    """Función principal de validación"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validador completo del sistema Johnson Controls"
    )
    parser.add_argument('--save-report', action='store_true', 
                       help='Guardar reporte en archivo JSON')
    parser.add_argument('--quick', action='store_true',
                       help='Validación rápida (solo críticos)')
    
    args = parser.parse_args()
    
    try:
        validator = SystemValidator()
        results = validator.validate_all()
        
        if args.save_report:
            validator.save_report()
        
        # Código de salida basado en el estado
        exit_codes = {
            'excellent': 0,
            'good': 0, 
            'acceptable': 1,
            'poor': 2
        }
        
        sys.exit(exit_codes.get(results['overall_status'], 2))
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Validación cancelada por usuario")
        sys.exit(3)
    except Exception as e:
        print(f"\n❌ Error durante validación: {e}")
        logger.error(f"Validation error: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()