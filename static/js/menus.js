document.addEventListener("DOMContentLoaded", function() {
    // 📷 FOTOĞRAF YÜKLEME, GÜVENLİK KONTROLÜ VE CANLI ÖNİZLEME
    const fileInput = document.querySelector('input[name="menu_image"]');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (!file) return;

            const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
            if (!validTypes.includes(file.type)) {
                if (typeof window.showToast === 'function') window.showToast("Sadece JPG, PNG veya WEBP yükleyebilirsiniz.", "error");
                else alert("Sadece JPG, PNG veya WEBP formatında resim yükleyebilirsiniz.");
                this.value = ''; 
                return;
            }

            const maxSizeInBytes = 3 * 1024 * 1024; 
            if (file.size > maxSizeInBytes) {
                if (typeof window.showToast === 'function') window.showToast("Yemek fotoğrafı 3 MB'dan küçük olmalıdır. Lütfen görseli küçültüp tekrar deneyin.", "error");
                else alert("Yemek fotoğrafı 3 MB'dan küçük olmalıdır. Lütfen görseli küçültüp tekrar deneyin.");
                this.value = ''; 
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                const previewBox = document.getElementById('menu-image-preview');
                if (previewBox) {
                    previewBox.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px; animation: fadeIn 0.3s ease;">`;
                }
            }
            reader.readAsDataURL(file);
        });
    }
});

// 🛠️ DİNAMİK SEÇENEK YÖNETİMİ DEĞİŞKENLERİ
let optionGroupIndex = 0;

// ➕ YENİ YEMEK EKLEME MODALI
function openMenuModal() {
    document.getElementById('menuFormModal').style.display = 'flex';
    document.getElementById('menuModalTitle').innerText = 'Yeni Yemek Ekle';
    document.getElementById('modal-add-btn').style.display = 'block';
    document.getElementById('modal-update-btn').style.display = 'none';

    // Formu temizle
    document.getElementById('menu-form').reset();
    
    const menuIdInput = document.getElementById('menu-id');
    const updateMenuIdInput = document.getElementById('update-menu-id');
    if (menuIdInput) menuIdInput.value = '';
    if (updateMenuIdInput) updateMenuIdInput.value = '';

    // Görsel önizlemeyi sıfırla
    const previewBox = document.getElementById('menu-image-preview');
    if(previewBox) {
        previewBox.innerHTML = '<i class="ph-fill ph-cooking-pot" style="color: #9ca3af; font-size: 32px;"></i>';
    }

    // 🛠️ Opsiyon ekleme alanını göster ve formdaki eski kalıntıları temizle
    const optionsContainer = document.getElementById('options-container');
    if(optionsContainer) optionsContainer.innerHTML = '';
    optionGroupIndex = 0;
    const optionsSection = document.getElementById('options-section');
    if(optionsSection) optionsSection.style.display = 'block';
}

