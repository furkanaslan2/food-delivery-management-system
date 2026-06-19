// ==========================================
//  KURYE PANELİ & GPS TAKİP SİSTEMİ
// ==========================================

let currentFormId = null;

function confirmCourierAction(orderId, actionType) {
    currentFormId = 'status-form-' + orderId;
    const overlay = document.getElementById('courier-confirm-overlay');
    const title = document.getElementById('confirm-title');
    const desc = document.getElementById('confirm-desc');
    const icon = document.getElementById('confirm-icon');
    const yesBtn = document.getElementById('confirm-yes-btn');

    if (actionType === 'pickup') {
        icon.innerHTML = '<i class="ph-bold ph-moped" style="color: #3b82f6;"></i>';
        title.innerText = 'Yola Çıkıyorsunuz!';
        desc.innerText = 'Paketi restorandan eksiksiz bir şekilde teslim aldığınızı onaylıyor musunuz?';
        yesBtn.style.background = '#3b82f6'; 
    } else if (actionType === 'deliver') {
        icon.innerHTML = '<i class="ph-bold ph-check-circle" style="color: #10b981;"></i>';
        title.innerText = 'Teslimatı Tamamla';
        desc.innerText = 'Siparişi müşteriye sorunsuz teslim ettiğinizi (ve gerekiyorsa ödemeyi aldığınızı) onaylıyor musunuz?';
        yesBtn.style.background = '#10b981'; 
    }

    if (overlay) overlay.style.display = 'flex';
}

function closeCourierConfirm() {
    const overlay = document.getElementById('courier-confirm-overlay');
    if (overlay) overlay.style.display = 'none';
    currentFormId = null;
}

function toggleCourierStatus() {
    const btn = document.getElementById('status-toggle-btn');
    const isCurrentlyOnline = btn.classList.contains('online');
    const newStatus = !isCurrentlyOnline; 
    
    btn.innerHTML = '<i class="ph-bold ph-hourglass-high"></i> İşleniyor...';
    btn.style.opacity = '0.7';
    btn.style.pointerEvents = 'none';
    
    fetch('/api/toggle_courier_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_online: newStatus })
    })
    .then(res => res.json())
    .then(data => {
        btn.style.opacity = '1';
        btn.style.pointerEvents = 'auto';
        
        if(data.success) {
            if(data.is_online) {
                btn.className = 'status-toggle online';
                btn.innerHTML = '<div class="status-dot online"></div> Çevrimiçi';
            } else {
                btn.className = 'status-toggle offline';
                btn.innerHTML = '<div class="status-dot offline"></div> Molada';
            }
        } else {
            alert('Durum güncellenirken hata oluştu!');
            btn.innerHTML = isCurrentlyOnline ? '<div class="status-dot online"></div> Çevrimiçi' : '<div class="status-dot offline"></div> Molada';
        }
    })
    .catch(err => {
        btn.style.opacity = '1';
        btn.style.pointerEvents = 'auto';
        alert('Bağlantı hatası!');
        btn.innerHTML = isCurrentlyOnline ? '<div class="status-dot online"></div> Çevrimiçi' : '<div class="status-dot offline"></div> Molada';
    });
}

// ----------------------------------------------------
// 2. OTOMATİK SİSTEMLER (GPS & BİLDİRİM RADARI)
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    
    // Onay Butonu Event Listener'ı (HTML'den taşındı)
    const confirmYesBtn = document.getElementById('confirm-yes-btn');
    if (confirmYesBtn) {
        confirmYesBtn.addEventListener('click', function() {
            if (currentFormId) {
                this.innerHTML = 'İşleniyor... <i class="ph-bold ph-spinner ph-spin"></i>';
                this.style.opacity = '0.7';
                this.style.pointerEvents = 'none';
                document.getElementById(currentFormId).submit();
            }
        });
    }

    const gpsDataElement = document.getElementById('courier-gps-data');
    if (gpsDataElement) {
        const hasActiveDelivery = gpsDataElement.getAttribute('data-has-active-delivery') === 'true';

        if (hasActiveDelivery && navigator.geolocation) {
            const trackerBanner = document.getElementById('gps-tracker-banner');
            if(trackerBanner) trackerBanner.style.display = 'flex';

            navigator.geolocation.watchPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;

                    fetch('/api/update_courier_location', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ lat: lat, lon: lon })
                    }).catch(err => console.log("GPS Gönderim Hatası:", err));
                },
                (error) => {
                    console.error("Konum hatası:", error);
                    const statusText = document.getElementById('gps-status-text');
                    const banner = document.getElementById('gps-tracker-banner');
                    
                    if (banner) banner.style.backgroundColor = "#ef4444"; 
                    if (statusText) {
                        if (error.code === 1) statusText.innerHTML = "<i class='ph-bold ph-warning'></i> Lütfen Konum İzni Verin!";
                        else statusText.innerHTML = "<i class='ph-bold ph-warning'></i> Konum Sinyali Zayıf!";
                    }
                },
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 }
            );
        }
    }

    const orderElements = document.querySelectorAll('.order-card');
    let currentOrderCount = orderElements ? orderElements.length : 0;

    function checkCourierOrders() {
        const timestamp = new Date().getTime(); 
        
        fetch(`/api/check_courier_orders?order_count=${currentOrderCount}&t=${timestamp}`)
            .then(response => response.json())
            .then(data => {
                if (data.has_changes) {
                    const alertBox = document.getElementById('courier-alert');
                    if(alertBox) {
                        const alertText = document.getElementById('courier-alert-text');
                        if (alertText) alertText.innerHTML = data.message + ' <span style="font-size:12px; font-weight:500;">(Yenilemek için dokun)</span>';
                        alertBox.style.display = 'block';
                    }
                    
                    setTimeout(() => { window.location.reload(); }, 5000);
                    clearInterval(courierPolling); 
                }
            })
            .catch(err => console.error('Kurye API Hatası:', err));
    }

    const courierPolling = setInterval(checkCourierOrders, 7000);
});