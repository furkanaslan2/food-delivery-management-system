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

// ==========================================
// 🛡️ RESTORAN FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const restaurantForm = document.getElementById('restaurant-form');
    
    if (restaurantForm) {
        restaurantForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const userIdInput = document.getElementById('user-id');
            const name = document.getElementById('restaurant-name-input').value.trim();
            const city = document.getElementById('restaurant-city').value.trim();
            const cuisine = document.getElementById('restaurant-cuisine').value;
            const tables = document.getElementById('restaurant-table-count').value.trim();
            const address = document.getElementById('restaurant-address').value.trim();

            // Admin ekranındaysa User ID kontrolü yap (Hidden değilse ekranda demektir)
            if (userIdInput && userIdInput.type !== "hidden") {
                const userId = userIdInput.value.trim();
                if (!userId || parseInt(userId) <= 0) {
                    hasError = true;
                    errorMessage = "Lütfen geçerli bir Kullanıcı ID (Sahibi) girin.";
                }
            }

            if (!hasError && !name) {
                hasError = true;
                errorMessage = "Lütfen restoranın adını girin.";
            } else if (!hasError && !city) {
                hasError = true;
                errorMessage = "Lütfen restoranın bulunduğu şehri girin.";
            } else if (!hasError && (!cuisine || cuisine === "")) {
                hasError = true;
                errorMessage = "Lütfen bir mutfak türü seçin.";
            } else if (!hasError && (!tables || parseInt(tables) < 1)) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir masa kapasitesi girin (en az 1 olmalıdır).";
            } else if (!hasError && !address) {
                hasError = true;
                errorMessage = "Lütfen restoranın tam adresini girin.";
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