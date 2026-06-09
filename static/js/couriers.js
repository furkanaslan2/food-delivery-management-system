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
        
        // Güncellemede şifre zorunlu değildir, boş bırakılabilir
        document.getElementById('courier-password').required = false;
        document.getElementById('password-help').style.display = 'block';
    } else {
        // --- YENİ EKLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Yeni Kurye Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        if (form) form.reset();
        document.getElementById('update-courier-id').value = '';
        document.getElementById('courier-id').value = '';
        
        // Yeni eklemede şifre zorunludur
        document.getElementById('courier-password').required = true;
        document.getElementById('password-help').style.display = 'none';
    }
}