// ✏️ YEMEK DÜZENLEME MODALI
function openMenuModalFromBtn(btn) {
    document.getElementById('menuFormModal').style.display = 'flex';
    document.getElementById('menuModalTitle').innerText = 'Yemeği Düzenle';
    document.getElementById('modal-add-btn').style.display = 'none';
    document.getElementById('modal-update-btn').style.display = 'block';

    const menuId = btn.getAttribute('data-id');
    const foodId = btn.getAttribute('data-food-id');
    const categoryId = btn.getAttribute('data-category-id'); 
    const customName = btn.getAttribute('data-custom-name');
    const price = btn.getAttribute('data-price');
    const stock = btn.getAttribute('data-stock');
    const image = btn.getAttribute('data-image');

    document.getElementById('update-menu-id').value = menuId;
    document.getElementById('menu-id').value = menuId;  
    document.getElementById('food-name').value = foodId;
    
    const categorySelect = document.getElementById('category-id');
    if (categorySelect) {
        categorySelect.value = (categoryId !== 'None' && categoryId) ? categoryId : '';
    }

    document.getElementById('menu-custom-name').value = customName !== 'None' ? customName : '';
    document.getElementById('menu-price').value = price;
    document.getElementById('menu-stock').value = stock;

    const previewBox = document.getElementById('menu-image-preview');
    if (image && image.trim() !== '') {
        previewBox.innerHTML = `<img src="/static/images/menus/${image}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">`;
    } else {
        previewBox.innerHTML = '<i class="ph-fill ph-cooking-pot" style="color: #9ca3af; font-size: 32px;"></i>';
    }

    // 🛠️ OPSİYONLARI VERİTABANINDAN ÇEKİP EKRANA ÇİZME KISMI
    const optionsSection = document.getElementById('options-section');
    if(optionsSection) optionsSection.style.display = 'block'; 
    
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '<div style="padding: 15px; text-align: center; color: #6b7280; font-weight: 600;"><i class="ph-bold ph-hourglass-high"></i> Mevcut seçenekler yükleniyor...</div>';
    optionGroupIndex = 0; 

    fetch('/api/menu_options?menu_id=' + menuId)
        .then(res => res.json())
        .then(data => {
            optionsContainer.innerHTML = ''; 
            if (data.success && data.options && data.options.length > 0) {
                data.options.forEach(opt => {
                    const groupId = optionGroupIndex++;
                    const isReq = opt.is_required ? 'checked' : '';
                    const isMult = opt.is_multiple ? 'checked' : '';
                    
                    const groupHTML = `
                        <div class="option-group" id="group-${groupId}" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; position: relative; margin-bottom: 15px; animation: fadeIn 0.3s ease-out;">
                            <button type="button" onclick="document.getElementById('group-${groupId}').remove()" style="position: absolute; top: 12px; right: 12px; background: #fee2e2; color: #dc2626; border: none; width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; display: flex; align-items: center; justify-content: center; transition: 0.2s;" onmouseover="this.style.background='#fca5a5'" onmouseout="this.style.background='#fee2e2'">&times;</button>
                            
                            <div style="display: flex; gap: 15px; margin-bottom: 15px; padding-right: 30px;">
                                <div style="flex: 2;">
                                    <input type="text" name="option_names[]" value="${opt.option_name}" class="form-input" style="margin: 0; font-weight: 600;">
                                </div>
                                <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 8px; background: white; padding: 8px 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                    <label style="font-size: 12px; font-weight: 600; color: #374151; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                                        <input type="checkbox" name="is_required_${groupId}" value="1" style="transform: scale(1.2);" ${isReq}> Zorunlu Seçim
                                    </label>
                                    <label style="font-size: 12px; font-weight: 600; color: #374151; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                                        <input type="checkbox" name="is_multiple_${groupId}" value="1" style="transform: scale(1.2);" ${isMult}> Çoklu Seçim
                                    </label>
                                </div>
                            </div>

                            <div class="choices-container" id="choices-${groupId}" style="display: flex; flex-direction: column; gap: 8px;">
                                ${opt.choices.map(ch => {
                                    let optionsHTML = document.getElementById('hidden-stock-options') ? document.getElementById('hidden-stock-options').innerHTML : '';
                                    
                                    if (ch.linked_menu_id) {
                                        optionsHTML = optionsHTML.replace(`value="${ch.linked_menu_id}"`, `value="${ch.linked_menu_id}" selected`);
                                    }

                                    return `
                                    <div style="display: flex; gap: 10px; align-items: center;">
                                        <input type="text" name="choice_names_${groupId}[]" value="${ch.choice_name}" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px;">
                                        <input type="number" step="0.01" name="additional_prices_${groupId}[]" value="${ch.additional_price}" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 140px;">
                                        
                                        <select name="linked_menu_ids_${groupId}[]" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 180px; cursor: pointer;">
                                            ${optionsHTML}
                                        </select>

                                        <button type="button" onclick="this.parentElement.remove()" style="background: none; border: none; color: #9ca3af; cursor: pointer; font-size: 18px; transition: 0.2s;" onmouseover="this.style.color='#dc2626'" onmouseout="this.style.color='#9ca3af'">&times;</button>
                                    </div>
                                    `;
                                }).join('')}
                            </div>
                            
                            <button type="button" onclick="addChoice(${groupId})" style="background: none; border: 1px dashed #d1d5db; color: #4b5563; padding: 8px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 10px; transition: 0.2s;" onmouseover="this.style.borderColor='#4f46e5'; this.style.color='#4f46e5'" onmouseout="this.style.borderColor='#d1d5db'; this.style.color='#4b5563'">
                                + Yeni Seçenek Ekle (Alt Kırılım)
                            </button>
                        </div>
                    `;
                    optionsContainer.insertAdjacentHTML('beforeend', groupHTML);
                });
            }
        })
        .catch(err => {
            optionsContainer.innerHTML = '<div style="padding: 15px; text-align: center; color: #dc2626; font-weight: 600;"><i class="ph-bold ph-x-circle"></i> Seçenekler yüklenemedi.</div>';
            console.error("Seçenekler çekilirken hata:", err);
            if(typeof window.showToast === 'function') window.showToast("Seçenekler yüklenirken hata oluştu.", "error");
        });
}

