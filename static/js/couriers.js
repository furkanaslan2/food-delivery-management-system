// ==========================================
// 🛵 KURYE YÖNETİMİ 
// ==========================================

// Butondaki data-* verilerini alıp modalı açan aracı fonksiyon
function openCourierModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const name = btn.getAttribute('data-name');
    const email = btn.getAttribute('data-email');
    const gender = btn.getAttribute('data-gender');
    const birth = btn.getAttribute('data-birth');

    // Asıl modal açma fonksiyonunu tetikle
    openCourierModal(true, id, name, email, gender, birth);
}

// Modal'ı Yeni Ekleme veya Güncelleme modunda açan ana fonksiyon
function openCourierModal(isUpdate = false, id = '', name = '', email = '', gender = '', birth = '') {
    const modal = document.getElementById('courierFormModal');
    if (!modal) return;
    
    modal.style.display = 'flex';
    const form = document.getElementById('courier-form');
    
    if (isUpdate) {
        // --- GÜNCELLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Kuryeyi Düzenle';
        document.getElementById('modal-action').value = 'update';
        document.getElementById('modal-submit-btn').innerText = 'Güncelle';
        
        document.getElementById('update-courier-id').value = id;
        document.getElementById('courier-id').value = id;
        document.getElementById('courier-name').value = name;
        document.getElementById('courier-email').value = email;
        document.getElementById('courier-gender').value = gender;
        document.getElementById('courier-birthdate').value = birth;
        
        document.getElementById('password-help').style.display = 'block';
    } else {
        // --- YENİ EKLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Yeni Kurye Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        if (form) form.reset();
        document.getElementById('update-courier-id').value = '';
        document.getElementById('courier-id').value = '';
        
        document.getElementById('password-help').style.display = 'none';
    }
}

// ==========================================
// 🛡️ KURYE FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const courierForm = document.getElementById('courier-form');
    
    if (courierForm) {
        courierForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const action = document.getElementById('modal-action').value;
            const name = document.getElementById('courier-name').value.trim();
            const email = document.getElementById('courier-email').value.trim();
            const password = document.getElementById('courier-password').value.trim();
            const gender = document.getElementById('courier-gender').value;
            const birthdate = document.getElementById('courier-birthdate').value;

            // E-posta formatını kontrol eden Regex (Örn: isim@domain.com)
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen kuryenin adını ve soyadını girin.";
            } else if (!email || !emailRegex.test(email)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir e-posta adresi girin.";
            } else if (action === 'add' && !password) {
                // Sadece YENİ eklemede şifre zorunlu!
                hasError = true;
                errorMessage = "Yeni kurye eklerken şifre belirlemek zorunludur.";
            } else if (password && password.length < 6) {
                // Şifre girilmişse (ekleme veya güncelleme fark etmez) en az 6 karakter olmalı
                hasError = true;
                errorMessage = "Güvenlik için şifre en az 6 karakter olmalıdır.";
            } else if (!gender) {
                hasError = true;
                errorMessage = "Lütfen cinsiyet seçimi yapın.";
            // Eski Doğum Tarihi Kontrolünü Şununla Değiştir:
            } else if (!birthdate) {
                hasError = true;
                errorMessage = "Lütfen kuryenin doğum tarihini girin.";
            } else {
                const birthYear = birthdate.split('-')[0];
                const currentYear = new Date().getFullYear();
                
                if (birthYear.length > 4 || parseInt(birthYear) < 1940) {
                    hasError = true;
                    errorMessage = "Lütfen geçerli 4 haneli bir doğum yılı girin.";
                } else if (parseInt(birthYear) > (currentYear - 18)) {
                    hasError = true;
                    errorMessage = "Güvenlik ve yasa gereği kurye en az 18 yaşında olmalıdır.";
                }
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