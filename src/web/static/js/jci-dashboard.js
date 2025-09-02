// Johnson Controls Dashboard - Enhanced JavaScript v2.0
class JCIDashboard {
    constructor() {
        this.autoUpdate = true;
        this.updateInterval = null;
        this.charts = {};
        this.analyticsData = {
            timeline: [],
            efficiency: [],
            bottlenecks: {}
        };
        this.analyticsVisible = false;
        this.lastDataTimestamp = null;
        
        // Configuración de colores Johnson Controls para Chart.js
        this.chartColors = {
            primary: '#00B8E0',
            secondary: '#0399CC',
            tertiary: '#0554A3',
            dark: '#08338F',
            success: '#29B582',
            accent: '#7DBA00',
            warning: '#F59E0B',
            error: '#EF4444',
            background: 'rgba(0, 184, 224, 0.1)',
            grid: '#E2E8F0',
            text: '#2D3748'
        };
        
        // Configuración base para Chart.js con colores JCI
        Chart.defaults.color = this.chartColors.text;
        Chart.defaults.borderColor = this.chartColors.grid;
        Chart.defaults.backgroundColor = this.chartColors.background;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoUpdate();
        console.log('Johnson Controls Dashboard v2.0 inicializado');
    }
    
    setupEventListeners() {
        // Atajos de teclado mejorados
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName.toLowerCase() === 'input') return;
            