function closeMenuModal() {
    document.getElementById('menuFormModal').style.display = 'none';
}

// 🛠️ OPSİYON GRUBU VE SEÇENEK EKLEME FONKSİYONLARI 
function addOptionGroup() {
    const container = document.getElementById('options-container');
    const groupId = optionGroupIndex++;
    
    const stockOptionsHTML = document.getElementById('hidden-stock-options') ? document.getElementById('hidden-stock-options').innerHTML : '<option value="">-- Stok Bağlantısı Yok --</option>';

    const groupHTML = `
        <div class="option-group" id="group-${groupId}" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; position: relative; animation: fadeIn 0.3s ease-out;">
            <button type="button" onclick="document.getElementById('group-${groupId}').remove()" style="position: absolute; top: 12px; right: 12px; background: #fee2e2; color: #dc2626; border: none; width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; display: flex; align-items: center; justify-content: center; transition: 0.2s;" onmouseover="this.style.background='#fca5a5'" onmouseout="this.style.background='#fee2e2'" title="Grubu Sil">&times;</button>
            <div style="display: flex; gap: 15px; margin-bottom: 15px; padding-right: 30px;">
                <div style="flex: 2;">
                    <input type="text" name="option_names[]" placeholder="Seçenek Grubu (Örn: Ekstra Malzemeler, Hamur Tipi)" class="form-input" style="margin: 0; font-weight: 600;">
                </div>
                <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 8px; background: white; padding: 8px 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                    <label style="font-size: 12px; font-weight: 600; color: #374151; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <input type="checkbox" name="is_required_${groupId}" value="1" style="transform: scale(1.2);"> Zorunlu Seçim
                    </label>
                    <label style="font-size: 12px; font-weight: 600; color: #374151; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <input type="checkbox" name="is_multiple_${groupId}" value="1" style="transform: scale(1.2);"> Çoklu Seçim
                    </label>
                </div>
            </div>
            
            <div class="choices-container" id="choices-${groupId}" style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="text" name="choice_names_${groupId}[]" placeholder="Seçenek Adı (Örn: Kaşar Peyniri)" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px;">
                    <input type="number" step="0.01" name="additional_prices_${groupId}[]" placeholder="+ Ücret (Yoksa boş bırak)" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 140px;">
                    
                    <select name="linked_menu_ids_${groupId}[]" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 180px; cursor: pointer;">
                        ${stockOptionsHTML}
                    </select>

                    <button type="button" onclick="this.parentElement.remove()" style="background: none; border: none; color: #9ca3af; cursor: pointer; font-size: 18px; transition: 0.2s;" onmouseover="this.style.color='#dc2626'" onmouseout="this.style.color='#9ca3af'">&times;</button>
                </div>
            </div>
            
            <button type="button" onclick="addChoice(${groupId})" style="background: none; border: 1px dashed #d1d5db; color: #4b5563; padding: 8px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 10px; transition: 0.2s;" onmouseover="this.style.borderColor='#4f46e5'; this.style.color='#4f46e5'" onmouseout="this.style.borderColor='#d1d5db'; this.style.color='#4b5563'">
                + Yeni Seçenek Ekle
            </button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', groupHTML);
}

function addChoice(groupId) {
    const container = document.getElementById(`choices-${groupId}`);
    const stockOptionsHTML = document.getElementById('hidden-stock-options') ? document.getElementById('hidden-stock-options').innerHTML : '<option value="">-- Stok Bağlantısı Yok --</option>';

    const choiceHTML = `
        <div style="display: flex; gap: 10px; align-items: center;">
            <input type="text" name="choice_names_${groupId}[]" placeholder="Seçenek Adı (Örn: Sucuk)" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px;">
            <input type="number" step="0.01" name="additional_prices_${groupId}[]" placeholder="+ Ücret (Yoksa boş bırak)" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 140px;">
            
            <select name="linked_menu_ids_${groupId}[]" class="form-input" style="margin: 0; padding: 8px 12px; font-size: 13px; width: 180px; cursor: pointer;">
                ${stockOptionsHTML}
            </select>

            <button type="button" onclick="this.parentElement.remove()" style="background: none; border: none; color: #9ca3af; cursor: pointer; font-size: 18px; transition: 0.2s;" onmouseover="this.style.color='#dc2626'" onmouseout="this.style.color='#9ca3af'">&times;</button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', choiceHTML);
}

