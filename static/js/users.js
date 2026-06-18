function openUserModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const name = btn.getAttribute('data-name');
    const email = btn.getAttribute('data-email');

    openUserModal(true, id, name, email);
}

function openUserModal(isUpdate = false, id = '', name = '', email = '') {
    document.getElementById('userFormModal').style.display = 'flex';
    const form = document.getElementById('user-form');
    
    if (isUpdate) {
        document.getElementById('modalTitle').innerText = 'Kullanıcıyı/Profili Düzenle';
        document.getElementById('modal-action').value = 'update';
        document.getElementById('modal-submit-btn').innerText = 'Güncelle';
        
        document.getElementById('update-user-id').value = id;
        document.getElementById('user-name').value = name;
        document.getElementById('user-email').value = email;
        
        // SADECE GÖRÜNÜMÜ AYARLIYORUZ (Eski required = false kodunu sildik)
        document.getElementById('password-help').style.display = 'block';
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Kullanıcı Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Ekle';
        
        form.reset();
        document.getElementById('update-user-id').value = '';
        
        // SADECE GÖRÜNÜMÜ AYARLIYORUZ (Eski required = true kodunu sildik)
        document.getElementById('password-help').style.display = 'none';
    }
}

// ==========================================
// 🛡️ KULLANICI FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const userForm = document.getElementById('user-form');
    
    if (userForm) {
        userForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const action = document.getElementById('modal-action').value;
            const name = document.getElementById('user-name').value.trim();
            const email = document.getElementById('user-email').value.trim();
            const password = document.getElementById('user-password').value.trim();

            // E-posta formatını kontrol eden Regex
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen ad ve soyad bilgisini girin.";
            } else if (!email || !emailRegex.test(email)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir e-posta adresi girin.";
            } else if (action === 'add' && !password) {
                // Sadece YENİ eklemede şifre zorunlu!
                hasError = true;
                errorMessage = "Yeni kullanıcı eklerken şifre belirlemek zorunludur.";
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