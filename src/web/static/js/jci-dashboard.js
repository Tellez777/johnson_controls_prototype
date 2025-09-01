// src/web/static/js/jci-dashboard.js
let autoRefresh = true;
let refreshInterval = null;
let performanceChart = null;

// Configuración de colores JCI
const jciColors = {
    primary: '#0066CC',
    secondary: '#003D79',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444'
};

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    loadSystemInfo();
    startAutoRefresh();
});

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system/info');
        const info = await response.json();
        
        document.getElementById('plant-name').textContent = info.plant_name;
        document.getElementById('department').textContent = info.department;
        
    } catch (error) {
        console.error('Error cargando información del sistema:', error);
    }
}

async function refreshData() {
    try {
        // Simular datos para el prototipo
        updateKPIs();
        updateProducts();
        updateStatus();
        
        showNotification('Datos actualizados correctamente', 'success');
        
    } catch (error) {
        console.error('Error actualizando datos:', error);
        showNotification('Error actualizando datos', 'error');
    }
}

function updateKPIs() {
    // Simular KPIs realistas para Johnson Controls
    document.getElementById('oee-score').textContent = (85 + Math.random() * 10).toFixed(0) + '%';
    document.getElementById('efficiency-rate').textContent = (88 + Math.random() * 8).toFixed(0) + '%';
    document.getElementById('quality-score').textContent = (94 + Math.random() * 5).toFixed(0) + '%';
    document.getElementById('throughput').textContent = Math.floor(20 + Math.random() * 10);
}

function updateProducts() {
    const container = document.getElementById('products-container');
    const products = [
        {
            code: 'JCI240001A',
            name: 'Controlador HVAC Inteligente',
            partNumber: 'HVAC-CTL-2024-001',
            workOrder: 'WO-2024-0156',
            progress: 75,
            stage: 'Calidad',
            status: 'En Proceso'
        },
        {
            code: 'JCI240002B',
            name: 'Sistema de Gestión de Batería',
            partNumber: 'BATT-SYS-2024-002',
            workOrder: 'WO-2024-0157',
            progress: 100,
            stage: 'Completado',
            status: 'Completado'
        },
        {
            code: 'JCI240003C',
            name: 'Switch Inteligente Interior',
            partNumber: 'INT-SWT-2024-003',
            workOrder: 'WO-2024-0158',
            progress: 33,
            stage: 'Pulido',
            status: 'En Proceso'
        }
    ];
    
    container.innerHTML = products.map(product => `
        <div class="product-card">
            <div class="product-header">
                <div>
                    <div class="product-name">${product.name}</div>
                    <div class="product-code">${product.code}</div>
                </div>
                <div style="padding: 6px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600; background: ${product.status === 'Completado' ? '#10b981' : '#f59e0b'}; color: white;">
                    ${product.status}
                </div>
            </div>
            <div class="product-meta">
                <div><strong>P/N:</strong> ${product.partNumber}</div>
                <div><strong>WO:</strong> ${product.workOrder}</div>
                <div><strong>Etapa:</strong> ${product.stage}</div>
                <div><strong>Progreso:</strong> ${product.progress}%</div>
            </div>
        </div>
    `).join('');
}

function updateStatus() {
    document.getElementById('system-status-text').textContent = 'Operativo';
    document.getElementById('scanner-status-text').textContent = 'Conectado';
    document.getElementById('current-stage').textContent = 'Soldadura';
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

function initializeChart() {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00'],
            datasets: [{
                label: 'Eficiencia',
                data: [92, 89, 94, 91, 88, 93],
                borderColor: jciColors.primary,
                backgroundColor: jciColors.primary + '20',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#e6e8eb' }
                }
            },
            scales: {
                x: {
                    grid: { color: '#374151' },
                    ticks: { color: '#e6e8eb' }
                },
                y: {
                    grid: { color: '#374151' },
                    ticks: { color: '#e6e8eb' },
                    min: 80,
                    max: 100
                }
            }
        }
    });
}

async function simulateScan(productCode) {
    try {
        showNotification(`Simulando escaneo: ${productCode}`, 'warning');
        
        const response = await fetch('/api/control/simulate_scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode: productCode })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Escaneo simulado exitosamente', 'success');
            setTimeout(refreshData, 1000);
        } else {
            showNotification('Error en simulación: ' + result.message, 'error');
        }
        
    } catch (error) {
        showNotification('Error de conexión', 'error');
    }
}

async function changeStage(stageNumber) {
    try {
        const response = await fetch('/api/control/change_stage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stage: stageNumber })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Etapa cambiada a ${stageNumber}`, 'success');
            refreshData();
        } else {
            showNotification('Error cambiando etapa', 'error');
        }
        
    } catch (error) {
        showNotification('Error de conexión', 'error');
    }
}

function exportReport() {
    showNotification('Funcionalidad de exportación en desarrollo', 'warning');
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 4000);
}

function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (autoRefresh) {
            refreshData();
        }
    }, 5000);
}

// Controles de teclado
document.addEventListener('keydown', (e) => {
    if (e.target.tagName.toLowerCase() === 'input') return;
    
    switch(e.key) {
        case '1': simulateScan('JCI240001A'); break;
        case '2': simulateScan('JCI240002B'); break;
        case '3': simulateScan('JCI240003C'); break;
        case 'r': case 'R': refreshData(); break;
    }
});

// Inicialización
refreshData();