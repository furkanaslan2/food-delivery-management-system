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
        
        // Güncellemede şifre zorunlu değil
        document.getElementById('waiter-password').required = false;
        document.getElementById('password-help').style.display = 'block';
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Garson Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        form.reset();
        document.getElementById('update-waiter-id').value = '';
        document.getElementById('waiter-id').value = '';
        
        // Yeni eklemede şifre zorunlu
        document.getElementById('waiter-password').required = true;
        document.getElementById('password-help').style.display = 'none';
    }
}