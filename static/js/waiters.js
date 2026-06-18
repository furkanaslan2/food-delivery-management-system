function openWaiterModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const restaurantId = btn.getAttribute('data-restaurantid');
    const name = btn.getAttribute('data-name');
    const email = btn.getAttribute('data-email');

    openWaiterModal(true, id, restaurantId, name, email);
}

function openWaiterModal(isUpdate = false, id = '', restaurantId = '', name = '', email = '') {
    document.getElementById('waiterFormModal').style.display = 'flex';
    const form = document.getElementById('waiter-form');
    
    if (isUpdate) {
        document.getElementById('modalTitle').innerText = 'Garsonu Düzenle';
        document.getElementById('modal-action').value = 'update';
        document.getElementById('modal-submit-btn').innerText = 'Güncelle';
        
        document.getElementById('update-waiter-id').value = id;
        document.getElementById('waiter-id').value = id;
        
        if (document.getElementById('waiter-restaurant-id')) {
            document.getElementById('waiter-restaurant-id').value = restaurantId;
        }
        
        document.getElementById('waiter-name').value = name;
        document.getElementById('waiter-email').value = email;
        
        // SADECE GÖRÜNÜMÜ AYARLIYORUZ (Eski required = false kodunu sildik)
        document.getElementById('password-help').style.display = 'block';
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Garson Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        form.reset();
        document.getElementById('update-waiter-id').value = '';
        document.getElementById('waiter-id').value = '';
        
        // SADECE GÖRÜNÜMÜ AYARLIYORUZ (Eski required = true kodunu sildik)
        document.getElementById('password-help').style.display = 'none';
    }
}

// ==========================================
// 🛡️ GARSON FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const waiterForm = document.getElementById('waiter-form');
    
    if (waiterForm) {
        waiterForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const action = document.getElementById('modal-action').value;
            const name = document.getElementById('waiter-name').value.trim();
            const email = document.getElementById('waiter-email').value.trim();
            const password = document.getElementById('waiter-password').value.trim();

            // E-posta formatını kontrol eden Regex (Örn: isim@domain.com)
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen garsonun adını ve soyadını girin.";
            } else if (!email || !emailRegex.test(email)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir e-posta adresi girin.";
            } else if (action === 'add' && !password) {
                // Sadece YENİ eklemede şifre zorunlu!
                hasError = true;
                errorMessage = "Yeni garson eklerken şifre belirlemek zorunludur.";
            } else if (password && password.length < 6) {
                // Şifre girilmişse (ekleme veya güncelleme fark etmez) en az 6 karakter olmalı
                hasError = true;
                errorMessage = "Güvenlik için şifre en az 6 karakter olmalıdır.";
            }

            // ❌ HATA VARSA: Formu durdur ve şık bildirim (Toast) göster
            if (hasError) {
                e.preventDefault();
                if (typeof window.showToast === 'function') {
                    window.showToast(errorMessage, "error");
                } else {
                    alert(errorMessage);
                }
                return false;
            }
            
            // ✅ HATA YOKSA: Form sorunsuzca Python'a gider
        });
    }
});