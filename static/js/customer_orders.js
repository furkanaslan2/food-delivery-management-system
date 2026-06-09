// ==========================================
// 📦 SİPARİŞLERİM & CANLI TAKİP MOTORU
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    const confirmModal = document.getElementById('cancelConfirmModal');
    const btnYes = document.getElementById('btn-cancel-yes');
    const btnNo = document.getElementById('btn-cancel-no');

    const alertModal = document.getElementById('customAlertModal');
    const alertTitle = document.getElementById('customAlertTitle');
    const alertMessage = document.getElementById('customAlertMessage');
    const alertIcon = document.getElementById('customAlertIcon');
    const btnAlertOk = document.getElementById('btn-alert-ok');

    let currentOrderIdToCancel = null;

    function showCustomAlert(title, message, isSuccess, reloadOnClose = false) {
        alertTitle.innerText = title;
        alertMessage.innerText = message;
        
        // 🌟 PHOSPHOR İKONLARINA GEÇİŞ YAPILDI
        if (isSuccess === true) {
            alertIcon.innerHTML = '<i class="ph-fill ph-check-circle" style="color:#10b981;"></i>';
        } else if (isSuccess === 'info') {
            alertIcon.innerHTML = '<i class="ph-fill ph-moped" style="color:#3b82f6;"></i>';
        } else {
            alertIcon.innerHTML = '<i class="ph-fill ph-x-circle" style="color:#ef4444;"></i>';
        }

        alertModal.style.display = 'flex';
        
        btnAlertOk.onclick = function() {
            alertModal.style.display = 'none';
            if(reloadOnClose) window.location.reload();
        };
    }

    // --- 📍 DİNAMİK BUTON DİNLEYİCİLERİ ---
    document.addEventListener('click', function(e) {
        const cancelBtn = e.target.closest('.cancel-order-btn');
        if (cancelBtn) {
            e.preventDefault();
            currentOrderIdToCancel = cancelBtn.getAttribute('data-id');
            confirmModal.style.display = 'flex'; 
        }

        const reorderBtn = e.target.closest('.reorder-btn');
        if (reorderBtn) {
            e.preventDefault();
            const orderIdToReorder = reorderBtn.getAttribute('data-id');

            fetch('/api/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({ order_id: orderIdToReorder })
            })
            .then(res => res.json())
            .then(data => {
                // NOT: Harici JS dosyası olduğu için {{ url_for('view_cart') }} yerine düz '/cart' rotasını kullanıyoruz
                if (data.success) window.location.href = "/cart"; 
                else showCustomAlert("Hata", data.message, false);
            })
            .catch(error => showCustomAlert("Bağlantı Hatası", "Bir sorun oluştu.", false));
        }
    });

    btnNo.addEventListener('click', function() { confirmModal.style.display = 'none'; currentOrderIdToCancel = null; });

    btnYes.addEventListener('click', function() {
        confirmModal.style.display = 'none'; 
        if (!currentOrderIdToCancel) return;

        fetch('/api/cancel_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ order_id: currentOrderIdToCancel })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) showCustomAlert("Başarılı!", data.message, true, true);
            else showCustomAlert("İptal Edilemedi", data.message, false, false);
        })
        .catch(error => showCustomAlert("Bağlantı Hatası", "Lütfen tekrar deneyin.", false, false));
    });

    // --- 🚀 CANLI SİPARİŞ TAKİP MOTORU ---
    setInterval(() => {
        fetch(window.location.href, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const newDoc = parser.parseFromString(html, 'text/html');
            const newCards = newDoc.querySelectorAll('.order-card');
            
            newCards.forEach(newCard => {
                const orderId = newCard.getAttribute('data-order-id');
                const newStatus = newCard.getAttribute('data-status');
                const currentCard = document.querySelector(`.order-card[data-order-id="${orderId}"]`);
                
                if (currentCard && currentCard.getAttribute('data-status') !== newStatus) {
                    currentCard.innerHTML = newCard.innerHTML;
                    currentCard.setAttribute('data-status', newStatus);
                    
                    currentCard.style.transition = 'box-shadow 0.4s ease';
                    currentCard.style.boxShadow = '0 0 25px rgba(16, 185, 129, 0.6)';
                    setTimeout(() => { currentCard.style.boxShadow = '0 4px 15px rgba(0,0,0,0.02)'; }, 2000);
                    
                    if(newStatus === 'preparing') showCustomAlert("Harika Haber!", "#" + orderId + " numaralı siparişiniz hazırlanmaya başlandı!", true);
                    else if(newStatus === 'on_the_way') showCustomAlert("Yolda!", "#" + orderId + " numaralı siparişiniz yola çıktı!", 'info');
                    else if(newStatus === 'delivered') showCustomAlert("Teslim Edildi!", "#" + orderId + " numaralı siparişiniz teslim edildi. Afiyet olsun!", true);
                    else if(newStatus === 'canceled') showCustomAlert("İptal Edildi", "#" + orderId + " numaralı siparişiniz iptal edildi.", false);
                }
            });
        })
        .catch(err => console.log('Oto-güncelleme hatası:', err));
    }, 5000); 
});