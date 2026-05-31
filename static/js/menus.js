document.addEventListener("DOMContentLoaded", function() {
    // 📷 FOTOĞRAF SEÇİLDİĞİNDE CANLI ÖNİZLEME YAPMA
    const fileInput = document.querySelector('input[name="menu_image"]');
    if(fileInput) {
        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewBox = document.getElementById('menu-image-preview');
                    if(previewBox) {
                        previewBox.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">`;
                    }
                }
                reader.readAsDataURL(file);
            }
        });
    }
});

// ➕ YENİ YEMEK EKLEME MODALI
function openMenuModal() {
    document.getElementById('menuFormModal').style.display = 'flex';
    document.getElementById('menuModalTitle').innerText = 'Yeni Yemek Ekle';
    document.getElementById('modal-add-btn').style.display = 'block';
    document.getElementById('modal-update-btn').style.display = 'none';

    // Formu temizle
    document.getElementById('menu-form').reset();
    
    const updateId = document.getElementById('update-menu-id');
    if(updateId) updateId.value = '';
    
    const menuId = document.getElementById('menu-id');
    if(menuId) menuId.value = '';

    // Görseli sıfırla
    const previewBox = document.getElementById('menu-image-preview');
    if(previewBox) previewBox.innerHTML = '<span style="color: #9ca3af; font-size: 30px;">🍲</span>';
}

// ✏️ MENÜ DÜZENLEME MODALI (Hatasız Veri Doldurma)
function openMenuModalFromBtn(btn) {
    document.getElementById('menuFormModal').style.display = 'flex';
    document.getElementById('menuModalTitle').innerText = 'Menüyü Düzenle';
    document.getElementById('modal-add-btn').style.display = 'none';
    document.getElementById('modal-update-btn').style.display = 'block';

    // 🛡️ Korumalı Veri Doldurma (Eğer HTML'de o kutu yoksa kod çökmez, atlar)
    const updateMenuId = document.getElementById('update-menu-id');
    if(updateMenuId) updateMenuId.value = btn.getAttribute('data-id');

    const menuId = document.getElementById('menu-id');
    if(menuId) menuId.value = btn.getAttribute('data-id'); 

    const foodName = document.getElementById('food-name');
    if(foodName) foodName.value = btn.getAttribute('data-food-id');

    const customName = document.getElementById('menu-custom-name');
    if(customName) customName.value = btn.getAttribute('data-custom-name');

    const menuPrice = document.getElementById('menu-price');
    if(menuPrice) menuPrice.value = btn.getAttribute('data-price');

    const menuStock = document.getElementById('menu-stock');
    if(menuStock) menuStock.value = btn.getAttribute('data-stock');

    // Mevcut resmi önizleme kutusuna ekle
    const imageUrl = btn.getAttribute('data-image');
    const previewBox = document.getElementById('menu-image-preview');
    if(previewBox) {
        if (imageUrl && imageUrl !== 'None' && imageUrl !== '') {
            previewBox.innerHTML = `<img src="/static/images/menus/${imageUrl}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">`;
        } else {
            previewBox.innerHTML = '<span style="color: #9ca3af; font-size: 30px;">🍲</span>';
        }
    }
}

// ❌ MODALI KAPAT
function closeMenuModal() {
    document.getElementById('menuFormModal').style.display = 'none';
}

// ==========================================
// 🎟️ KUPON VE PROMOSYON İŞLEMLERİ 
// ==========================================

function openPromoModal() {
    document.getElementById('promoModal').style.display = 'flex';
    loadPromos();
}

function closePromoModal() {
    document.getElementById('promoModal').style.display = 'none';
}

function loadPromos() {
    fetch('/api/manage_promos')
    .then(res => res.json())
    .then(data => {
        const tbody = document.getElementById('promo-table-body');
        if(!tbody) return;
        
        tbody.innerHTML = '';
        if(data.promos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Aktif kupon yok.</td></tr>';
            return;
        }
        data.promos.forEach(p => {
            const tr = document.createElement('tr');
            const valStr = p.discount_type === 'percentage' ? `%${p.discount_value}` : `$${p.discount_value}`;
            tr.innerHTML = `
                <td><strong>${p.code_name}</strong></td>
                <td><span style="background:#dcfce3; color:#16a34a; padding:2px 6px; border-radius:4px; font-weight:bold;">${valStr}</span></td>
                <td>$${p.min_cart_amount}</td>
                <td>
                    <label style="display:flex; align-items:center; cursor:pointer;">
                        <input type="checkbox" ${p.is_active ? 'checked' : ''} onchange="togglePromo(${p.promo_id})" style="margin-right:5px;">
                        ${p.is_active ? 'Aktif' : 'Pasif'}
                    </label>
                </td>
                <td><button onclick="deletePromo(${p.promo_id})" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:16px;">🗑️</button></td>
            `;
            tbody.appendChild(tr);
        });
    });
}

function addPromo() {
    const code = document.getElementById('new-promo-code').value.trim().toUpperCase();
    const type = document.getElementById('new-promo-type').value;
    const val = document.getElementById('new-promo-val').value;
    const min = document.getElementById('new-promo-min').value;

    if(!code || !val) return alert("Kod ve İndirim tutarı boş olamaz!");

    fetch('/api/manage_promos', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'add', code_name: code, discount_type: type, discount_value: val, min_cart_amount: min || 0})
    }).then(res => res.json()).then(data => {
        if(data.success) {
            document.getElementById('new-promo-code').value = '';
            document.getElementById('new-promo-val').value = '';
            document.getElementById('new-promo-min').value = '';
            loadPromos();
        } else alert(data.message);
    });
}

function deletePromo(id) {
    if(!confirm("Kuponu silmek istediğinize emin misiniz?")) return;
    fetch('/api/manage_promos', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'delete', promo_id: id})
    }).then(res => res.json()).then(data => { if(data.success) loadPromos(); });
}

function togglePromo(id) {
    fetch('/api/manage_promos', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'toggle', promo_id: id})
    }).then(res => res.json()).then(data => { if(data.success) loadPromos(); });
}