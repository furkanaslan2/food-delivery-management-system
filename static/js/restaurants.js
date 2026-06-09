// ==========================================
// 🏪 RESTORAN YÖNETİMİ
// ==========================================

// Butondaki data-* verilerini alıp modalı açan aracı fonksiyon
function openRestaurantModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const userid = btn.getAttribute('data-userid');
    const name = btn.getAttribute('data-name');
    const city = btn.getAttribute('data-city');
    const address = btn.getAttribute('data-address');
    const cuisine = btn.getAttribute('data-cuisine');
    const tables = btn.getAttribute('data-tables');

    // Asıl modal açma fonksiyonunu tetikle
    openRestaurantModal(true, id, userid, name, city, address, cuisine, tables);
}

// Modal'ı Yeni Ekleme veya Güncelleme modunda açan ana fonksiyon
function openRestaurantModal(isUpdate = false, id = '', userid = '', name = '', city = '', address = '', cuisine = '', tables = '') {
    const modal = document.getElementById('restaurantFormModal');
    if (!modal) return;
    
    // Modalı görünür yap
    modal.style.display = 'flex';
    const form = document.getElementById('restaurant-form');
    
    if (isUpdate) {
        // --- GÜNCELLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Restoranı Düzenle';
        document.getElementById('modal-action').value = 'update';
        document.getElementById('modal-submit-btn').innerText = 'Güncelle';
        
        // ID'leri doldur
        document.getElementById('update-restaurant-id').value = id;
        document.getElementById('restaurant-id').value = id;
        
        // Admin için kullanıcı ID alanını doldur
        if (document.getElementById('user-id')) {
            document.getElementById('user-id').value = userid;
        }
        
        // Form alanlarını doldur
        document.getElementById('restaurant-name-input').value = name;
        document.getElementById('restaurant-city').value = city;
        document.getElementById('restaurant-address').value = address;
        document.getElementById('restaurant-cuisine').value = cuisine;
        document.getElementById('restaurant-table-count').value = tables;
    } else {
        // --- YENİ EKLEME MODU ---
        document.getElementById('modalTitle').innerText = 'Yeni Restoran Ekle';
        document.getElementById('modal-action').value = 'add';
        document.getElementById('modal-submit-btn').innerText = 'Kaydet';
        
        // Formu temizle
        if (form) form.reset();
        document.getElementById('update-restaurant-id').value = '';
        document.getElementById('restaurant-id').value = '';
    }
}