// ==========================================
// DÜKKAN DURUMU (AÇIK/KAPALI) KONTROLÜ
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const toggleBtn = document.getElementById('toggle-store-btn');
    
    // Eğer bu buton sayfada varsa (yani admin değil, restoran kullanıcısıysa) çalışsın
    if (toggleBtn) {
        // 1. Sayfa ilk açıldığında durumu kontrol et
        fetch('/api/toggle_store_status', { method: 'GET' })
        .then(res => res.json())
        .then(data => {
            if (data.success) { updateStoreUI(data.is_manually_closed); }
        });

        // 2. Butona tıklandığında durum değiştirme komutunu yolla
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
                    updateStoreUI(data.is_manually_closed);
                    if (typeof showToast === 'function') {
                        showToast(data.is_manually_closed ? "Dükkan sipariş alımına KAPATILDI!" : "Dükkan sipariş almaya AÇILDI!", data.is_manually_closed ? "warning" : "success");
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

// Arayüz (UI) boyama fonksiyonu
function updateStoreUI(isClosed) {
    const container = document.getElementById('status-container');
    const pulse = document.getElementById('status-pulse');
    const text = document.getElementById('status-text');
    const btn = document.getElementById('toggle-store-btn');
    const btnText = document.getElementById('toggle-btn-text');

    btn.style.display = 'flex';

    if (isClosed) {
        // KAPALIYSA: Kutuyu hafif kızart, ışığı kırmızı yap ve "AÇ" butonu koy
        container.style.borderLeftColor = '#ef4444';
        container.style.background = '#fef2f2';
        
        pulse.style.backgroundColor = '#ef4444';
        pulse.style.animation = 'pulse-red 2s infinite';
        
        text.innerHTML = '<span style="color:#dc2626; font-weight:800;">ŞU AN KAPALI</span> - Müşteriler sipariş veremez.';
        
        btn.style.background = '#10b981';
        btn.style.boxShadow = '0 4px 10px rgba(16, 185, 129, 0.3)';
        btnText.innerText = 'Dükkanı Siparişlere Aç';
    } else {
        // AÇIKSA: Kutuyu beyaz yap, ışığı yeşil yap ve "KAPAT" butonu koy
        container.style.borderLeftColor = '#10b981';
        container.style.background = 'white';
        
        pulse.style.backgroundColor = '#10b981';
        pulse.style.animation = 'pulse 2s infinite';
        
        text.innerHTML = '<span style="color:#059669; font-weight:800;">ŞU AN AÇIK</span> - Siparişler alınıyor.';
        
        btn.style.background = '#ef4444';
        btn.style.boxShadow = '0 4px 10px rgba(239, 68, 68, 0.3)';
        btnText.innerText = 'Acil Durum: Dükkanı Kapat';
    }
}