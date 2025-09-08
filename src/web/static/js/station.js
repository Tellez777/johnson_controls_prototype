// JavaScript para la página de estación
class StationManager {
    constructor() {
        this.stageId = this.getStageIdFromUrl();
        this.currentOperator = null;
        this.stageInfo = null;
        this.productsInStage = [];
        this.activityLog = [];
        this.refreshInterval = null;
        
        this.initializeStation();
    }

    getStageIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return parseInt(urlParams.get('stage')) || 20; // Default a primera etapa
    }

    async initializeStation() {
        try {
            console.log(`Inicializando estación para etapa ${this.stageId}`);
            
            await this.loadStageInfo();
            await this.loadOperatorInfo();
            await this.loadStationProducts();
            
            this.setupEventListeners();
            this.startAutoRefresh();
            this.updateKPIs();
            
            this.addActivityLog('Sistema de estación iniciado');
        } catch (error) {
            console.error('Error inicializando estación:', error);
            this.addActivityLog('Error inicializando estación: ' + error.message);
        }
    }

    async loadStageInfo() {
        try {
            const response = await fetch('/api/data/stages');
            const data = await response.json();
            
            // Encontrar la etapa actual
            this.stageInfo = data.active_stages.find(stage => stage.id === this.stageId);
            
            if (this.stageInfo) {
                document.getElementById('station-name').textContent = `Estación: ${this.stageInfo.name}`;
                document.getElementById('station-description').textContent = this.stageInfo.description || 'Estación de trabajo industrial';
                document.getElementById('target-time').textContent = `${this.stageInfo.target_time_minutes} min`;
                document.getElementById('quality-threshold').textContent = `${this.stageInfo.quality_threshold}%`;
                document.getElementById('stage-type').textContent = this.stageInfo.stage_type || 'producción';
                
                // Instrucciones básicas basadas en el tipo de etapa
                const instructions = this.getStageInstructions(this.stageInfo.name);
                document.getElementById('stage-instructions').innerHTML = instructions;
            } else {
                throw new Error(`Etapa ${this.stageId} no encontrada`);
            }
        } catch (error) {
            console.error('Error cargando información de etapa:', error);
            throw error;
        }
    }

    async loadOperatorInfo() {
        try {
            const response = await fetch('/api/data/operators');
            const data = await response.json();
            
            // Encontrar operador de esta etapa
            for (const [opId, operator] of Object.entries(data.operators)) {
                if (operator.assigned_stages && operator.assigned_stages.length > 0) {
                    const hasStage = operator.assigned_stages.some(stage => stage.stage_id === this.stageId);
                    if (hasStage) {
                        this.currentOperator = operator;
                        document.getElementById('current-operator').textContent = operator.name;
                        break;
                    }
                }
            }
            
            if (!this.currentOperator && this.stageInfo) {
                // Fallback: usar operador definido en la etapa
                document.getElementById('current-operator').textContent = this.stageInfo.operator_name || 'No asignado';
            }
        } catch (error) {
            console.error('Error cargando información de operador:', error);
            document.getElementById('current-operator').textContent = 'Error cargando';
        }
    }

    async loadStationProducts() {
        try {
            const response = await fetch('/api/data/products');
            const data = await response.json();
            
            // Filtrar productos que están en esta etapa
            this.productsInStage = data.products.filter(product => 
                product.current_stage === this.stageId && product.status !== 'Completado'
            );
            
            this.renderProducts();
        } catch (error) {
            console.error('Error cargando productos de la estación:', error);
            this.showError('Error cargando productos');
        }
    }

    renderProducts() {
        const container = document.getElementById('station-products-container');
        
        if (this.productsInStage.length === 0) {
            container.innerHTML = `
                <div class="no-products">
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        <div style="font-size: 48px; margin-bottom: 16px;">📦</div>
                        <h3>No hay productos en esta etapa</h3>
                        <p>Los productos aparecerán aquí cuando lleguen a la etapa ${this.stageInfo?.name}</p>
                    </div>
                </div>
            `;
            return;
        }

        const html = this.productsInStage.map(product => `
            <div class="product-card station-product" data-barcode="${product.barcode}">
                <div class="product-header">
                    <span class="product-barcode">${product.barcode}</span>
                    <span class="product-priority ${product.priority?.toLowerCase() || 'normal'}">${product.priority || 'Normal'}</span>
                </div>
                <div class="product-details">
                    <div><strong>Descripción:</strong> ${product.part_number || 'N/A'}</div>
                    <div><strong>Cliente:</strong> ${product.customer_code || 'N/A'}</div>
                    <div><strong>Progreso:</strong> ${product.progress_percentage?.toFixed(1) || 0}%</div>
                    <div><strong>Lote:</strong> ${product.batch_number || 'N/A'}</div>
                    <div><strong>Ingresó:</strong> ${this.formatDateTime(product.created_at)}</div>
                    <div><strong>Calidad:</strong> ${product.current_quality_score?.toFixed(1) || 0}%</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }

    setupEventListeners() {
        // Input de escaneo
        const barcodeInput = document.getElementById('barcode-input');
        barcodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.processManualScan();
            }
        });

        // Mantener focus en el input
        barcodeInput.addEventListener('blur', () => {
            setTimeout(() => barcodeInput.focus(), 100);
        });

        // Filtros
        document.getElementById('priority-filter').addEventListener('change', () => {
            this.filterProducts();
        });
    }

    async processManualScan() {
        const barcodeInput = document.getElementById('barcode-input');
        const barcode = barcodeInput.value.trim();
        
        if (!barcode) {
            this.showScanStatus('error', 'Por favor ingrese un código válido');
            return;
        }

        try {
            this.showScanStatus('scanning', 'Procesando escaneo...');
            
            // Verificar si el producto existe
            const response = await fetch('/api/data/products');
            const data = await response.json();
            const product = data.products.find(p => p.barcode === barcode);
            
            if (!product) {
                this.showScanStatus('error', 'Producto no encontrado');
                this.addActivityLog(`Escaneo fallido: ${barcode} (no encontrado)`);
                return;
            }

            // Mostrar modal de confirmación
            this.showScanConfirmation(product);
            
        } catch (error) {
            console.error('Error procesando escaneo:', error);
            this.showScanStatus('error', 'Error procesando escaneo');
            this.addActivityLog(`Error en escaneo: ${barcode}`);
        } finally {
            barcodeInput.value = '';
        }
    }

    showScanConfirmation(product) {
        document.getElementById('scanned-barcode').textContent = product.barcode;
        document.getElementById('scanned-description').textContent = product.part_number || 'N/A';
        document.getElementById('scanned-status').textContent = product.status || 'N/A';
        
        const modal = document.getElementById('scanConfirmationModal');
        modal.style.display = 'block';
        
        // Almacenar producto para confirmación
        this.pendingScanProduct = product;
    }

    async confirmScan() {
        if (!this.pendingScanProduct) return;
        
        try {
            this.showScanStatus('scanning', 'Confirmando escaneo...');
            
            // Enviar simulación de escaneo
            const response = await fetch('/api/control/simulate_scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    barcode: this.pendingScanProduct.barcode
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showScanStatus('success', `Producto ${this.pendingScanProduct.barcode} procesado exitosamente`);
                this.addActivityLog(`Escaneo exitoso: ${this.pendingScanProduct.barcode}`);
                
                // Actualizar datos después de un momento
                setTimeout(() => {
                    this.loadStationProducts();
                    this.updateKPIs();
                }, 1500);
            } else {
                this.showScanStatus('error', result.message || 'Error procesando producto');
                this.addActivityLog(`Escaneo fallido: ${this.pendingScanProduct.barcode} - ${result.message}`);
            }
            
        } catch (error) {
            console.error('Error confirmando escaneo:', error);
            this.showScanStatus('error', 'Error enviando escaneo al sistema');
        } finally {
            this.closeScanModal();
        }
    }

    showScanStatus(type, message) {
        const statusElement = document.getElementById('scan-status');
        statusElement.className = `scan-status ${type}`;
        
        let icon = '▶';
        if (type === 'scanning') icon = '◐';
        if (type === 'success') icon = '✓';
        if (type === 'error') icon = '✗';
        
        statusElement.innerHTML = `
            <div class="scan-ready">
                <div class="scan-icon">${icon}</div>
                <p>${message}</p>
            </div>
        `;
        
        // Volver al estado normal después de unos segundos
        if (type !== 'scanning') {
            setTimeout(() => {
                statusElement.className = 'scan-status';
                statusElement.innerHTML = `
                    <div class="scan-ready">
                        <div class="scan-icon">📱</div>
                        <p>Listo para escanear</p>
                    </div>
                `;
            }, 3000);
        }
    }

    filterProducts() {
        const priorityFilter = document.getElementById('priority-filter').value;
        
        let filteredProducts = [...this.productsInStage];
        
        if (priorityFilter) {
            filteredProducts = filteredProducts.filter(p => 
                (p.priority || 'Normal') === priorityFilter
            );
        }
        
        // Re-renderizar con productos filtrados
        const tempProducts = this.productsInStage;
        this.productsInStage = filteredProducts;
        this.renderProducts();
        this.productsInStage = tempProducts;
    }

    async updateKPIs() {
        try {
            // Productos en etapa (real)
            document.getElementById('products-in-stage').textContent = this.productsInStage.length;
            
            // Completados hoy - contar productos con completed_at de hoy
            const today = new Date().toISOString().split('T')[0];
            const response = await fetch('/api/data/products');
            const data = await response.json();
            
            const completedToday = data.products.filter(product => {
                if (!product.completed_at) return false;
                return product.completed_at.startsWith(today);
            }).length;
            document.getElementById('products-completed-today').textContent = completedToday;
            
            // Tiempo promedio - usar target_time de la etapa o calcular promedio real
            if (this.productsInStage.length > 0) {
                const avgCycleTime = this.productsInStage.reduce((sum, product) => {
                    return sum + (product.total_cycle_time || 0);
                }, 0) / this.productsInStage.length;
                
                if (avgCycleTime > 0) {
                    document.getElementById('avg-cycle-time').textContent = `${Math.floor(avgCycleTime)}m`;
                } else if (this.stageInfo) {
                    document.getElementById('avg-cycle-time').textContent = `${this.stageInfo.target_time_minutes}m`;
                } else {
                    document.getElementById('avg-cycle-time').textContent = `--`;
                }
            } else if (this.stageInfo) {
                document.getElementById('avg-cycle-time').textContent = `${this.stageInfo.target_time_minutes}m`;
            } else {
                document.getElementById('avg-cycle-time').textContent = `--`;
            }
            
            // Eficiencia - usar efficiency_score promedio de productos en esta etapa
            if (this.productsInStage.length > 0) {
                const avgEfficiency = this.productsInStage.reduce((sum, product) => {
                    return sum + (product.efficiency_score || 0);
                }, 0) / this.productsInStage.length;
                document.getElementById('efficiency-rate').textContent = `${Math.floor(avgEfficiency)}%`;
            } else {
                document.getElementById('efficiency-rate').textContent = `--`;
            }
            
        } catch (error) {
            console.error('Error actualizando KPIs:', error);
            // Fallback a valores por defecto
            document.getElementById('products-in-stage').textContent = this.productsInStage.length;
            document.getElementById('products-completed-today').textContent = '--';
            document.getElementById('avg-cycle-time').textContent = this.stageInfo ? `${this.stageInfo.target_time_minutes}m` : '--';
            document.getElementById('efficiency-rate').textContent = '--';
        }
    }

    addActivityLog(message) {
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        this.activityLog.unshift({ timestamp, message });
        
        // Mantener solo los últimos 20 elementos
        if (this.activityLog.length > 20) {
            this.activityLog = this.activityLog.slice(0, 20);
        }
        
        this.renderActivityLog();
    }

    renderActivityLog() {
        const container = document.getElementById('activity-log');
        const html = this.activityLog.map(item => `
            <div class="activity-item">
                <div class="activity-time">${item.timestamp}</div>
                <div class="activity-text">${item.message}</div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }

    async refreshStationData() {
        try {
            this.showScanStatus('scanning', 'Actualizando datos...');
            await this.loadStationProducts();
            await this.updateKPIs();
            this.addActivityLog('Datos actualizados');
            this.showScanStatus('success', 'Datos actualizados correctamente');
        } catch (error) {
            console.error('Error actualizando datos:', error);
            this.showScanStatus('error', 'Error actualizando datos');
        }
    }

    startAutoRefresh() {
        // Actualizar cada 30 segundos
        this.refreshInterval = setInterval(() => {
            this.refreshStationData();
        }, 30000);
    }

    getStageInstructions(stageName) {
        const instructions = {
            'Soldadura': `
                <ul>
                    <li>Verificar que las piezas estén limpias y sin óxido</li>
                    <li>Aplicar soldadura según especificaciones técnicas</li>
                    <li>Revisar la calidad de la soldadura</li>
                    <li>Registrar el escaneo al completar el proceso</li>
                </ul>
            `,
            'Pulido': `
                <ul>
                    <li>Inspeccionar la superficie soldada</li>
                    <li>Aplicar proceso de pulido según estándar</li>
                    <li>Verificar acabado superficial</li>
                    <li>Escanear producto al finalizar</li>
                </ul>
            `,
            'Ensamblado': `
                <ul>
                    <li>Verificar componentes necesarios</li>
                    <li>Seguir secuencia de ensamblado</li>
                    <li>Aplicar torque especificado</li>
                    <li>Confirmar ensamblado completo con escaneo</li>
                </ul>
            `,
            'Control Calidad': `
                <ul>
                    <li>Realizar inspección visual completa</li>
                    <li>Ejecutar pruebas funcionales</li>
                    <li>Verificar dimensiones críticas</li>
                    <li>Aprobar o rechazar mediante escaneo</li>
                </ul>
            `,
            'Pintura': `
                <ul>
                    <li>Preparar superficie para pintura</li>
                    <li>Aplicar primer si es necesario</li>
                    <li>Aplicar pintura según especificación</li>
                    <li>Registrar finalización del proceso</li>
                </ul>
            `,
            'Embalaje': `
                <ul>
                    <li>Inspeccionar producto terminado</li>
                    <li>Aplicar protecciones necesarias</li>
                    <li>Embalar según procedimiento</li>
                    <li>Escanear para completar el proceso</li>
                </ul>
            `
        };
        
        return instructions[stageName] || '<p>Seguir procedimiento estándar de la etapa</p>';
    }

    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-ES') + ' ' + 
                   date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        } catch {
            return 'N/A';
        }
    }

    closeScanModal() {
        document.getElementById('scanConfirmationModal').style.display = 'none';
        this.pendingScanProduct = null;
        
        // Refocus en input de escaneo
        document.getElementById('barcode-input').focus();
    }

    showError(message) {
        console.error(message);
        // Aquí podrías agregar una notificación visual de error
    }
}

// Funciones globales para eventos
function processManualScan() {
    if (window.stationManager) {
        window.stationManager.processManualScan();
    }
}

function refreshStationData() {
    if (window.stationManager) {
        window.stationManager.refreshStationData();
    }
}

function filterProducts() {
    if (window.stationManager) {
        window.stationManager.filterProducts();
    }
}

function confirmScan() {
    if (window.stationManager) {
        window.stationManager.confirmScan();
    }
}

function closeScanModal() {
    if (window.stationManager) {
        window.stationManager.closeScanModal();
    }
}

// Inicializar cuando la página carga
document.addEventListener('DOMContentLoaded', () => {
    window.stationManager = new StationManager();
    
    // Actualizar timestamp cada minuto
    setInterval(() => {
        document.getElementById('last-update-time').textContent = 
            new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }, 60000);
    
    // Establecer timestamp inicial
    document.getElementById('last-update-time').textContent = 
        new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
});