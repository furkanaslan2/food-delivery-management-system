function openFoodModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const name = btn.getAttribute('data-name');

    openFoodModal(true, id, name);
}

function openFoodModal(isUpdate = false, id = '', name = '') {
    document.getElementById('foodFormModal').style.display = 'flex';
    const form = document.getElementById('food-form');
    
    if (isUpdate) {
        document.getElementById('modalTitle').innerText = 'Kategoriyi Düzenle';
        document.getElementById('modal-action').value = 'update';
        document.getElementById('modal-submit-btn').innerText = 'Güncelle';
        
        document.getElementById('update-food-id').value = id;
        document.getElementById('food-id').value = id;
        document.getElementById('food-name').value = name;
    } else {
        document.getElementById('modalTitle').innerText = 'Yeni Kategori Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Ekle';
        
        form.reset();
        document.getElementById('update-food-id').value = '';
        document.getElementById('food-id').value = '';
    }
}