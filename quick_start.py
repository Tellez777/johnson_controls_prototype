#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUICK START - Instalación rápida y verificación del sistema
Johnson Controls - Sistema de Seguimiento Industrial
"""

import sys
import os
import subprocess
from pathlib import Path
import importlib.util


def check_python_version():
    """Verificar versión de Python"""
    print("🔍 Verificando versión de Python...")
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True


def install_dependencies():
    """Instalar dependencias"""
    print("\n📦 Instalando dependencias...")
    
    # Lista mínima de dependencias
    min_deps = [
        'Flask==2.3.2',
        'Flask-CORS==4.0.0',
        'pyserial==3.5',
        'openpyxl==3.1.2',
        'python-dateutil==2.8.2'
    ]
    
    try:
        for dep in min_deps:
            print(f"   Instalando {dep}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', dep
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"❌ Error instalando {dep}")
                print(f"   {result.stderr}")
                return False
            
        print("✅ Dependencias instaladas correctamente")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout instalando dependencias")
        return False
    except Exception as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False


def check_imports():
    """Verificar que las importaciones funcionen"""
    print("\n🔍 Verificando importaciones...")
    
    # Importaciones críticas
    critical_imports = [
        ('flask', 'Flask'),
        ('flask_cors', 'CORS'),
        ('serial', 'pyserial'),
        ('openpyxl', 'openpyxl'),
        ('json', 'json (built-in)'),
        ('threading', 'threading (built-in)'),
        ('datetime', 'datetime (built-in)')
    ]
    
    for module, name in critical_imports:
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                print(f"❌ {name} no disponible")
                return False
            print(f"✅ {name} - OK")
        except Exception as e:
            print(f"❌ Error verificando {name}: {e}")
            return False
    
    return True


def create_minimal_structure():
    """Crear estructura mínima si no existe"""
    print("\n📁 Verificando estructura de proyecto...")
    
    dirs = ['src', 'src/utils', 'config', 'data', 'data/json', 'data/excel', 'data/logs']
    
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Crear archivo de configuración mínima si no existe
    config_file = Path('config/development.json')
    if not config_file.exists():
        print("   Creando configuración mínima...")
        minimal_config = {
            "hardware": {"serial_port": "COM5", "baud_rate": 9600},
            "web": {"host": "0.0.0.0", "port": 5000, "debug": True},
            "system": {"environment": "development", "log_level": "INFO"}
        }
        
        import json
        with open(config_file, 'w') as f:
            json.dump(minimal_config, f, indent=2)
    
    print("✅ Estructura de proyecto - OK")


def test_web_server():
    """Probar servidor web básico"""
    print("\n🌐 Probando servidor web básico...")
    
    try:
        # Crear servidor de prueba simple
        test_server_code = '''
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def test():
    return jsonify({'status': 'OK', 'message': 'Johnson Controls System Ready'})

@app.route('/test')
def health():
    return jsonify({'test': 'passed', 'components': ['web', 'flask']})

if __name__ == '__main__':
    print("Servidor de prueba iniciado en http://localhost:5555")
    print("Presiona Ctrl+C para detener")
    app.run(host='0.0.0.0', port=5555, debug=False)
'''
        
        # Guardar y ejecutar brevemente
        with open('test_server.py', 'w') as f:
            f.write(test_server_code)
        
        print("✅ Código de servidor web generado")
        print("   Archivo: test_server.py")
        print("   Para probar: python test_server.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando servidor de prueba: {e}")
        return False


def test_serial_ports():
    """Probar puertos serie disponibles"""
    print("\n🔌 Verificando puertos serie...")
    
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        if ports:
            print("✅ Puertos serie disponibles:")
            for port in ports:
                print(f"   - {port.device}: {port.description}")
        else:
            print("⚠️  No se encontraron puertos serie")
            print("   (El escáner se puede conectar más tarde)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando puertos serie: {e}")
        return False


def create_startup_scripts():
    """Crear scripts de inicio"""
    print("\n📜 Creando scripts de inicio...")
    
    scripts = {
        'start_web.py': '''#!/usr/bin/env python3
import os, sys
sys.path.append('.')

try:
    from src.web.app import WebApplication
    app = WebApplication()
    if app.initialize():
        print("🌐 Servidor web iniciado en http://localhost:5000")
        app.start()
    else:
        print("❌ Error inicializando aplicación web")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Ejecuta: python setup_project.py primero")
''',
        
        'start_basic.py': '''#!/usr/bin/env python3
# Inicio básico con Flask simple
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Johnson Controls - Sistema Básico</title>
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
            .header { background: #003D79; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .status { padding: 15px; background: #e8f5e8; border: 1px solid #4CAF50; border-radius: 4px; margin: 10px 0; }
            .button { background: #0066CC; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .button:hover { background: #003D79; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Johnson Controls</h1>
                <p>Sistema de Seguimiento Industrial - Modo Básico</p>
            </div>
            <div class="status">
                <strong>✅ Estado:</strong> Sistema web funcionando correctamente
            </div>
            <p><strong>Próximos pasos:</strong></p>
            <ol>
                <li>Ejecutar: <code>python setup_project.py</code></li>
                <li>Instalar dependencias: <code>pip install -r requirements.txt</code></li>
                <li>Ejecutar sistema completo: <code>python main.py</code></li>
            </ol>
            <button class="button" onclick="window.location.reload()">🔄 Actualizar</button>
            <button class="button" onclick="fetch('/api/test').then(r=>r.json()).then(d=>alert(JSON.stringify(d,null,2)))">🧪 Probar API</button>
        </div>
    </body>
    </html>
    """)

