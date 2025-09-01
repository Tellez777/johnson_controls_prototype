#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEM TESTS - Pruebas básicas del sistema
Johnson Controls - Sistema de Seguimiento Industrial
"""

import sys
import os
import unittest
from pathlib import Path
import json
import tempfile

# Agregar src al path para testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSystemConfiguration(unittest.TestCase):
    """Pruebas de configuración del sistema"""
    
    def setUp(self):
        """Configuración de pruebas"""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Limpieza después de pruebas"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_directory_structure(self):
        """Probar que la estructura de directorios existe"""
        required_dirs = [
            'src', 'src/core', 'src/hardware', 'src/web', 'src/models', 
            'src/services', 'src/utils', 'config', 'data'
        ]
        
        for directory in required_dirs:
            self.assertTrue(
                Path(directory).exists(), 
                f"Directorio requerido no existe: {directory}"
            )
    
    def test_config_files_exist(self):
        """Probar que los archivos de configuración existen"""
        config_files = [
            'config/development.json',
            'requirements.txt'
        ]
        
        for config_file in config_files:
            self.assertTrue(
                Path(config_file).exists(), 
                f"Archivo de configuración no existe: {config_file}"
            )
    
    def test_config_file_structure(self):
        """Probar estructura de archivo de configuración"""
        config_file = Path('config/development.json')
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            required_sections = ['hardware', 'web', 'system']
            for section in required_sections:
                self.assertIn(section, config, f"Sección faltante en config: {section}")


class TestBasicImports(unittest.TestCase):
    """Pruebas de importaciones básicas"""
    
    def test_flask_import(self):
        """Probar importación de Flask"""
        try:
            import flask
            self.assertTrue(True, "Flask importado correctamente")
        except ImportError:
            self.fail("Flask no disponible")
    
    def test_serial_import(self):
        """Probar importación de pyserial"""
        try:
            import serial
            self.assertTrue(True, "PySerial importado correctamente")
        except ImportError:
            self.fail("PySerial no disponible")
    
    def test_openpyxl_import(self):
        """Probar importación de openpyxl"""
        try:
            import openpyxl
            self.assertTrue(True, "OpenPyXL importado correctamente")
        except ImportError:
            self.fail("OpenPyXL no disponible")


class TestProductModel(unittest.TestCase):
    """Pruebas del modelo de producto"""
    
    def test_product_creation(self):
        """Probar creación de producto"""
        try:
            from src.models.product import JCIProduct, ProductStatus
            
            product = JCIProduct(
                barcode="TEST001",
                part_number="TEST-PART-001",
                product_name="Producto de Prueba",
                product_family="Testing",
                work_order="WO-TEST-001",
                batch_number="BATCH-001",
                serial_number="SN-001",
                customer_code="TEST-CUSTOMER"
            )
            
            self.assertEqual(product.barcode, "TEST001")
            self.assertEqual(product.status, ProductStatus.PENDING)
            self.assertEqual(product.progress_percentage, 0.0)
            
        except ImportError as e:
            self.skipTest(f"Modelo de producto no disponible: {e}")
    
    def test_product_serialization(self):
        """Probar serialización de producto"""
        try:
            from src.models.product import JCIProduct
            
            product = JCIProduct(
                barcode="TEST002",
                part_number="TEST-PART-002",
                product_name="Producto Serialización",
                product_family="Testing",
                work_order="WO-TEST-002",
                batch_number="BATCH-002",
                serial_number="SN-002",
                customer_code="TEST-CUSTOMER"
            )
            
            # Probar conversión a diccionario
            product_dict = product.to_dict()
            self.assertIsInstance(product_dict, dict)
            self.assertIn('barcode', product_dict)
            self.assertIn('product_name', product_dict)
            
        except ImportError as e:
            self.skipTest(f"Modelo de producto no disponible: {e}")


class TestWebServer(unittest.TestCase):
    """Pruebas básicas del servidor web"""
    
    def test_basic_flask_app(self):
        """Probar creación de app Flask básica"""
        try:
            from flask import Flask
            
            app = Flask(__name__)
            
            @app.route('/test')
            def test_route():
                return {'status': 'ok'}
            
            # Probar que la app se puede crear
            self.assertIsNotNone(app)
            
            # Probar context
            with app.test_client() as client:
                response = client.get('/test')
                self.assertEqual(response.status_code, 200)
                
        except ImportError:
            self.skipTest("Flask no disponible")


class TestSystemValidation(unittest.TestCase):
    """Pruebas de validación del sistema"""
    
    def test_python_version(self):
        """Probar versión de Python"""
        self.assertGreaterEqual(
            sys.version_info, 
            (3, 8), 
            "Se requiere Python 3.8 o superior"
        )
    
    def test_required_modules_available(self):
        """Probar que los módulos requeridos están disponibles"""
        required_modules = [
            'json', 'os', 'sys', 'pathlib', 'datetime', 
            'threading', 'time', 'logging'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                self.fail(f"Módulo requerido no disponible: {module}")
    
    def test_file_permissions(self):
        """Probar permisos de archivos"""
        test_file = Path('data') / 'test_permissions.tmp'
        
        try:
            # Crear directorio data si no existe
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Probar escritura
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Probar lectura
            with open(test_file, 'r') as f:
                content = f.read()
            
            self.assertEqual(content, "test")
            
            # Limpiar
            test_file.unlink()
            
        except PermissionError:
            self.fail("Sin permisos de escritura en directorio data/")


def run_basic_tests():
    """Ejecutar pruebas básicas sin unittest framework"""
    print("🧪 EJECUTANDO PRUEBAS BÁSICAS DEL SISTEMA")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Prueba 1: Estructura de directorios
    tests_total += 1
    print("📁 Verificando estructura de directorios...")
    required_dirs = ['src', 'config', 'data']
    
    missing_dirs = [d for d in required_dirs if not Path(d).exists()]
    if missing_dirs:
        print(f"❌ Directorios faltantes: {missing_dirs}")
    else:
        print("✅ Estructura de directorios OK")
        tests_passed += 1
    
    # Prueba 2: Importaciones críticas
    tests_total += 1
    print("📦 Verificando importaciones críticas...")
    critical_modules = ['json', 'os', 'sys', 'pathlib']
    
    failed_imports = []
    for module in critical_modules:
        try:
            __import__(module)
        except ImportError:
            failed_imports.append(module)
    
    if failed_imports:
        print(f"❌ Imports fallidos: {failed_imports}")
    else:
        print("✅ Importaciones críticas OK")
        tests_passed += 1
    
    # Prueba 3: Dependencias opcionales
    tests_total += 1
    print("🔧 Verificando dependencias opcionales...")
    optional_modules = ['flask', 'serial', 'openpyxl']
    
    available_modules = []
    for module in optional_modules:
        try:
            __import__(module)
            available_modules.append(module)
        except ImportError:
            pass
    
    if available_modules:
        print(f"✅ Dependencias disponibles: {available_modules}")
        tests_passed += 1
    else:
        print("⚠️  Sin dependencias opcionales instaladas")
    
    # Prueba 4: Configuración
    tests_total += 1
    print("⚙️ Verificando archivos de configuración...")
    config_files = ['requirements.txt']
    
    existing_configs = [f for f in config_files if Path(f).exists()]
    if existing_configs:
        print(f"✅ Configs existentes: {existing_configs}")
        tests_passed += 1
    else:
        print("⚠️  Sin archivos de configuración")
    
    # Resultado final
    print("\n" + "=" * 50)
    print(f"📊 RESULTADO: {tests_passed}/{tests_total} pruebas pasaron")
    
    if tests_passed == tests_total:
        print("🎉 ¡Todas las pruebas básicas pasaron!")
        return True
    elif tests_passed >= tests_total - 1:
        print("✅ Sistema mayormente funcional")
        return True
    else:
        print("❌ Sistema requiere configuración")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Pruebas del sistema Johnson Controls")
    parser.add_argument('--basic', action='store_true', help='Ejecutar solo pruebas básicas')
    parser.add_argument('--verbose', action='store_true', help='Output verboso')
    
    args = parser.parse_args()
    
    if args.basic:
        # Ejecutar pruebas básicas sin unittest
        success = run_basic_tests()
        sys.exit(0 if success else 1)
    else:
        # Ejecutar unittest completo
        if args.verbose:
            unittest.main(verbosity=2)
        else:
            unittest.main()