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
        
        // Şifre güncellenirken zorunlu değil
        document.getElementById('user-password').required = false;
        document.getElementById('password-help').style.display = 'block';
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Kullanıcı Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Ekle';
        
        form.reset();
        document.getElementById('update-user-id').value = '';
        
        // Yeni eklemede şifre zorunlu
        document.getElementById('user-password').required = true;
        document.getElementById('password-help').style.display = 'none';
    }
}