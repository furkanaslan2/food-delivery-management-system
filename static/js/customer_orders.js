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

// ==========================================
    // İNTERAKTİF YILDIZ DEĞERLENDİRME SİSTEMİ
    // ==========================================
    document.querySelectorAll('.star-rating-container').forEach(container => {
        const stars = container.querySelectorAll('.star-btn');
        const orderId = container.getAttribute('data-order-id');
        const hiddenInput = document.getElementById(`rating-input-${orderId}`);
        const textDisplay = document.getElementById(`rating-text-${orderId}`);

        const ratingTexts = ["Berbat", "Kötü", "Ortalama", "Çok İyi", "Mükemmel!"];

        stars.forEach((star, index) => {
            // Fareyle üzerine gelindiğinde
            star.addEventListener('mouseover', () => {
                stars.forEach((s, i) => {
                    s.style.color = i <= index ? '#f59e0b' : '#e5e7eb';
                    s.style.transform = i <= index ? 'scale(1.15)' : 'scale(1)';
                });
                textDisplay.innerText = ratingTexts[index];
                textDisplay.style.color = '#f59e0b';
            });

            // Fare çekildiğinde (Seçili olana geri dön)
            star.addEventListener('mouseout', () => {
                const currentVal = hiddenInput.value;
                stars.forEach((s, i) => {
                    s.style.color = i < currentVal ? '#f59e0b' : '#e5e7eb';
                    s.style.transform = 'scale(1)';
                });
                
                if(currentVal) {
                    textDisplay.innerText = ratingTexts[currentVal - 1];
                    textDisplay.style.color = '#111827';
                } else {
                    textDisplay.innerText = "Lütfen puanınızı seçin";
                    textDisplay.style.color = '#9ca3af';
                }
            });

            // Tıklanarak seçildiğinde
            star.addEventListener('click', () => {
                hiddenInput.value = index + 1;
                // Şık bir zıplama animasyonu
                star.style.transform = 'scale(1.3)';
                setTimeout(() => { star.style.transform = 'scale(1)'; }, 150);
            });
        });
    });

    // ==========================================
    // 🛡️ YORUM GÖNDERME MASTER KONTROL (AKILLI DOĞRULAMA)
    // ==========================================
    document.addEventListener('submit', function(e) {
        // Eğer gönderilen form bir "review-form" (değerlendirme formu) ise
        if (e.target && e.target.classList.contains('review-form')) {
            const form = e.target;
            const orderId = form.querySelector('input[name="order_id"]').value;
            const ratingInput = document.getElementById(`rating-input-${orderId}`);
            
            // Puan (Yıldız) seçilmemişse
            if (!ratingInput || !ratingInput.value) {
                e.preventDefault(); // Formu durdur (Sayfa yenilenmez, yazılan yorum silinmez)
                
                if (typeof window.showToast === 'function') {
                    window.showToast("Lütfen değerlendirmeyi göndermeden önce yıldızlara tıklayarak bir puan seçin.", "error");
                } else {
                    alert("Lütfen bir puan seçin.");
                }
            }
            // Hata yoksa form normal şekilde Python'a gider
        }
    });