            switch(e.key.toLowerCase()) {
                case '1': this.simulateScan('JCI240001A'); break;
                case '2': this.simulateScan('JCI240002B'); break;
                case '3': this.simulateScan('JCI240003C'); break;
                case 'r': this.refreshData(); break;
                case 'a': this.toggleAnalytics(); break;
                case ' ':
                    e.preventDefault();
                    this.toggleAutoUpdate();
                    break;
            }
        });
        
        // Event listeners para elementos del DOM
        this.setupDOMEventListeners();
        
        // Limpiar al cerrar ventana
        window.addEventListener('beforeunload', () => {
            this.stopAutoUpdate();
        });
    }
    
    setupDOMEventListeners() {
        // Botón de toggle analytics
        const toggleBtn = document.getElementById('toggle-analytics');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleAnalytics());
        }
        
        // Botones de simulación
        const simulateButtons = document.querySelectorAll('[onclick*="simulateScan"]');
        simulateButtons.forEach(btn => {
            const productCode = btn.onclick.toString().match(/JCI\w+/)?.[0];
            if (productCode) {
                btn.onclick = null; // Remove inline onclick
                btn.addEventListener('click', () => this.simulateScan(productCode));
            }
        });
        
        // Botones de cambio de etapa
        const stageButtons = document.querySelectorAll('[onclick*="changeStage"]');
        stageButtons.forEach(btn => {
            const stage = btn.onclick.toString().match(/\d+/)?.[0];
            if (stage) {
                btn.onclick = null; // Remove inline onclick
                btn.addEventListener('click', () => this.changeStage(parseInt(stage)));
            }
        });
    }
    
    async loadInitialData() {
        try {
            // Intentar cargar datos del endpoint mejorado primero
            await this.loadEnhancedData();
        } catch (error) {
            console.warn('Endpoint mejorado no disponible, usando endpoint básico:', error);
            // Fallback a endpoint básico
            await this.loadBasicData();
        }
    }
    
    async loadEnhancedData() {
        const response = await fetch('/api/enhanced_data');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        this.updateUI(data);
        this.updateAnalytics(data);
        this.updateConnectionStatus(true, data);
    }
    
    async loadBasicData() {
        // Usar endpoints del sistema original
        const response = await fetch('/api/data/main');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        this.updateUI(data);
        this.updateConnectionStatus(true, data);
    }
    
    async loadData() {
        try {
            await this.loadInitialData();
        } catch (error) {
            console.error('Error cargando datos:', error);
            this.updateConnectionStatus(false, null, error.message);
            this.updateSystemInfo('Error de conexión: ' + error.message, 'error');
        }
    }
    
    updateUI(data) {
        // Actualizar estadísticas básicas
        const stats = data.estadisticas || {};
        this.updateElement('total-products', stats.total || 0);
        this.updateElement('completed-products', stats.completados || 0);
        this.updateElement('process-products', stats.en_proceso || 0);
        this.updateElement('pending-products', stats.pendientes || 0);
        
        // Actualizar etapa actual
        this.updateElement('current-stage', data.etapa_nombre || '-');
        
        // Actualizar productos con visualización mejorada
        this.updateProductsDisplay(data.productos || {});
        
        // Actualizar KPIs operacionales si están disponibles
        this.updateOperationalKPIs(data);
        
        // Actualizar insights si están disponibles
        this.updateInsights(data.insights || []);
        
        // Actualizar información del sistema
        this.updateSystemInfo('Sistema funcionando correctamente', 'success');
        this.updateElement('last-update', this.formatTimestamp(data.timestamp));
        
        // Marcar timestamp de últimos datos
        this.lastDataTimestamp = new Date(data.timestamp || new Date());
    }
    
    updateOperationalKPIs(data) {
        const kpis = data.kpis_operacionales || {};
        
        // KPIs mejorados si están disponibles
        if (kpis.efficiency_rate !== undefined) {
            this.updateElement('efficiency-rate', kpis.efficiency_rate + '%');
        }
        
        if (kpis.throughput_rate !== undefined) {
            this.updateElement('throughput-rate', kpis.throughput_rate);
        }
        
        if (kpis.avg_cycle_time !== undefined) {
            this.updateElement('avg-cycle-time', kpis.avg_cycle_time + 's');
        }
        
        if (kpis.bottleneck_stage !== undefined) {
            this.updateElement('bottleneck-stage', kpis.bottleneck_stage);
        }
        
        if (kpis.oee_score !== undefined) {
            this.updateElement('oee-score', kpis.oee_score + '%');
        }
        
        if (kpis.quality_score !== undefined) {
            this.updateElement('quality-score', kpis.quality_score + '%');
        }
        
        // Fallback a cálculos básicos si no hay KPIs mejorados
        if (!kpis.efficiency_rate) {
            this.calculateBasicKPIs(data);
        }
    }
    
    calculateBasicKPIs(data) {
        const stats = data.estadisticas || {};
        const productos = data.productos || {};
        
        // Eficiencia General
        const efficiency = stats.progreso_promedio || 0;
        this.updateElement('efficiency-rate', Math.round(efficiency) + '%');
        
        // Throughput simulado
        const throughput = Math.round((stats.completados || 0) * 2.5);
        this.updateElement('throughput-rate', throughput);
        
        // Tiempo de ciclo simulado
        const avgCycleTime = Math.round(120 - (efficiency * 0.8));
        this.updateElement('avg-cycle-time', avgCycleTime + 's');
        
        // Cuello de botella básico
        const bottleneck = this.identifyBasicBottleneck(productos);
        this.updateElement('bottleneck-stage', bottleneck);
        
        // OEE y Calidad simulados
        const oee = Math.max(75, Math.min(95, efficiency + 10));
        const quality = Math.max(90, Math.min(98, 96 - Object.keys(productos).length * 0.2));
        this.updateElement('oee-score', Math.round(oee) + '%');
        this.updateElement('quality-score', Math.round(quality) + '%');
    }
    
    identifyBasicBottleneck(productos) {
        const stageCounts = {};
        const stageNames = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        };
        
        Object.values(productos).forEach(producto => {
            const stage = producto.etapa_actual_numero || 1;
            stageCounts[stage] = (stageCounts[stage] || 0) + 1;
        });
        
        if (Object.keys(stageCounts).length === 0) return '-';
        
        const bottleneckStage = Object.keys(stageCounts).reduce((a, b) => 
            stageCounts[a] > stageCounts[b] ? a : b
        );
        
        return stageNames[bottleneckStage] || '-';
    }
    
    updateProductsDisplay(productos) {
        const container = document.getElementById('products-container');
        
        if (Object.keys(productos).length === 0) {
            container.innerHTML = '<div class="loading">No hay datos de productos disponibles</div>';
            return;
        }
        
        container.innerHTML = '';
        
        Object.entries(productos).forEach(([codigo, producto]) => {
            const productDiv = this.createProductCard(codigo, producto);
            container.appendChild(productDiv);
        });
    }
    
    createProductCard(codigo, producto) {
        const statusClass = this.getStatusClass(producto.estado);
        const progressColor = this.getProgressColor(producto.progreso);
        const etapasCompletadas = this.generateStageIndicators(producto);
        
        const productDiv = document.createElement('div');
        productDiv.className = 'product-card';
        productDiv.innerHTML = `
            <div class="product-header">
                <div>
                    <div class="product-name">${producto.nombre}</div>
                    <div class="product-code">${codigo}</div>
                </div>
                <div class="product-status ${statusClass}">${producto.estado}</div>
            </div>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${producto.progreso}%; background: ${progressColor};"></div>
                    <div class="progress-text">${producto.progreso}%</div>
                </div>
            </div>
            <div class="stages-completed">
                ${etapasCompletadas}
            </div>
            <div class="product-details">
                <div><strong>Etapa:</strong> ${producto.etapa_actual}</div>
                <div><strong>Actualizado:</strong> ${this.formatTimestamp(producto.fecha)}</div>
                <div><strong>Operador:</strong> ${this.getOperatorName(producto.etapa_actual_numero)}</div>
                <div><strong>Tiempo:</strong> ${this.calculateProcessTime(producto)}h</div>
            </div>
        `;
        
        return productDiv;
    }
    
    generateStageIndicators(producto) {
        const stages = ['SOL', 'PUL', 'PRE', 'CAL', 'PIN', 'ALM'];
        const currentStage = producto.etapa_actual_numero || 1;
        const progress = producto.progreso || 0;
        
        return stages.map((stage, index) => {
            let stageClass = 'stage-pending';
            if (index + 1 < currentStage || (index + 1 === currentStage && progress === 100)) {
                stageClass = 'stage-completed';
            } else if (index + 1 === currentStage) {
                stageClass = 'stage-current';
            }
            
            return `<span class="stage-indicator ${stageClass}">${stage}</span>`;
        }).join('');
    }
    
    getOperatorName(stageNumber) {
        const operators = {
            1: 'Lucero M.',
            2: 'Felipe H.',
            3: 'Fernando G.',
            4: 'Control QC',
            5: 'Acabados',
            6: 'Almacén'
        };
        return operators[stageNumber] || 'N/A';
    }
    
    calculateProcessTime(producto) {
        const baseTime = 2.5;
        const progress = producto.progreso || 0;
        const stage = producto.etapa_actual_numero || 1;
        return (baseTime * stage * (progress / 100)).toFixed(1);
    }
    
    updateAnalytics(data) {
        const timestamp = new Date();
        const stats = data.estadisticas || {};
        
        // Agregar punto de datos históricos
        this.analyticsData.timeline.push({
            time: timestamp,
            efficiency: stats.progreso_promedio || 0,
            completed: stats.completados || 0,
            inProcess: stats.en_proceso || 0
        });
        
        // Mantener solo los últimos 20 puntos
        if (this.analyticsData.timeline.length > 20) {
            this.analyticsData.timeline.shift();
        }
        
        // Actualizar gráficos si están visibles
        if (this.analyticsVisible) {
            this.updateCharts(data.productos || {}, stats);
        }
    }
    
    updateInsights(insights) {
        const container = document.getElementById('insights-container');
        
        if (!insights || insights.length === 0) {
            container.innerHTML = '<div class="loading">No hay insights disponibles</div>';
            return;
        }
        
        container.innerHTML = insights.map(insight => `
            <div class="insight-card">
                <div class="insight-title">${insight.title}</div>
                <div class="insight-text">${insight.text}</div>
            </div>
        `).join('');
    }
    
    toggleAnalytics() {
        const content = document.getElementById('analytics-content');
        const toggleText = document.getElementById('analytics-toggle-text');
        const toggleIcon = document.getElementById('analytics-toggle-icon');
        
        if (!content) return;
        
        this.analyticsVisible = !this.analyticsVisible;
        
        if (this.analyticsVisible) {
            content.style.display = 'block';
            if (toggleText) toggleText.textContent = 'Ocultar Gráficas';
            if (toggleIcon) {
                toggleIcon.textContent = '▲';
                toggleIcon.classList.add('expanded');
            }
            
            // Inicializar gráficos cuando se muestran
            setTimeout(() => this.initializeCharts(), 100);
        } else {
            content.style.display = 'none';
            if (toggleText) toggleText.textContent = 'Mostrar Gráficas';
            if (toggleIcon) {
                toggleIcon.textContent = '▼';
                toggleIcon.classList.remove('expanded');
            }
        }
    }
    
    initializeCharts() {
        if (!this.analyticsVisible) return;
        
        this.initProgressChart();
        this.initStatusChart();
        this.initStageEfficiencyChart();
        this.initTimelineChart();
    }
    
    initProgressChart() {
        const canvas = document.getElementById('progressChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico existente si existe
        if (this.charts.progress) {
            this.charts.progress.destroy();
        }
        
        this.charts.progress = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Controlador HVAC', 'Sistema Batería', 'Switch Inteligente'],
                datasets: [{
                    label: 'Progreso (%)',
                    data: [0, 0, 0],
                    backgroundColor: [
                        this.chartColors.primary,
                        this.chartColors.success,
                        this.chartColors.accent
                    ],
                    borderColor: [
                        this.chartColors.secondary,
                        this.chartColors.success,
                        this.chartColors.accent
                    ],
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: this.chartColors.grid },
                        ticks: { color: this.chartColors.text }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: this.chartColors.text }
                    }
                }
            }
        });
    }
    
    initStatusChart() {
        const canvas = document.getElementById('statusChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.status) {
            this.charts.status.destroy();
        }
        
        this.charts.status = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completados', 'En Proceso', 'Pendientes'],
                datasets: [{
                    data: [0, 0, 3],
                    backgroundColor: [
                        this.chartColors.success,
                        this.chartColors.primary,
                        this.chartColors.warning
                    ],
                    borderColor: '#FFFFFF',
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: this.chartColors.text,
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                }
            }
        });
    }
    
    initStageEfficiencyChart() {
        const canvas = document.getElementById('stageEfficiencyChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.stageEfficiency) {
            this.charts.stageEfficiency.destroy();
        }
        
        this.charts.stageEfficiency = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Soldadura', 'Pulido', 'Presión', 'Calidad', 'Pintura', 'Almacén'],
                datasets: [{
                    label: 'Eficiencia (%)',
                    data: [85, 92, 78, 88, 95, 90],
                    backgroundColor: 'rgba(0, 184, 224, 0.2)',
                    borderColor: this.chartColors.primary,
                    borderWidth: 2,
                    pointBackgroundColor: this.chartColors.primary,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: this.chartColors.grid },
                        pointLabels: { color: this.chartColors.text },
                        ticks: {
                            color: this.chartColors.text,
                            backdropColor: 'transparent'
                        }
                    }
                }
            }
        });
    }
    
    initTimelineChart() {
        const canvas = document.getElementById('timelineChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.timeline) {
            this.charts.timeline.destroy();
        }
        
        this.charts.timeline = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Eficiencia (%)',
                    data: [],
                    borderColor: this.chartColors.primary,
                    backgroundColor: 'rgba(0, 184, 224, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Completados',
                    data: [],
                    borderColor: this.chartColors.success,
                    backgroundColor: 'rgba(41, 181, 130, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: this.chartColors.text,
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: this.chartColors.grid },
                        ticks: { color: this.chartColors.text, maxTicksLimit: 6 }
                    },
                    y: {
                        grid: { color: this.chartColors.grid },
                        ticks: { color: this.chartColors.text }
                    }
                }
            }
        });
    }
    
    updateCharts(productos, stats) {
        this.updateProgressChart(productos);
        this.updateStatusChart(stats);
        this.updateStageEfficiencyChart();
        this.updateTimelineChart();
    }
    
    updateProgressChart(productos) {
        if (!this.charts.progress) return;
        
        const codigos = ['JCI240001A', 'JCI240002B', 'JCI240003C'];
        const progressData = codigos.map(codigo =>
            productos[codigo] ? productos[codigo].progreso : 0
        );
        
        this.charts.progress.data.datasets[0].data = progressData;
        this.charts.progress.update('none');
    }
    
    updateStatusChart(stats) {
        if (!this.charts.status) return;
        
        this.charts.status.data.datasets[0].data = [
            stats.completados || 0,
            stats.en_proceso || 0,
            stats.pendientes || 0
        ];
        this.charts.status.update('none');
    }
    
    updateStageEfficiencyChart() {
        if (!this.charts.stageEfficiency) return;
        
        // Simular datos de eficiencia por etapa
        const efficiencyData = [
            85 + Math.random() * 10,
            90 + Math.random() * 8,
            78 + Math.random() * 12,
            88 + Math.random() * 10,
            95 + Math.random() * 5,
            87 + Math.random() * 10
        ];
        
        this.charts.stageEfficiency.data.datasets[0].data = efficiencyData;
        this.charts.stageEfficiency.update('none');
    }
    
    updateTimelineChart() {
        if (!this.charts.timeline) return;
        
        const labels = this.analyticsData.timeline.map(point =>
            point.time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        );
        const efficiencyData = this.analyticsData.timeline.map(point => point.efficiency);
        const completedData = this.analyticsData.timeline.map(point => point.completed);
        
        this.charts.timeline.data.labels = labels;
        this.charts.timeline.data.datasets[0].data = efficiencyData;
        this.charts.timeline.data.datasets[1].data = completedData;
        this.charts.timeline.update('none');
    }
    
    async simulateScan(productCode) {
        try {
            this.showNotification(`Enviando simulación: ${productCode}`, 'warning');
            
            // Intentar usar endpoint mejorado
            let endpoint = '/api/simulate_scan_enhanced';
            let response = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({codigo: productCode})
            });
            
            // Fallback a endpoint básico si el mejorado no está disponible
            if (!response.ok && response.status === 404) {
                endpoint = '/api/simulate_scan';
                response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({codigo: productCode})
                });
            }
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(result.message, 'success');
                setTimeout(() => this.loadData(), 1000);
            } else {
                this.showNotification('Error: ' + result.message, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    async changeStage(etapa) {
        try {
            this.showNotification(`Cambiando a etapa ${etapa}`, 'warning');
            
            // Intentar endpoint mejorado primero
            let endpoint = '/api/stage_change_enhanced';
            let response = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({etapa: etapa})
            });
            
            // Fallback a endpoint básico
            if (!response.ok && response.status === 404) {
                endpoint = '/api/change_stage';
                response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({etapa: etapa})
                });
            }
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(`Etapa cambiada a ${etapa}`, 'success');
                setTimeout(() => this.loadData(), 500);
            } else {
                this.showNotification('Error cambiando etapa: ' + result.message, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    refreshData() {
        this.showNotification('Actualizando datos...', 'info');
        this.loadData();
    }
    
    exportReport() {
        this.showNotification('Función de exportación en desarrollo', 'info');
    }
    
    updateConnectionStatus(isConnected, data, errorMessage = '') {
        const systemStatus = document.getElementById('system-status');
        const systemStatusText = document.getElementById('system-status-text');
        const scannerStatus = document.getElementById('scanner-status');
        const scannerStatusText = document.getElementById('scanner-status-text');
        
        if (isConnected && data && !data.error) {
            if (systemStatus) systemStatus.className = 'status-dot status-active';
            if (systemStatusText) systemStatusText.textContent = 'Operativo';
            if (scannerStatus) scannerStatus.className = 'status-dot status-active';
            if (scannerStatusText) scannerStatusText.textContent = 'Conectado';
        } else if (data && data.error) {
            if (systemStatus) systemStatus.className = 'status-dot status-warning';
            if (systemStatusText) systemStatusText.textContent = 'Advertencia';
            if (scannerStatus) scannerStatus.className = 'status-dot status-warning';
            if (scannerStatusText) scannerStatusText.textContent = 'Desconectado';
        } else {
            if (systemStatus) systemStatus.className = 'status-dot status-error';
            if (systemStatusText) systemStatusText.textContent = 'Error';
            if (scannerStatus) scannerStatus.className = 'status-dot status-error';
            if (scannerStatusText) scannerStatusText.textContent = 'Error';
        }
    }
    
    updateSystemInfo(message, type) {
        const systemInfo = document.getElementById('system-info');
        if (systemInfo) {
            systemInfo.textContent = message;
            systemInfo.className = `system-${type}`;
        }
    }
    
    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 4000);
    }
    
    startAutoUpdate() {
        if (this.updateInterval) this.stopAutoUpdate();
        this.updateInterval = setInterval(() => this.loadData(), 5000); // Cada 5 segundos
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    toggleAutoUpdate() {
        this.autoUpdate = !this.autoUpdate;
        if (this.autoUpdate) {
            this.startAutoUpdate();
            this.showNotification('Actualización automática activada', 'success');
        } else {
            this.stopAutoUpdate();
            this.showNotification('Actualización automática pausada', 'warning');
        }
    }
    
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Sin datos';
        try {
            return new Date(timestamp).toLocaleString('es-MX', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Sin datos';
        }
    }
    
    getStatusClass(estado) {
        return estado === 'Completado' ? 'status-completado' :
               estado === 'En Proceso' ? 'status-proceso' : 'status-pendiente';
    }
    
    getProgressColor(progreso) {
        if (progreso === 0) return '#EF4444';
        if (progreso < 100) return 'linear-gradient(90deg, #F59E0B, #00B8E0)';
        return 'linear-gradient(90deg, #29B582, #00B8E0)';
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
}

// Funciones globales para mantener compatibilidad con HTML
let dashboard;

function refreshData() {
    if (dashboard) dashboard.refreshData();
}

function simulateScan(productCode) {
    if (dashboard) dashboard.simulateScan(productCode);
}

function changeStage(etapa) {
    if (dashboard) dashboard.changeStage(etapa);
}

function exportReport() {
    if (dashboard) dashboard.exportReport();
}

function toggleAnalytics() {
    if (dashboard) dashboard.toggleAnalytics();
}

// Inicialización cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('Johnson Controls Dashboard v2.0 cargando...');
    
    // Pequeña demora para asegurar que todos los elementos estén listos
    setTimeout(() => {
        dashboard = new JCIDashboard();
    }, 500);
});