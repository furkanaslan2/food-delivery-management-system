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
        document.getElementById('waiter-email').setAttribute('data-old-email', email);
        
        document.getElementById('password-help').style.display = 'block';
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Garson Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        form.reset();
        document.getElementById('waiter-email').setAttribute('data-old-email', '');
        document.getElementById('update-waiter-id').value = '';
        document.getElementById('waiter-id').value = '';
        
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

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$/; 

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen garsonun adını ve soyadını girin.";
            } else if (!email || !emailRegex.test(email)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir e-posta adresi girin.";
            } else if (action === 'add' && !password) {
                hasError = true;
                errorMessage = "Yeni garson eklerken şifre belirlemek zorunludur.";
            } else if (password && !passwordRegex.test(password)) { 
                hasError = true;
                errorMessage = "Garson şifresi en az 8 karakter olmalı; en az 1 büyük harf, 1 küçük harf ve 1 rakam içermelidir.";
            }

            if (hasError) {
                e.preventDefault();
                if (typeof window.showToast === 'function') {
                    window.showToast(errorMessage, "error");
                } else {
                    alert(errorMessage);
                }
                return false;
            }
            
        });
    }
});

// ==========================================
// 🚀 GARSON E-POSTA CANLI KONTROL SİSTEMİ
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const emailInput = document.getElementById('waiter-email');
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
                body: JSON.stringify({ email: email, type: 'waiter', exclude_email: excludeEmail })
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