// 🎟️ KUPON VE PROMOSYON YÖNETİMİ
function openPromoModal() {
    document.getElementById('promoModal').style.display = 'flex';
    loadPromos();
}

function closePromoModal() {
    document.getElementById('promoModal').style.display = 'none';
}

function loadPromos() {
    const tbody = document.getElementById('promo-table-body');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Yükleniyor...</td></tr>';

    fetch('/api/manage_promos')
    .then(res => res.json())
    .then(data => {
        if(data.success && data.promos && data.promos.length > 0) {
            tbody.innerHTML = data.promos.map(p => `
                <tr>
                    <td style="font-weight:700; color:#111827;">${p.code_name}</td>
                    <td style="color:#059669; font-weight:600;">${p.discount_type === 'percentage' ? '%' + p.discount_value : '₺' + p.discount_value}</td>
                    <td>₺${p.min_cart_amount}</td>
                    <td>
                        <button onclick="togglePromo(${p.promo_id}, ${p.is_active ? 0 : 1})" 
                            style="background:${p.is_active ? '#dcfce3' : '#f3f4f6'}; color:${p.is_active ? '#16a34a' : '#6b7280'}; border:none; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:11px; cursor:pointer;">
                            ${p.is_active ? '<i class="ph-bold ph-check-circle"></i> Aktif' : '<i class="ph-bold ph-x-circle"></i> Pasif'}
                        </button>
                    </td>
                    <td><button onclick="deletePromo(${p.promo_id})" style="background:none; border:none; color:#dc2626; font-size:18px; cursor:pointer;"><i class="ph-bold ph-trash"></i></button></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#6b7280;">Henüz aktif kuponunuz yok.</td></tr>';
        }
    })
    .catch(err => {
        console.error('Kupon Yükleme Hatası:', err);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#ef4444;">Kuponlar yüklenirken bir hata oluştu.</td></tr>';
    });
}

function addPromo() {
    const code = document.getElementById('new-promo-code').value.trim().toUpperCase();
    const type = document.getElementById('new-promo-type').value;
    const val = document.getElementById('new-promo-val').value;
    const min = document.getElementById('new-promo-min').value;

    if(!code || !val) {
        if(typeof window.showToast === 'function') window.showToast("Kod ve İndirim tutarı boş olamaz!", "error");
        else alert("Kod ve İndirim tutarı boş olamaz!");
        return;
    }

    fetch('/api/manage_promos', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'add', code_name: code, discount_type: type, discount_value: val, min_cart_amount: min || 0})
    }).then(res => res.json()).then(data => {
        if(data.success) {
            document.getElementById('new-promo-code').value = '';
            document.getElementById('new-promo-val').value = '';
            document.getElementById('new-promo-min').value = '';
            if(typeof window.showToast === 'function') window.showToast("Kupon başarıyla oluşturuldu!", "success");
            loadPromos();
        } else {
            if(typeof window.showToast === 'function') window.showToast(data.message, "error");
        }
    });
}

let pendingPromoDeleteId = null;

function deletePromo(id) {
    pendingPromoDeleteId = id;
    const modal = document.getElementById('promoDeleteConfirmModal');
    if (modal) modal.style.display = 'flex';
}

function closePromoDeleteModal() {
    pendingPromoDeleteId = null;
    const modal = document.getElementById('promoDeleteConfirmModal');
    if (modal) modal.style.display = 'none';
}

function executePromoDelete() {
    if (pendingPromoDeleteId === null) return;
    
    const id = pendingPromoDeleteId;
    const btn = document.getElementById('confirmPromoDeleteBtn');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Siliniyor...';
    btn.style.pointerEvents = 'none';

    fetch('/api/manage_promos', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'delete', promo_id: id})
    }).then(res => res.json()).then(data => { 
        if(data.success) {
            if(typeof window.showToast === 'function') window.showToast("Kupon başarıyla silindi.", "success");
            loadPromos(); 
        }
        closePromoDeleteModal();
        btn.innerHTML = originalText;
        btn.style.pointerEvents = 'auto';
    }).catch(err => {
        console.error('Kupon silme hatası:', err);
        closePromoDeleteModal();
        btn.innerHTML = originalText;
        btn.style.pointerEvents = 'auto';
    });
}

function togglePromo(id, newStatus) {
    fetch('/api/manage_promos', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'toggle', promo_id: id, is_active: newStatus})
    }).then(res => res.json()).then(data => { 
        if(data.success) {
            if(typeof window.showToast === 'function') window.showToast("Kupon durumu güncellendi.", "success");
            loadPromos(); 
        } 
    });
}

// ==========================================
// 🛡️ MENÜ FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const menuForm = document.getElementById('menu-form');
    
    if (menuForm) {
        menuForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const foodId = document.getElementById('food-name').value;
            const categorySelect = document.getElementById('category-id');
            const categoryId = categorySelect ? categorySelect.value : 'valid'; 
            
            const customName = document.getElementById('menu-custom-name').value.trim();
            const price = document.getElementById('menu-price').value.trim();
            const stock = document.getElementById('menu-stock').value.trim();

            if (!foodId || foodId === "None") {
                hasError = true;
                errorMessage = "Lütfen Sistem Altyapısı (Arka Plan) için yemek tipi seçin.";
            } else if (!categoryId || categoryId === "None" || categoryId === "") {
                hasError = true;
                errorMessage = "Lütfen Restoran Kategoriniz (Ön Yüz) için bir kategori seçin.";
            } else if (!customName) {
                hasError = true;
                errorMessage = "Lütfen menüdeki özel adı girin.";
            } else if (!price || parseFloat(price) <= 0) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir fiyat girin (0'dan büyük olmalı).";
            } else if (!stock || parseInt(stock) < 0) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir stok adedi girin (0 veya daha büyük olmalı).";
            }

            // 2. Dinamik Seçenek (Opsiyon) Kontrolleri
            if (!hasError) {
                const optionGroups = document.querySelectorAll('.option-group');
                for (let i = 0; i < optionGroups.length; i++) {
                    const group = optionGroups[i];
                    const groupNameInput = group.querySelector('input[name="option_names[]"]');
                    
                    if (!groupNameInput || groupNameInput.value.trim() === "") {
                        hasError = true;
                        errorMessage = "Lütfen eklediğiniz tüm seçenek gruplarına bir isim verin (Örn: Soslar) veya boş grubu silin.";
                        break;
                    }

                    const choiceInputs = group.querySelectorAll('input[name^="choice_names_"]');
                    
                    if (choiceInputs.length === 0) {
                        hasError = true;
                        errorMessage = `"${groupNameInput.value.trim()}" grubu için en az bir seçenek (şık) eklemelisiniz.`;
                        break;
                    }

                    for(let j=0; j < choiceInputs.length; j++) {
                        if(choiceInputs[j].value.trim() === "") {
                            hasError = true;
                            errorMessage = `"${groupNameInput.value.trim()}" grubundaki boş seçenek adlarını doldurun veya o satırı silin.`;
                            break;
                        }
                    }
                    if(hasError) break;
                }
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

//HIZLI KATEGORİ YÖNETİMİ (MODAL)
function openQuickCategoryModal() {
    document.getElementById('quickCategoryModal').style.display = 'flex';
    document.getElementById('quick-cat-name').value = '';
    setTimeout(() => document.getElementById('quick-cat-name').focus(), 100);
}

function closeQuickCategoryModal() {
    document.getElementById('quickCategoryModal').style.display = 'none';
}

function submitQuickCategory() {
    const catName = document.getElementById('quick-cat-name').value.trim();
    
    if (!catName) {
        if (typeof window.showToast === 'function') window.showToast("Lütfen bir kategori adı girin.", "error");
        else alert("Lütfen bir kategori adı girin.");
        return;
    }

    fetch('/api/manage_restaurant_categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add', category_name: catName }) 
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if (typeof window.showToast === 'function') window.showToast("Kategori başarıyla eklendi!", "success");
            
            const select = document.getElementById('category-id');
            if (select) {
                const option = document.createElement('option');
                option.value = data.category_id;
                option.text = data.category_name;
                select.appendChild(option);
                select.value = data.category_id; 
            }
            
            closeQuickCategoryModal();
        } else {
            if (typeof window.showToast === 'function') window.showToast(data.message, "error");
            else alert(data.message);
        }
    })
    .catch(err => console.error("Kategori ekleme hatası:", err));
}

// 🚀 SEKME (TAB) DEĞİŞTİRME MOTORU
function switchMenuTab(tab) {
    if(tab === 'active') {
        document.getElementById('active-menus-wrapper').style.display = 'block';
        document.getElementById('phantom-menus-wrapper').style.display = 'none';
        document.getElementById('tab-active').style.background = '#111827';
        document.getElementById('tab-active').style.color = 'white';
        document.getElementById('tab-phantom').style.background = '#f3f4f6';
        document.getElementById('tab-phantom').style.color = '#4b5563';
    } else {
        document.getElementById('active-menus-wrapper').style.display = 'none';
        document.getElementById('phantom-menus-wrapper').style.display = 'block';
        document.getElementById('tab-phantom').style.background = '#111827';
        document.getElementById('tab-phantom').style.color = 'white';
        document.getElementById('tab-active').style.background = '#f3f4f6';
        document.getElementById('tab-active').style.color = '#4b5563';
    }
}

// 🚀 HIZLI DEPO MODALI YÖNETİMİ (HEM EKLE HEM DÜZENLE)
function openPhantomModal(btn = null) {
    document.getElementById('phantomModal').style.display = 'flex';
    
    if (btn) {
        // Düzenleme Modu (Edit)
        document.getElementById('phantomModalTitle').innerHTML = '<i class="ph-bold ph-ghost" style="color: #64748b; font-size: 22px;"></i> Depo Ürününü Düzenle';
        document.getElementById('phantom-action').value = 'update';
        document.getElementById('phantom-update-id').value = btn.getAttribute('data-id');
        document.getElementById('phantom-menu-id').value = btn.getAttribute('data-id');
        document.getElementById('phantom-food-id').value = btn.getAttribute('data-food-id');
        document.getElementById('phantom-custom-name').value = btn.getAttribute('data-custom-name');
        document.getElementById('phantom-price').value = btn.getAttribute('data-price');
        document.getElementById('phantom-stock').value = btn.getAttribute('data-stock');
        
        document.getElementById('phantom-add-btn').style.display = 'none';
        document.getElementById('phantom-update-btn').style.display = 'block';
    } else {
        // Yeni Ekleme Modu (Add)
        document.getElementById('phantomModalTitle').innerHTML = '<i class="ph-bold ph-ghost" style="color: #64748b; font-size: 22px;"></i> Hızlı Depo Ürünü Ekle';
        document.getElementById('phantom-action').value = 'add';
        document.getElementById('phantom-update-id').value = '';
        document.getElementById('phantom-menu-id').value = ''; 
        document.getElementById('phantom-custom-name').value = '';
        document.getElementById('phantom-price').value = '0';
        document.getElementById('phantom-stock').value = '';
        
        document.getElementById('phantom-add-btn').style.display = 'block';
        document.getElementById('phantom-update-btn').style.display = 'none';
    }
}

function closePhantomModal() {
    document.getElementById('phantomModal').style.display = 'none';
}

// 🛡️ HIZLI DEPO FORMU KONTROL MOTORU (Şık Bildirimler İçin)
function validatePhantomForm(event) {
    const nameInput = document.getElementById('phantom-custom-name').value.trim();
    const stockInput = document.getElementById('phantom-stock').value.trim();
    
    if (!nameInput) {
        if (typeof window.showToast === 'function') {
            window.showToast('Lütfen depo ürününün adını girin.', 'error');
        } else {
            alert('Lütfen depo ürününün adını girin.');
        }
        event.preventDefault();
        return false;
    }
    
    if (!stockInput || parseInt(stockInput) < 0) {
        if (typeof window.showToast === 'function') {
            window.showToast('Lütfen geçerli bir stok adedi girin.', 'error');
        } else {
            alert('Lütfen geçerli bir stok adedi girin.');
        }
        event.preventDefault();
        return false;
    }
    
    return true; 
}