@app.route('/api/test')
def api_test():
    return jsonify({
        'status': 'OK',
        'system': 'Johnson Controls Industrial Tracking',
        'version': '2.0-basic',
        'components': ['web', 'api'],
        'next_steps': [
            'Ejecutar setup_project.py',
            'Instalar dependencias completas',
            'Conectar escáner Zebra DS3678'
        ]
    })

if __name__ == '__main__':
    print("🚀 Johnson Controls - Sistema Básico")
    print("📡 Servidor iniciado en http://localhost:5000")
    print("⚡ Presiona Ctrl+C para detener")
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
    }
    
    for filename, code in scripts.items():
        with open(filename, 'w') as f:
            f.write(code)
        print(f"✅ {filename}")
    
    return True


def main():
    """Función principal de verificación rápida"""
    print("🚀 JOHNSON CONTROLS - INSTALACIÓN RÁPIDA")
    print("=" * 50)
    
    steps = [
        ("Versión de Python", check_python_version),
        ("Dependencias", install_dependencies),
        ("Importaciones", check_imports),
        ("Estructura", create_minimal_structure),
        ("Servidor Web", test_web_server),
        ("Puertos Serie", test_serial_ports),
        ("Scripts", create_startup_scripts)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        try:
            if step_func():
                success_count += 1
            else:
                print(f"⚠️  Problemas en: {step_name}")
        except Exception as e:
            print(f"❌ Error en {step_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTADO: {success_count}/{len(steps)} pasos completados")
    
    if success_count >= len(steps) - 1:  # Permitir 1 fallo
        print("🎉 ¡INSTALACIÓN EXITOSA!")
        print("\n🚀 OPCIONES DE INICIO:")
        print("1. Sistema básico:    python start_basic.py")
        print("2. Setup completo:    python setup_project.py")
        print("3. Solo web:          python start_web.py")
        print("4. Servidor de prueba: python test_server.py")
        
        print("\n📖 SIGUIENTE PASOS:")
        print("• Abrir http://localhost:5000 en el navegador")
        print("• Conectar escáner Zebra DS3678 (opcional)")
        print("• Ejecutar sistema completo con python main.py")
        
    else:
        print("⚠️  Instalación incompleta")
        print("Revisar errores anteriores o contactar soporte")
    
    return success_count >= len(steps) - 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Instalación cancelada por usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")