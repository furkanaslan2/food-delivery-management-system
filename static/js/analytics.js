// ==========================================
// 📊 İŞLETME ANALİZLERİ VE GRAFİKLER (Chart.js)
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    // 1. HTML İçindeki Gizli JSON Verisini Yakala
    const dataElement = document.getElementById('analytics-data');
    if (!dataElement) return;

    const rawData = dataElement.textContent;
    const db = JSON.parse(rawData);

    // 2. Modern Renk Paleti
    const primaryColor = 'rgba(79, 70, 229, 0.8)';   
    const successColor = 'rgba(16, 185, 129, 0.8)';  
    const warningColor = 'rgba(245, 158, 11, 0.8)';  
    const multiColors = [
        'rgba(99, 102, 241, 0.8)', 'rgba(236, 72, 153, 0.8)', 
        'rgba(16, 185, 129, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(139, 92, 246, 0.8)'
    ];

    // 📈 1. Çizgi Grafik: Son 7 Günlük Ciro
    const lineChartEl = document.getElementById('lineChart');
    if (lineChartEl) {
        new Chart(lineChartEl, {
            type: 'line',
            data: {
                labels: db.trend_labels,
                datasets: [{
                    label: 'Günlük Ciro (₺)',
                    data: db.trend_data,
                    borderColor: primaryColor,
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    }

    // 🍩 2. Doughnut Grafik: Paket vs Masa Oranı (Son 30 Gün)
    const doughnutChartEl = document.getElementById('doughnutChart');
    if (doughnutChartEl) {
        new Chart(doughnutChartEl, {
            type: 'doughnut',
            data: {
                labels: ['Paket Servis', 'Masaya Servis'],
                datasets: [{
                    data: [db.chart_delivery_count, db.chart_dinein_count],
                    backgroundColor: [successColor, warningColor],
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });
    }

    // 🔥 3. Dikey Bar Grafik: En Çok Satanlar (Son 30 Gün)
    const barChartEl = document.getElementById('barChart');
    if (barChartEl) {
        new Chart(barChartEl, {
            type: 'bar',
            data: {
                labels: db.top_item_labels,
                datasets: [{
                    label: 'Satılan Adet',
                    data: db.top_item_data,
                    backgroundColor: multiColors,
                    borderRadius: 6 
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    }

    // 🚀 4. Yatay Bar Grafik: Kurye Performansı (Son 30 Gün)
    const horizontalBarChartEl = document.getElementById('horizontalBarChart');
    if (horizontalBarChartEl) {
        new Chart(horizontalBarChartEl, {
            type: 'bar',
            data: {
                labels: db.courier_labels,
                datasets: [{
                    label: 'Teslim Edilen Paket',
                    data: db.courier_data,
                    backgroundColor: primaryColor,
                    borderRadius: 6
                }]
            },
            options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
        });
    }
});