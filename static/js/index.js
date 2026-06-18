// ==========================================
// 🚀 DÜKKAN DURUMU (AKILLI RADAR KONTROLÜ)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const toggleBtn = document.getElementById('toggle-store-btn');
    
    if (toggleBtn) {
        // 1. Sayfa yüklendiğinde durumu kontrol et
        fetch('/api/toggle_store_status', { method: 'GET' })
        .then(res => res.json())
        .then(data => {
            if (data.success) { updateStoreUI(data.status); }
        });

        // 2. Butona tıklandığında aksiyon al
        toggleBtn.addEventListener('click', function() {
            toggleBtn.style.opacity = '0.7';
            toggleBtn.style.pointerEvents = 'none';

            fetch('/api/toggle_store_status', { 
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateStoreUI(data.status);
                    if (typeof showToast === 'function') {
                        showToast(data.status === 'manually_closed' ? "Frene Basıldı: Dükkan sipariş alımına KAPATILDI!" : "Dükkan sipariş almaya AÇILDI!", data.status === 'manually_closed' ? "warning" : "success");
                    }
                } else {
                    // 🛑 MESAİ DIŞI ENGELİ!
                    if (typeof window.showToast === 'function') {
                        window.showToast(data.message, "error");
                    } else {
                        alert(data.message);
                    }
                }
            })
            .finally(() => {
                toggleBtn.style.opacity = '1';
                toggleBtn.style.pointerEvents = 'auto';
            });
        });
    }
});

// Arayüz (UI) 3 Durumlu Boyama Fonksiyonu
function updateStoreUI(status) {
    const container = document.getElementById('status-container');
    const pulse = document.getElementById('status-pulse');
    const text = document.getElementById('status-text');
    const btn = document.getElementById('toggle-store-btn');
    const btnText = document.getElementById('toggle-btn-text');

    btn.style.display = 'flex';

    if (status === 'out_of_hours') {
        // 1. MESAİ DIŞI: Kutuyu gri yap, pasif hissiyatı ver
        container.style.borderLeftColor = '#6b7280';
        container.style.background = '#f9fafb';
        pulse.style.backgroundColor = '#6b7280';
        pulse.style.animation = 'none';
        
        text.innerHTML = '<span style="color:#4b5563; font-weight:800;">MESAİ SAATLERİ DIŞINDA</span> - Restoranınız şu an kapalı.';
        
        btn.style.background = '#9ca3af';
        btn.style.boxShadow = 'none';
        btnText.innerText = 'Çalışma Saatleri Dışında';
        
    } else if (status === 'manually_closed') {
        // 2. FREN (MOLA) MODU: Turuncu renk ile geçici duraklama hissiyatı ver
        container.style.borderLeftColor = '#f59e0b';
        container.style.background = '#fffbeb';
        pulse.style.backgroundColor = '#f59e0b';
        pulse.style.animation = 'pulse-red 2s infinite'; // Mevcut animasyon class'ını kullanabiliriz
        
        text.innerHTML = '<span style="color:#d97706; font-weight:800;">MOLA (FREN) MODU</span> - Geçici olarak sipariş alınmıyor.';
        
        btn.style.background = '#10b981';
        btn.style.boxShadow = '0 4px 10px rgba(16, 185, 129, 0.3)';
        btnText.innerText = 'Molayı Bitir: Siparişlere Aç';
        
    } else if (status === 'open') {
        // 3. AÇIK: Yeşil renk ile aktif çalışma
        container.style.borderLeftColor = '#10b981';
        container.style.background = 'white';
        pulse.style.backgroundColor = '#10b981';
        pulse.style.animation = 'pulse 2s infinite';
        
        text.innerHTML = '<span style="color:#059669; font-weight:800;">ŞU AN AÇIK</span> - Siparişler alınıyor.';
        
        btn.style.background = '#ef4444';
        btn.style.boxShadow = '0 4px 10px rgba(239, 68, 68, 0.3)';
        btnText.innerText = 'Yoğunluk: Frene Bas (Kapat)';
    }
}