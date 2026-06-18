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
        document.getElementById('courier-email').setAttribute('data-old-email', email); 
        document.getElementById('courier-gender').value = gender;
        document.getElementById('courier-birthdate').value = birth;

        
        document.getElementById('password-help').style.display = 'block';
    } else {
        // --- YENİ EKLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Yeni Kurye Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        if (form) form.reset();
        document.getElementById('courier-email').setAttribute('data-old-email', '');
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

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$/; 

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen kuryenin adını ve soyadını girin.";
            } else if (!email || !emailRegex.test(email)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir e-posta adresi girin.";
            } else if (action === 'add' && !password) {
                hasError = true;
                errorMessage = "Yeni kurye eklerken şifre belirlemek zorunludur.";
            } else if (password && !passwordRegex.test(password)) { 
                hasError = true;
                errorMessage = "Kurye şifresi en az 8 karakter olmalı; en az 1 büyük harf, 1 küçük harf ve 1 rakam içermelidir.";
            } else if (!gender) {
                hasError = true;
                errorMessage = "Lütfen cinsiyet seçimi yapın.";
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

// ==========================================
// 🚀 KURYE E-POSTA CANLI KONTROL SİSTEMİ
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const emailInput = document.getElementById('courier-email');
    if (!emailInput) return;

    const emailWarning = document.createElement('span');
    emailWarning.style.fontSize = '12px';
    emailWarning.style.fontWeight = '600';
    emailWarning.style.marginTop = '5px';
    emailWarning.style.display = 'block';
    emailInput.parentNode.insertBefore(emailWarning, emailInput.nextSibling);

    emailInput.addEventListener('blur', function() {
        const email = this.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const excludeEmail = emailInput.getAttribute('data-old-email') || '';

        if (email && emailRegex.test(email)) {
            if (email === excludeEmail) {
                emailInput.style.borderColor = '#10b981';
                emailWarning.innerText = 'Mevcut e-posta değişmedi. ✅';
                emailWarning.style.color = '#10b981';
                return;
            }

            fetch('/api/check_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, type: 'courier', exclude_email: excludeEmail })
            })
            .then(res => res.json())
            .then(data => {
                if (data.available === false) {
                    emailInput.style.borderColor = '#ef4444';
                    emailWarning.innerText = 'Bu e-posta başka bir hesap tarafından kullanılıyor! ❌';
                    emailWarning.style.color = '#ef4444';
                } else {
                    emailInput.style.borderColor = '#10b981';
                    emailWarning.innerText = 'Bu e-posta kullanılabilir. ✅';
                    emailWarning.style.color = '#10b981';
                }
            }).catch(err => console.log('Mail kontrol hatası:', err));
        } else {
            emailInput.style.borderColor = '';
            emailWarning.innerText = '';
        }
    });
});