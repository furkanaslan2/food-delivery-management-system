// ==========================================
// 🛵 KURYE PANELİ & GPS TAKİP SİSTEMİ
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    
    // ----------------------------------------------------
    // 1. GPS TAKİP MOTORU (CANLI KONUM AKTARIMI)
    // ----------------------------------------------------
    const gpsDataElement = document.getElementById('courier-gps-data');
    if (gpsDataElement) {
        const hasActiveDelivery = gpsDataElement.getAttribute('data-has-active-delivery') === 'true';

        // Eğer kurye yoldaysa, telefonun GPS'ini takip etmeye başla
        if (hasActiveDelivery && navigator.geolocation) {
            const trackerBanner = document.getElementById('gps-tracker-banner');
            if(trackerBanner) trackerBanner.style.display = 'flex';

            navigator.geolocation.watchPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;

                    // Her konum değiştiğinde arka plandaki Python API'ye fırlat
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
                        if (error.code === 1) statusText.innerText = "⚠️ Lütfen Tarayıcıdan Konum İzni Verin!";
                        else statusText.innerText = "⚠️ Konum Sinyali Zayıf!";
                    }
                },
                // Yüksek doğruluk (Gerçek GPS) kullanmasını istiyoruz
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 }
            );
        }
    }

    // ----------------------------------------------------
    // 2. YENİ PAKET RADARI (OTOMATİK YENİLEME)
    // ----------------------------------------------------
    const orderElements = document.querySelectorAll('.order-card');
    let currentOrderCount = orderElements ? orderElements.length : 0;

    function checkCourierOrders() {
        const timestamp = new Date().getTime(); // Cache engelleme
        
        fetch(`/api/check_courier_orders?order_count=${currentOrderCount}&t=${timestamp}`)
            .then(response => response.json())
            .then(data => {
                if (data.has_changes) {
                    const alertBox = document.getElementById('courier-alert');
                    if(alertBox) {
                        const alertText = document.getElementById('courier-alert-text');
                        if (alertText) alertText.innerText = data.message + ' (Yenilemek için dokun)';
                        alertBox.style.display = 'block';
                    }
                    
                    // 5 saniye sonra ekranı kendi kendine yenile
                    setTimeout(() => { window.location.reload(); }, 5000);
                    clearInterval(courierPolling); 
                }
            })
            .catch(err => console.error('Kurye API Hatası:', err));
    }

    // Her 7 saniyede bir sessizce tekrarla
    const courierPolling = setInterval(checkCourierOrders, 7000);
});