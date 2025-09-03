# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Johnson Controls Industrial Tracking System - A modular barcode scanning and product tracking system for industrial manufacturing environments using Zebra scanners.

## Architecture

The system follows a modular architecture with the following key layers:

- **Core**: Product management, workflow engine, scanner management (`src/core/`)
- **Hardware**: Zebra scanner integration and serial communication (`src/hardware/`)
- **Models**: Data models for products, stages, analytics (`src/models/`)
- **Services**: Background services for analytics, data sync, notifications (`src/services/`)
- **Web**: Flask-based web application with REST APIs (`src/web/`)
- **Utils**: Configuration, logging, validation utilities (`src/utils/`)

### Key Components

- **ScannerManager** (`src/core/scanner_manager.py`): Central orchestrator for scanning operations
- **JCIProduct** (`src/models/product.py`): Core product data model with status tracking
- **WebApplication** (`src/web/app.py`): Flask web server with modular API endpoints
- **ConfigManager** (`src/utils/config.py`): Centralized configuration system with environment support

## Running the Application

### Main Entry Points
```bash
# Full system (scanner + web + analytics)
py main.py --mode full

# Scanner only mode
py main.py --mode scanner

# Web interface only
py main.py --mode web

# Interactive console mode
py main.py --mode console

# Analytics service only
py main.py --mode analytics
```

### Quick Start Options
```bash
# Basic startup
py start_basic.py

# Quick development start
py quick_start.py

# Web-only server
py run_web.py

# Scanner-only service
py run_scanner.py
```

### Configuration
- Environment can be set with `--config` parameter (defaults to 'development')
- Log level can be set with `--log-level` parameter
- Web port can be overridden with `--port` parameter

## Development Commands

### Testing
```bash
# Run tests using unittest (pytest not installed by default)
py -m unittest discover tests/

# Run specific test
py -m unittest tests.test_system
```

### Code Quality
The requirements.txt includes optional development tools:
```bash
# Install development dependencies first
py -m pip install black flake8 mypy

# Code formatting
py -m black src/

# Linting
py -m flake8 src/

# Type checking
py -m mypy src/
```

### Dependencies
```bash
# Install all dependencies
py -m pip install -r requirements.txt

# Core dependencies only (Flask, pyserial, openpyxl, python-dateutil)
```

## Data Storage

- **Excel Files**: Product tracking data in `data/excel/`
- **JSON State**: System state and web commands in `data/json/`
- **Logs**: System logs in `data/logs/`
- **Backups**: Automated backups in `data/backup/`

## Configuration Files

- System configuration managed through `src/utils/config.py`
- Environment-specific configs supported
- Hardware settings (COM ports, scanner models) configurable
- Web server settings (port, CORS) configurable

## API Endpoints

The web application provides REST APIs:
- **Data API** (`/api/data/*`): Product and system data endpoints
- **Control API** (`/api/control/*`): System control and operations
- **Analytics API** (`/api/analytics/*`): Analytics and reporting

## Stage Management

Six-stage production workflow:
1. Soldadura (Welding)
2. Pulido (Polishing)  
3. Presión (Pressure)
4. Calidad (Quality)
5. Pintura (Painting)
6. Almacén (Storage)

Products progress through stages via barcode scanning at each station.