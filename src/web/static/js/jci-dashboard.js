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
        this.updateCurrentShiftByTime();
        
        // Actualizar turno cada minuto
        setInterval(() => this.updateCurrentShiftByTime(), 60000);
        
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
        
        // Botones de simulación - actualizar para códigos reales
        const simulateButtons = document.querySelectorAll('[onclick*="simulateScan"]');
        simulateButtons.forEach(btn => {
            let productCode = btn.onclick.toString().match(/\w+/)?.[0];
            // Mapear botones a códigos reales
            if (btn.textContent.includes('Producto A')) productCode = 'fewygfyu3';
            else if (btn.textContent.includes('Producto B')) productCode = 'fwe24gvfd';
            else if (btn.textContent.includes('Producto C')) productCode = 'fdgffdwwd3';
            
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
        
        // Buscador de productos
        const searchInput = document.getElementById('product-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterProducts(e.target.value);
            });
        }
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
        const response = await fetch('/api/data/enhanced_data');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        this.updateUI(data);
        this.updateAnalytics(data);
        // No llamar updateConnectionStatus aquí, ya que updateUI maneja el estado correctamente
    }
    
    async loadBasicData() {
        // Usar endpoints del sistema original
        const response = await fetch('/api/data/main');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        this.updateUI(data);
        // No llamar updateConnectionStatus aquí, ya que updateUI maneja el estado correctamente
    }
    
    async loadData() {
        try {
            await this.loadInitialData();
        } catch (error) {
            console.error('Error cargando datos:', error);
            // En caso de error de conexión, marcar sistema como error
            this.updateSystemStatus(false);
            this.updateScannerStatus(false);
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
        
        // Actualizar estado del sistema y escáner
        const sistemaActivo = data.sistema_activo === true;
        const scannerConectado = data.scanner_conectado === true;
        
        this.updateSystemStatus(sistemaActivo);
        this.updateScannerStatus(scannerConectado);
        
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
        
        // Actualizar gráficas si están visibles
        if (this.analyticsVisible && data.datos_graficas) {
            this.updateCharts(data.datos_graficas);
        }
        
        // Actualizar listas de gestión
        if (data.operadores) {
            this.updateOperatorsList(data.operadores);
        }
        this.updateStagesList();
        
        // Marcar timestamp de últimos datos
        this.lastDataTimestamp = new Date(data.timestamp || new Date());
        
        // Almacenar datos para uso en edición
        this.lastLoadedData = data;
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
        const searchInput = document.getElementById('product-search');
        const currentSearchTerm = searchInput ? searchInput.value : '';
        
        if (Object.keys(productos).length === 0) {
            container.innerHTML = '<div class="loading">No hay datos de productos disponibles</div>';
            return;
        }
        
        container.innerHTML = '';
        
        Object.entries(productos).forEach(([codigo, producto]) => {
            const productDiv = this.createProductCard(codigo, producto);
            container.appendChild(productDiv);
        });
        
        // Reaplicar el filtro si había una búsqueda activa
        if (currentSearchTerm.trim() !== '') {
            this.filterProducts(currentSearchTerm);
        }
    }
    
    filterProducts(searchTerm) {
        const productCards = document.querySelectorAll('.product-card');
        const search = searchTerm.toLowerCase().trim();
        
        productCards.forEach(card => {
            const productCode = card.getAttribute('data-product-code');
            const visible = productCode && productCode.includes(search);
            
            if (visible || search === '') {
                card.classList.remove('hidden');
                card.style.display = 'block';
            } else {
                card.classList.add('hidden');
                card.style.display = 'none';
            }
        });
        
        // Mostrar mensaje si no hay resultados
        const visibleCards = document.querySelectorAll('.product-card:not(.hidden)');
        const container = document.getElementById('products-container');
        
        // Remover mensaje de no resultados previo
        const noResultsMsg = container.querySelector('.no-results-message');
        if (noResultsMsg) {
            noResultsMsg.remove();
        }
        
        if (visibleCards.length === 0 && search !== '') {
            const noResultsDiv = document.createElement('div');
            noResultsDiv.className = 'no-results-message loading';
            noResultsDiv.innerHTML = `No se encontraron productos con el código: "<strong>${searchTerm}</strong>"`;
            container.appendChild(noResultsDiv);
        }
    }
    
    createProductCard(codigo, producto) {
        const statusClass = this.getStatusClass(producto.estado);
        const progressColor = this.getProgressColor(producto.progreso);
        const etapasCompletadas = this.generateStageIndicators(producto);
        
        const productDiv = document.createElement('div');
        productDiv.className = 'product-card';
        productDiv.setAttribute('data-product-code', codigo.toLowerCase());
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
            <div class="insight-card ${insight.type}">
                <div class="insight-title">${insight.title}</div>
                <div class="insight-text">${insight.description || insight.text || ''}</div>
                ${insight.action ? `<div class="insight-action">Recomendación: ${insight.action}</div>` : ''}
            </div>
        `).join('');
    }
    
    toggleAnalytics() {
        console.log('toggleAnalytics() llamado, estado actual:', this.analyticsVisible);
        
        const content = document.getElementById('analytics-content');
        const toggleText = document.getElementById('analytics-toggle-text');
        const toggleIcon = document.getElementById('analytics-toggle-icon');
        
        console.log('Elementos encontrados:', { 
            content: !!content, 
            toggleText: !!toggleText, 
            toggleIcon: !!toggleIcon 
        });
        
        if (!content) {
            console.error('No se encontró el elemento analytics-content');
            return;
        }
        
        this.analyticsVisible = !this.analyticsVisible;
        console.log('Nuevo estado analyticsVisible:', this.analyticsVisible);
        
        if (this.analyticsVisible) {
            console.log('Mostrando analytics...');
            content.style.display = 'block';
            console.log('Display style cambiado a block');
            
            if (toggleText) toggleText.textContent = 'Ocultar Gráficas';
            if (toggleIcon) {
                toggleIcon.textContent = '▲';
                toggleIcon.classList.add('expanded');
            }
            
            // Verificar que el contenido sea visible
            setTimeout(() => {
                const isVisible = content.offsetHeight > 0;
                console.log('Contenido visible después de 100ms:', isVisible);
                console.log('Altura del contenedor:', content.offsetHeight);
            }, 100);
            
            // Inicializar gráficos cuando se muestran
            setTimeout(() => {
                console.log('Intentando inicializar gráficos...');
                this.initializeCharts();
                // Recargar datos para las gráficas
                this.loadData();
            }, 200);
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
        
        console.log('Inicializando gráficas...');
        
        // Verificar si Chart.js está disponible
        if (typeof Chart === 'undefined') {
            console.error('Chart.js no está disponible');
            return;
        }
        
        // Pequeña demora para asegurar que el DOM esté listo
        setTimeout(() => {
            this.initProgressChart();
            this.initStatusChart();
            this.initStageEfficiencyChart();
            this.initTimelineChart();
            
            // Cargar datos inmediatamente después de inicializar
            this.loadData();
        }, 200);
    }
    
    initProgressChart() {
        const canvas = document.getElementById('progressChart');
        if (!canvas) {
            console.error('Canvas progressChart no encontrado');
            return;
        }
        
        console.log('Inicializando Progress Chart...');
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico existente si existe
        if (this.charts.progress) {
            this.charts.progress.destroy();
        }
        
        try {
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
            console.log('Progress Chart inicializado exitosamente');
        } catch (error) {
            console.error('Error inicializando Progress Chart:', error);
        }
    }
    
    initStatusChart() {
        const canvas = document.getElementById('statusChart');
        if (!canvas) {
            console.error('Canvas statusChart no encontrado');
            return;
        }
        console.log('Inicializando Status Chart...');
        
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
            
            // Usar el nuevo endpoint que funciona correctamente
            let endpoint = '/api/data/stage_control';
            let response = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({stage: etapa})
            });
            
            // Fallback a endpoint básico si el nuevo no está disponible
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
                // Obtener el nombre de la etapa desde el mapeo local
                const stageNames = {
                    1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
                    4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
                };
                const stageName = stageNames[etapa] || `Etapa ${etapa}`;
                
                this.showNotification(`Etapa cambiada a ${etapa}: ${stageName}`, 'success');
                
                // Actualizar indicadores visuales
                this.updateStageIndicators(etapa, stageName);
                
                setTimeout(() => this.loadData(), 500);
            } else {
                this.showNotification('Error cambiando etapa: ' + result.message, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    updateStageIndicators(activeStage, stageName) {
        // Obtener nombres de etapas
        const stageNames = {
            1: 'Soldadura', 2: 'Pulido', 3: 'Presión',
            4: 'Calidad', 5: 'Pintura', 6: 'Almacén'
        };
        
        // Remover clase active de todos los botones
        document.querySelectorAll('.stage-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Agregar clase active al botón seleccionado
        const activeButton = document.getElementById(`stage-btn-${activeStage}`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        // Actualizar indicador de etapa activa
        const indicator = document.getElementById('active-stage-indicator');
        if (indicator) {
            const displayName = stageName || stageNames[activeStage] || `Etapa ${activeStage}`;
            indicator.textContent = ` (Activa: ${displayName})`;
        }
        
        console.log(`Etapa activa actualizada: ${activeStage} - ${stageName}`);
    }
    
    refreshData() {
        this.showNotification('Actualizando datos...', 'info');
        this.loadData();
    }
    
    exportReport() {
        this.showNotification('Generando reporte Excel...', 'info');
        
        // Create a temporary link to trigger download
        const downloadLink = document.createElement('a');
        downloadLink.href = '/api/data/export/excel';
        downloadLink.download = '';
        downloadLink.style.display = 'none';
        
        document.body.appendChild(downloadLink);
        
        // Add event listeners to handle success/error
        let downloadStarted = false;
        
        const checkDownload = setTimeout(() => {
            if (!downloadStarted) {
                this.showNotification('Descarga de Excel iniciada', 'success');
                downloadStarted = true;
            }
        }, 1000);
        
        downloadLink.addEventListener('click', () => {
            downloadStarted = true;
            clearTimeout(checkDownload);
            this.showNotification('Descargando archivo Excel...', 'success');
        });
        
        // Trigger the download
        try {
            downloadLink.click();
            
            // Clean up
            setTimeout(() => {
                if (document.body.contains(downloadLink)) {
                    document.body.removeChild(downloadLink);
                }
            }, 5000);
            
        } catch (error) {
            this.showNotification('Error iniciando descarga: ' + error.message, 'error');
            if (document.body.contains(downloadLink)) {
                document.body.removeChild(downloadLink);
            }
        }
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
    
    updateSystemStatus(isActive) {
        const statusDot = document.getElementById('system-status');
        const statusText = document.getElementById('system-status-text');
        
        if (statusDot) {
            statusDot.className = isActive ? 'status-dot status-active' : 'status-dot status-error';
        }
        if (statusText) {
            statusText.textContent = isActive ? 'Operativo' : 'Detenido';
        }
    }
    
    updateScannerStatus(isConnected) {
        const statusDot = document.getElementById('scanner-status');
        const statusText = document.getElementById('scanner-status-text');
        
        if (statusDot) {
            statusDot.className = isConnected ? 'status-dot status-active' : 'status-dot status-error';
        }
        if (statusText) {
            statusText.textContent = isConnected ? 'Conectado' : 'Desconectado';
        }
    }
    
    updateCharts(chartData) {
        if (!chartData) return;
        
        // Actualizar gráfica de progreso
        if (this.charts.progress && chartData.progreso) {
            this.charts.progress.data.labels = chartData.progreso.labels;
            this.charts.progress.data.datasets[0].data = chartData.progreso.data;
            this.charts.progress.update();
        }
        
        // Actualizar gráfica de estados
        if (this.charts.status && chartData.estados) {
            this.charts.status.data.datasets[0].data = chartData.estados.data;
            this.charts.status.update();
        }
        
        // Actualizar gráfica de eficiencia por etapa
        if (this.charts.stageEfficiency && chartData.eficiencia_etapas) {
            this.charts.stageEfficiency.data.datasets[0].data = chartData.eficiencia_etapas.data;
            this.charts.stageEfficiency.update();
        }
        
        // Actualizar gráfica de timeline
        if (this.charts.timeline && chartData.timeline) {
            this.charts.timeline.data.labels = chartData.timeline.labels;
            this.charts.timeline.data.datasets[0].data = chartData.timeline.efficiency;
            this.charts.timeline.data.datasets[1].data = chartData.timeline.completed;
            this.charts.timeline.update();
        }
    }
    
    // ===== FUNCIONES DE GESTIÓN DE DATOS =====
    
    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        this.showNotification('Subiendo archivo...', 'info');
        
        fetch('/api/data/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                this.showNotification('Archivo subido correctamente', 'success');
                setTimeout(() => this.loadData(), 1000);
            } else {
                this.showNotification('Error: ' + result.message, 'error');
            }
        })
        .catch(error => {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        });
        
        // Limpiar input
        event.target.value = '';
    }
    
    showDataStructure() {
        const modal = this.createModal('Estructura de Datos Excel/CSV', `
            <div class="data-structure">
                <h4>Formato requerido para Excel/CSV:</h4>
                <div class="structure-example">
barcode,product_name,product_type,status,current_stage
fewygfyu3,Controlador HVAC Premium,HVAC_CONTROLLER,En Proceso,2
fwe24gvfd,Sistema Batería Industrial,BATTERY_SYSTEM,En Proceso,4
fdgffdwwd3,Switch Inteligente IoT,IOT_SWITCH,Completado,6

Campos requeridos:
- barcode: Código de barras único
- product_name: Nombre del producto  
- product_type: Tipo de producto
- status: Estado (Pendiente/En Proceso/Completado)
- current_stage: Etapa actual (1-6)

Campos opcionales:
- progress_percentage: Porcentaje de progreso (0-100)
- quality_score: Puntuación de calidad (0-100)
- operator_current: ID del operador actual
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cerrar</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    
    // ===== FUNCIONES DE GESTIÓN DE TURNOS =====
    
    updateOperatorsList(operators) {
        const container = document.getElementById('operators-list');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(operators).forEach(([id, operator]) => {
            const operatorDiv = document.createElement('div');
            operatorDiv.className = 'operator-item';
            operatorDiv.innerHTML = `
                <div class="operator-info">
                    <div class="operator-name">${operator.name}</div>
                    <div class="operator-details">${operator.shift} - ${operator.station}</div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-xs btn-warning" onclick="editOperator('${id}')">✏️</button>
                    <button class="btn btn-xs btn-error" onclick="deleteOperator('${id}')">🗑️</button>
                </div>
            `;
            container.appendChild(operatorDiv);
        });
    }
    
    async updateStagesList() {
        const container = document.getElementById('stages-list');
        if (!container) return;
        
        try {
            // Obtener etapas dinámicamente desde el servidor
            const response = await fetch('/api/data/stages');
            let stages = [];
            
            if (response.ok) {
                const result = await response.json();
                stages = result.stages || [];
            } else {
                // Fallback a etapas por defecto si no se puede obtener del servidor
                stages = [
                    {id: 1, name: 'Soldadura', description: 'Proceso de soldadura', is_default: true},
                    {id: 2, name: 'Pulido', description: 'Acabado y pulido', is_default: true},
                    {id: 3, name: 'Presión', description: 'Pruebas de presión', is_default: true},
                    {id: 4, name: 'Calidad', description: 'Control de calidad', is_default: true},
                    {id: 5, name: 'Pintura', description: 'Acabado final', is_default: true},
                    {id: 6, name: 'Almacén', description: 'Almacenamiento', is_default: true}
                ];
            }
            
            container.innerHTML = '';
            
            stages.forEach(stage => {
                const stageDiv = document.createElement('div');
                stageDiv.className = 'stage-item';
                
                // Determinar si se puede eliminar (solo etapas personalizadas, no las básicas)
                const canDelete = !stage.is_default && stage.id > 6;
                
                stageDiv.innerHTML = `
                    <div class="stage-info">
                        <div class="stage-name">${stage.name}</div>
                        <div class="stage-details">${stage.description}</div>
                        ${stage.is_default ? '<div class="stage-badge">Sistema</div>' : '<div class="stage-badge custom">Personalizada</div>'}
                    </div>
                    <div class="item-actions">
                        <button class="btn btn-xs btn-warning" onclick="editStage(${stage.id})" title="Editar">✏️</button>
                        ${canDelete ? `<button class="btn btn-xs btn-error" onclick="deleteStage(${stage.id})" title="Eliminar">🗑️</button>` : ''}
                    </div>
                `;
                container.appendChild(stageDiv);
            });
            
        } catch (error) {
            console.error('Error cargando etapas:', error);
            container.innerHTML = '<div class="loading">Error cargando etapas</div>';
        }
    }
    
    changeShift(shiftName) {
        this.showNotification(`Cambiando turno a ${shiftName}...`, 'info');
        
        fetch('/api/data/change_shift', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({shift: shiftName})
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                this.showNotification(`Turno cambiado a ${shiftName}`, 'success');
                this.updateElement('current-shift', shiftName);
                this.updateElement('current-shift-display', shiftName);
                setTimeout(() => this.loadData(), 500);
            } else {
                this.showNotification('Error cambiando turno: ' + result.message, 'error');
            }
        })
        .catch(error => {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        });
    }
    
    editShiftSchedule() {
        const modal = this.createModal('Editar Horarios de Turnos', `
            <div class="form-group">
                <label>Turno Día</label>
                <input type="time" id="dia-start" value="06:00"> - 
                <input type="time" id="dia-end" value="14:00">
            </div>
            <div class="form-group">
                <label>Turno Tarde</label>
                <input type="time" id="tarde-start" value="14:00"> - 
                <input type="time" id="tarde-end" value="22:00">
            </div>
            <div class="form-group">
                <label>Turno Noche</label>
                <input type="time" id="noche-start" value="22:00"> - 
                <input type="time" id="noche-end" value="06:00">
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                <button class="btn btn-primary" onclick="saveShiftSchedule()">Guardar</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    addOperator() {
        const modal = this.createModal('Agregar Operador', `
            <div class="form-group">
                <label>Nombre Completo</label>
                <input type="text" id="operator-name" placeholder="Ej: Juan Pérez">
            </div>
            <div class="form-group">
                <label>Turno</label>
                <select id="operator-shift">
                    <option value="Día">Día</option>
                    <option value="Tarde">Tarde</option>
                    <option value="Noche">Noche</option>
                </select>
            </div>
            <div class="form-group">
                <label>Estación de Trabajo</label>
                <select id="operator-station">
                    <option value="Soldadura">Soldadura</option>
                    <option value="Pulido">Pulido</option>
                    <option value="Presión">Presión</option>
                    <option value="Calidad">Calidad</option>
                    <option value="Pintura">Pintura</option>
                    <option value="Almacén">Almacén</option>
                </select>
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                <button class="btn btn-success" onclick="saveOperator()">Guardar</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    editOperators() {
        // Cargar operadores existentes para edición
        const state_data = this.lastLoadedData;
        const operators = state_data?.operadores || {};
        
        let operatorRows = '';
        Object.entries(operators).forEach(([id, operator]) => {
            operatorRows += `
                <div class="form-row" data-operator-id="${id}">
                    <input type="text" value="${operator.name}" placeholder="Nombre" class="operator-name-edit">
                    <select class="operator-shift-edit">
                        <option value="Día" ${operator.shift === 'Día' ? 'selected' : ''}>Día</option>
                        <option value="Tarde" ${operator.shift === 'Tarde' ? 'selected' : ''}>Tarde</option>
                        <option value="Noche" ${operator.shift === 'Noche' ? 'selected' : ''}>Noche</option>
                    </select>
                    <select class="operator-station-edit">
                        <option value="Soldadura" ${operator.station === 'Soldadura' ? 'selected' : ''}>Soldadura</option>
                        <option value="Pulido" ${operator.station === 'Pulido' ? 'selected' : ''}>Pulido</option>
                        <option value="Presión" ${operator.station === 'Presión' ? 'selected' : ''}>Presión</option>
                        <option value="Calidad" ${operator.station === 'Calidad' ? 'selected' : ''}>Calidad</option>
                        <option value="Pintura" ${operator.station === 'Pintura' ? 'selected' : ''}>Pintura</option>
                        <option value="Almacén" ${operator.station === 'Almacén' ? 'selected' : ''}>Almacén</option>
                    </select>
                    <button type="button" onclick="deleteOperatorRow('${id}')" class="btn btn-xs btn-error">🗑️</button>
                </div>
            `;
        });
        
        const modal = this.createModal('Editar Operadores', `
            <div class="operators-edit-container">
                ${operatorRows}
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                <button class="btn btn-success" onclick="saveAllOperators(this)">Guardar Cambios</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    async addStage() {
        const modal = this.createModal('Agregar Nueva Etapa', `
            <div class="form-group">
                <label>Nombre de la Etapa</label>
                <input type="text" id="stage-name" placeholder="Ej: Ensamble">
            </div>
            <div class="form-group">
                <label>Descripción</label>
                <input type="text" id="stage-description" placeholder="Descripción de la etapa">
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                <button class="btn btn-success" onclick="saveNewStage()">Agregar Etapa</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    async saveNewStage() {
        const stageName = document.getElementById('stage-name').value.trim();
        const stageDescription = document.getElementById('stage-description').value.trim();
        
        if (!stageName) {
            this.showNotification('El nombre de la etapa es requerido', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/data/stages', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: stageName,
                    description: stageDescription
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(result.message, 'success');
                // Cerrar modal
                const modal = document.querySelector('.modal');
                if (modal) modal.style.display = 'none';
                // Recargar datos para mostrar la nueva etapa
                this.loadData();
                this.updateStagesList();
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    async deleteStage(stageId) {
        if (stageId <= 6) {
            this.showNotification('No se pueden eliminar las etapas básicas del sistema', 'warning');
            return;
        }
        
        if (!confirm('¿Está seguro de eliminar esta etapa?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/data/stages/${stageId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(result.message, 'success');
                this.loadData();
                this.updateStagesList();
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    async editStage(stageId) {
        try {
            // Obtener datos actuales de la etapa
            const response = await fetch('/api/data/stages');
            if (!response.ok) {
                throw new Error('No se pudieron obtener los datos de las etapas');
            }
            
            const result = await response.json();
            const stages = result.stages || [];
            const stageToEdit = stages.find(stage => stage.id == stageId);
            
            if (!stageToEdit) {
                this.showNotification('Etapa no encontrada', 'error');
                return;
            }
            
            const isSystemStage = stageId <= 6;
            const editWarning = isSystemStage 
                ? '<p class="warning-text">⚠️ <strong>Advertencia:</strong> Esta es una etapa básica del sistema. Los cambios pueden afectar el flujo de producción.</p>'
                : '';
            
            const modal = this.createModal(`Editar Etapa: ${stageToEdit.name}`, `
                ${editWarning}
                <div class="form-group">
                    <label>Nombre de la Etapa</label>
                    <input type="text" id="edit-stage-name" value="${stageToEdit.name}" placeholder="Nombre de la etapa">
                </div>
                <div class="form-group">
                    <label>Descripción</label>
                    <input type="text" id="edit-stage-description" value="${stageToEdit.description || ''}" placeholder="Descripción de la etapa">
                </div>
                <div class="form-group">
                    <label>ID de la Etapa</label>
                    <input type="number" id="edit-stage-id" value="${stageToEdit.id}" readonly class="readonly-input">
                    <small>El ID de la etapa no se puede modificar</small>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                    <button class="btn btn-success" onclick="saveEditedStage(${stageId})">Guardar Cambios</button>
                </div>
            `);
            
            document.body.appendChild(modal);
            
        } catch (error) {
            this.showNotification('Error al cargar datos de la etapa: ' + error.message, 'error');
        }
    }
    
    async saveEditedStage(stageId) {
        const stageName = document.getElementById('edit-stage-name').value.trim();
        const stageDescription = document.getElementById('edit-stage-description').value.trim();
        
        if (!stageName) {
            this.showNotification('El nombre de la etapa es requerido', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/data/stages/${stageId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: stageName,
                    description: stageDescription
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(result.message, 'success');
                // Cerrar modal
                const modal = document.querySelector('.modal');
                if (modal) modal.style.display = 'none';
                
                // Recargar datos para mostrar los cambios
                this.loadData();
                this.updateStagesList();
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
            
        } catch (error) {
            this.showNotification('Error de conexión: ' + error.message, 'error');
        }
    }
    
    editStages() {
        const stages = [
            {id: 1, name: 'Soldadura', description: 'Proceso de soldadura'},
            {id: 2, name: 'Pulido', description: 'Acabado y pulido'},
            {id: 3, name: 'Presión', description: 'Pruebas de presión'},
            {id: 4, name: 'Calidad', description: 'Control de calidad'},
            {id: 5, name: 'Pintura', description: 'Acabado final'},
            {id: 6, name: 'Almacén', description: 'Almacenamiento'}
        ];
        
        let stageRows = '';
        stages.forEach(stage => {
            stageRows += `
                <div class="form-row" data-stage-id="${stage.id}">
                    <label>Etapa ${stage.id}:</label>
                    <input type="text" value="${stage.name}" placeholder="Nombre" class="stage-name-edit">
                    <input type="text" value="${stage.description}" placeholder="Descripción" class="stage-description-edit">
                </div>
            `;
        });
        
        const modal = this.createModal('Editar Etapas', `
            <div class="stages-edit-container">
                <p><strong>Nota:</strong> Las etapas son parte del flujo de producción estándar de Johnson Controls.</p>
                ${stageRows}
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cancelar</button>
                <button class="btn btn-success" onclick="saveAllStages(this)">Guardar Cambios</button>
            </div>
        `);
        document.body.appendChild(modal);
    }
    
    toggleManagement() {
        const content = document.getElementById('management-content');
        const toggleText = document.getElementById('management-toggle-text');
        const toggleIcon = document.getElementById('management-toggle-icon');
        
        if (!content) return;
        
        const isVisible = content.style.display !== 'none';
        
        if (isVisible) {
            content.style.display = 'none';
            if (toggleText) toggleText.textContent = 'Mostrar Gestión';
            if (toggleIcon) {
                toggleIcon.textContent = '▼';
                toggleIcon.classList.remove('expanded');
            }
        } else {
            content.style.display = 'block';
            if (toggleText) toggleText.textContent = 'Ocultar Gestión';
            if (toggleIcon) {
                toggleIcon.textContent = '▲';
                toggleIcon.classList.add('expanded');
            }
            
            // Cargar datos de operadores y etapas cuando se muestre
            this.loadData();
        }
    }
    
    // ===== FUNCIONES AUXILIARES =====
    
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-content">
                <h2>${title}</h2>
                ${content}
            </div>
        `;
        
        // Cerrar modal al hacer clic fuera
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
                setTimeout(() => modal.remove(), 300);
            }
        });
        
        return modal;
    }
    
    showExportModal(exportResult) {
        const data = exportResult.data || [];
        
        let tableRows = '';
        data.forEach(item => {
            tableRows += `
                <tr>
                    <td>${item.Codigo}</td>
                    <td>${item.Producto}</td>
                    <td>${item.Estado}</td>
                    <td>${item.Etapa_Actual}</td>
                    <td>${item['Progreso_%']}%</td>
                    <td>${item['Calidad_%']}%</td>
                </tr>
            `;
        });
        
        const modal = this.createModal('Reporte Excel Generado', `
            <div class="export-summary">
                <p><strong>Total de productos:</strong> ${exportResult.total_products}</p>
                <p><strong>Fecha de exportación:</strong> ${new Date(exportResult.export_timestamp).toLocaleString('es-MX')}</p>
            </div>
            
            <div class="export-preview">
                <h4>Vista previa de datos exportados:</h4>
                <table class="export-table">
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Producto</th>
                            <th>Estado</th>
                            <th>Etapa</th>
                            <th>Progreso</th>
                            <th>Calidad</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>
            
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="copyExportData()">Copiar Datos</button>
                <button class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">Cerrar</button>
            </div>
        `);
        
        document.body.appendChild(modal);
        
        // Almacenar datos para función de copia
        this.lastExportData = data;
    }
    
    updateCurrentShiftByTime() {
        const now = new Date();
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        const currentTime = currentHour * 100 + currentMinute; // Formato HHMM
        
        let currentShift = 'Día'; // Default
        
        // Día: 06:00 - 14:00 (600 - 1400)
        // Tarde: 14:00 - 22:00 (1400 - 2200)
        // Noche: 22:00 - 06:00 (2200 - 600)
        
        if (currentTime >= 600 && currentTime < 1400) {
            currentShift = 'Día';
        } else if (currentTime >= 1400 && currentTime < 2200) {
            currentShift = 'Tarde';
        } else {
            currentShift = 'Noche';
        }
        
        // Actualizar en el header
        this.updateElement('current-shift', currentShift);
        this.updateElement('current-shift-display', currentShift);
        
        // Actualizar visualmente si el turno cambió
        const lastShift = this.currentShift;
        if (lastShift && lastShift !== currentShift) {
            this.showNotification(`Turno cambiado automáticamente a: ${currentShift}`, 'info');
        }
        this.currentShift = currentShift;
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
    console.log('Función global toggleAnalytics() llamada');
    if (dashboard) {
        dashboard.toggleAnalytics();
    } else {
        console.error('Dashboard no está inicializado');
    }
}

function handleFileUpload(event) {
    if (dashboard) dashboard.handleFileUpload(event);
}

function showDataStructure() {
    if (dashboard) dashboard.showDataStructure();
}

function changeShift(shift) {
    if (dashboard) dashboard.changeShift(shift);
}

function editShiftSchedule() {
    if (dashboard) dashboard.editShiftSchedule();
}

function addOperator() {
    if (dashboard) dashboard.addOperator();
}

function editOperators() {
    if (dashboard) dashboard.editOperators();
}

function addStage() {
    if (dashboard) dashboard.addStage();
}

function editStages() {
    if (dashboard) dashboard.editStages();
}

function editStage(stageId) {
    if (dashboard) dashboard.editStage(stageId);
}

function saveNewStage() {
    if (dashboard) dashboard.saveNewStage();
}

function deleteStage(stageId) {
    if (dashboard) dashboard.deleteStage(stageId);
}

function saveEditedStage(stageId) {
    if (dashboard) dashboard.saveEditedStage(stageId);
}

function toggleManagement() {
    if (dashboard) dashboard.toggleManagement();
}

function copyExportData() {
    if (dashboard && dashboard.lastExportData) {
        const csvData = dashboard.lastExportData.map(item => 
            `${item.Codigo},${item.Producto},${item.Estado},${item.Etapa_Actual},${item['Progreso_%']},${item['Calidad_%']}`
        ).join('\n');
        
        const header = 'Código,Producto,Estado,Etapa,Progreso,Calidad\n';
        const fullData = header + csvData;
        
        navigator.clipboard.writeText(fullData).then(() => {
            dashboard.showNotification('Datos copiados al portapapeles', 'success');
        }).catch(() => {
            dashboard.showNotification('Error al copiar datos', 'error');
        });
    }
}

// Inicialización cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('Johnson Controls Dashboard v2.0 cargando...');
    
    // Pequeña demora para asegurar que todos los elementos estén listos
    setTimeout(() => {
        dashboard = new JCIDashboard();
    }, 500);
});