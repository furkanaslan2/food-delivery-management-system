// ==========================================
// 📦 SİPARİŞ DETAY MODALI VE API İSTEĞİ (3 SÜTUN + NOTLAR)
// ==========================================
function showOrderDetails(event, orderId) {
    event.preventDefault();
    document.getElementById('detailModal').style.display = 'flex';
    document.getElementById('modal-items').innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 20px;">Yükleniyor...</td></tr>';
    document.getElementById('grand-total').innerText = '₺0.00';

    fetch(`/order_details/${orderId}`)
        .then(response => response.json())
        .then(data => {
            let itemsHtml = '';
            let grandTotal = 0;

            if(!data || data.length === 0 || data.error) {
                itemsHtml = `<tr><td colspan="3" style="text-align:center; padding: 20px;">Ürün bulunamadı.</td></tr>`;
            } else {
                data.forEach(item => {
                    let total = item.quantity * parseFloat(item.unit_price);
                    grandTotal += total;

                    let extrasTotal = 0;
                    let choicesHtml = '';
                    
                    if (item.choices && item.choices.length > 0) {
                        choicesHtml = '<ul style="margin: 5px 0 0 15px; padding: 0; font-size: 12px; color: #6b7280; list-style-type: disc;">';
                        item.choices.forEach(choice => {
                            let addPrice = parseFloat(choice.additional_price || 0);
                            extrasTotal += addPrice;
                            let priceText = addPrice > 0 ? ` <strong style="color: #059669;">(+₺${addPrice.toFixed(2)})</strong>` : '';
                            choicesHtml += `<li>${choice.choice_name}${priceText}</li>`;
                        });
                        choicesHtml += '</ul>';
                    }

                    let basePrice = parseFloat(item.unit_price) - extrasTotal;

                    itemsHtml += `
                        <tr style="border-bottom: 1px solid #e5e7eb;">
                            <td style="padding: 12px; color: #111827;">
                                <div style="font-weight: 600;">${item.item_name} <span style="color: #6b7280; font-weight: 500;">(₺${basePrice.toFixed(2)})</span></div>
                                ${choicesHtml} 
                                ${item.item_note ? `<div style="font-size: 12px; color: #f59e0b; margin-top: 5px;"><i class="ph-bold ph-note-pencil"></i> Not: ${item.item_note}</div>` : ''}
                            </td>
                            <td style="padding: 12px; text-align: center; font-weight: 600;">${item.quantity}</td>
                            <td style="padding: 12px; font-weight: 600; color: #059669; text-align: right;">₺${total.toFixed(2)}</td>
                        </tr>
                    `;
                });
            }
            document.getElementById('modal-items').innerHTML = itemsHtml;
            document.getElementById('grand-total').innerText = '₺' + grandTotal.toFixed(2);
        });
}

function openOrderModal(isUpdate = false, btn = null) {
    document.getElementById('orderFormModal').style.display = 'flex';

    const courierSelect = document.getElementById('dynamic-courier-list');
    if (courierSelect) {
        courierSelect.innerHTML = '<option value="">Kuryeler yükleniyor...</option>';
        fetch('/api/get_couriers')
            .then(res => res.json())
            .then(data => {
                let options = '<option value="">Kurye Ata (Opsiyonel)...</option>';
                if(data.success && data.couriers) {
                    data.couriers.forEach(c => {
                        const isOffline = (c.is_online === 0 || c.is_online === false);
                        options += `<option value="${c.courier_id}" ${isOffline ? 'disabled' : ''}>
                            ${c.name} ${isOffline ? '- [Molada]' : ''}
                        </option>`;
                    });
                }
                courierSelect.innerHTML = options;
                
                if (isUpdate && btn) {
                    courierSelect.value = btn.getAttribute('data-courier');
                }
            });
    }

    const paymentSelectForLogic = document.getElementById('payment_method');
    if (paymentSelectForLogic) {
        Array.from(paymentSelectForLogic.options).forEach(opt => {
            if (opt.value === 'Online Payment') {
                if (isUpdate && btn && btn.getAttribute('data-payment-method') === 'Online Payment') {
                    opt.hidden = false;
                    opt.disabled = false;
                } else {
                    opt.hidden = true;
                    opt.disabled = true;
                }
            }
        });
    }
    
    if (isUpdate && btn) {
        document.getElementById('orderModalTitle').innerText = 'Siparişi Düzenle';
        document.getElementById('modal-add-btn').style.display = 'none';
        document.getElementById('modal-update-btn').style.display = 'block';
        document.getElementById('update-only-fields').style.display = 'flex';
        
        const orderId = btn.getAttribute('data-id');
        document.getElementById('update-order-id').value = orderId;
        document.getElementById('order-status').value = btn.getAttribute('data-status');
        
        const dateVal = btn.getAttribute('data-date');
        if(dateVal) document.getElementById('order-date').value = dateVal;
        
        document.getElementById('order-type').value = btn.getAttribute('data-type');
        document.getElementById('order-table-no').value = btn.getAttribute('data-table');
        document.getElementById('customer-name').value = btn.getAttribute('data-customer-name');
        document.getElementById('customer-address').value = btn.getAttribute('data-customer-address');
        document.getElementById('dynamic-courier-list').value = btn.getAttribute('data-courier');
        
        const paymentMethod = btn.getAttribute('data-payment-method');
        document.getElementById('payment_method').value = paymentMethod;

        const rawPhone = btn.getAttribute('data-customer-phone') || '';
        if (window.orderPhoneMask) {
            window.orderPhoneMask.unmaskedValue = rawPhone; 
        } else {
            const phoneInput = document.getElementById('customer-phone');
            if(phoneInput) phoneInput.value = rawPhone;
        }

        // 🚀 HİBRİT MODEL: Online ödeme ise yemekleri gizle, değilse aç ve doldur!
        const foodSection = document.getElementById('food-section');
        const container = document.getElementById('food-items-container');
        
        if (paymentMethod === 'Online Payment') {
            foodSection.style.display = 'none';
            container.innerHTML = ''; // Python'a boş gitmesi için içini temizliyoruz (Sadece bilgileri günceller)
        } else {
            foodSection.style.display = 'block';
            loadExistingOrderItems(orderId); // Sihirli fonksiyonumuz eski ürünleri yükleyecek
        }
        
        toggleOrderFields();
    } else {
        document.getElementById('orderModalTitle').innerText = 'Yeni Sipariş Ekle';
        document.getElementById('modal-add-btn').style.display = 'block';
        document.getElementById('modal-update-btn').style.display = 'none';
        document.getElementById('update-only-fields').style.display = 'none';
        document.getElementById('food-section').style.display = 'block';
        
        document.querySelectorAll('#order-form input[type="text"], #order-form textarea').forEach(el => el.value = '');
        document.querySelectorAll('#order-form select').forEach(el => el.selectedIndex = 0);
        
        if (window.orderPhoneMask) window.orderPhoneMask.unmaskedValue = ''; 
        document.getElementById('update-order-id').value = '';
        document.getElementById('dine-in-fields').style.display = 'none';
        document.getElementById('delivery-fields').style.display = 'none';
        
        document.getElementById('food-items-container').innerHTML = '';
        addFoodRow();
    }
}

function closeOrderModal() { document.getElementById('orderFormModal').style.display = 'none'; }
function closeModal() { document.getElementById('detailModal').style.display = 'none'; }

function toggleOrderFields() {
    const type = document.getElementById('order-type').value;
    document.getElementById('dine-in-fields').style.display = (type === 'Dine-in') ? 'block' : 'none';
    document.getElementById('delivery-fields').style.display = (type === 'Delivery') ? 'block' : 'none';
}

function loadExistingOrderItems(orderId) {
    const container = document.getElementById('food-items-container');
    container.innerHTML = '<div style="padding: 10px; color: #4f46e5; font-weight: 600; display: flex; align-items: center; gap: 6px;"><i class="ph-bold ph-hourglass-high"></i> Eski sipariş kalemleri yükleniyor...</div>';
    
    fetch(`/order_details/${orderId}`)
        .then(response => response.json())
        .then(data => {
            container.innerHTML = '';
            if(data && data.length > 0 && !data.error) {
                data.forEach(item => {
                    addFoodRow(item); 
                });
            } else {
                addFoodRow(); 
            }
        })
        .catch(err => {
            container.innerHTML = '<div style="color:#ef4444;">Kalemler yüklenirken hata oluştu.</div>';
            addFoodRow();
        });
}

// 🚀 DİNAMİK SATIR EKLEME MOTORU (Eski veriyi de içine alabilecek şekilde güçlendirildi)
function addFoodRow(existingItem = null) {
    const container = document.getElementById('food-items-container');
    const cartIndex = Date.now() + Math.floor(Math.random() * 1000);
    
    const templateEl = document.getElementById('food-options-template');
    if (!templateEl) return;
    const optionsHtml = templateEl.innerHTML;

    const rowDiv = document.createElement('div');
    rowDiv.className = 'food-row';
    rowDiv.style.cssText = "background: white; padding: 15px; border-radius: 8px; border: 1px solid #d1d5db; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);";
    
    let qtyVal = existingItem ? existingItem.quantity : 1;
    let noteVal = existingItem ? (existingItem.item_note || '') : '';

    rowDiv.innerHTML = `
        <div style="display: flex; gap: 10px; margin-bottom: 12px; align-items: stretch; height: 45px;">
            <input type="hidden" name="cart_index" value="${cartIndex}">
            
            <select name="menu_id_${cartIndex}" class="dynamic-food-list" style="flex: 2; margin: 0; padding: 0 10px; border: 1px solid #d1d5db; border-radius: 6px; font-family:inherit; font-weight:600; font-size: 14px; box-sizing: border-box; outline: none; cursor: pointer;" onchange="fetchMenuOptions(this, ${cartIndex})" required>
                ${optionsHtml}
            </select>
            
            <input type="number" name="qty_${cartIndex}" placeholder="Adet" value="${qtyVal}" min="1" style="flex: 0.5; margin: 0; padding: 0 10px; border: 1px solid #d1d5db; border-radius: 6px; font-family:inherit; font-weight:600; font-size: 14px; text-align: center; box-sizing: border-box; outline: none;" required>
            
            <button type="button" title="Bu Kalemi Sil" onclick="this.closest('.food-row').remove()" style="flex: 0 0 45px; margin: 0; padding: 0; background: transparent; border: 1px solid #fecaca; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-sizing: border-box; transition: 0.2s;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='transparent'">
                <img src="/static/images/icons/delete.png" style="width: 20px; height: 20px; object-fit: contain;">
            </button>
        </div>
        
        <input type="text" name="note_${cartIndex}" placeholder="Ürün Özel Notu (Örn: Az Pişmiş)" value="${noteVal}" style="width: 100%; height: 42px; margin: 0; padding: 0 12px; border: 1px solid #d1d5db; border-radius: 6px; font-family:inherit; font-size: 13px; outline: none; box-sizing: border-box;">
        
        <div id="options-container-${cartIndex}" style="margin-top: 10px;"></div>
    `;
    
    container.appendChild(rowDiv);

    // Eğer eski bir sipariş yükleniyorsa, yemeği seç ve ekstralarını çek
    const selectEl = rowDiv.querySelector(`select[name="menu_id_${cartIndex}"]`);
    if (existingItem) {
        selectEl.value = existingItem.menu_id;
        const selectedChoices = existingItem.choices ? existingItem.choices.map(c => String(c.choice_id)) : [];
        fetchMenuOptions(selectEl, cartIndex, selectedChoices);
    }
}

// 🚀 AJAX İLE SEÇENEKLERİ ÇEKME (Seçilmiş ekstraları otomatik işaretleme yeteneği eklendi)
async function fetchMenuOptions(selectEl, cartIndex, selectedChoices = []) {
    const container = document.getElementById(`options-container-${cartIndex}`);
    const menuId = selectEl.value;
    container.innerHTML = '';
    
    if (!menuId || menuId === "None") return;
    
    container.innerHTML = '<div style="color:#4f46e5; font-size:13px; font-weight:600; padding: 5px 0; display: flex; align-items: center; gap: 6px;"><i class="ph-bold ph-hourglass-high"></i> Seçenekler yükleniyor...</div>';
    
    try {
        const response = await fetch(`/api/menu_options?menu_id=${menuId}`);
        if (!response.ok) throw new Error("API Yanıt Vermedi");
        
        const data = await response.json();
        
        if (data.success && data.options && data.options.length > 0) {
            let html = '<div style="background: #f9fafb; padding: 12px; border-radius: 8px; border: 1px dashed #d1d5db; margin-top: 10px;">';
            data.options.forEach(opt => {
                html += `<div class="admin-option-group" data-required="${opt.is_required}" style="margin-bottom: 12px; transition: 0.2s;">
                            <div style="font-size: 13px; font-weight: 800; color: #374151; margin-bottom: 8px;">
                                ${opt.option_name} ${opt.is_required ? '<span style="color:#ef4444; font-size:11px;">*Zorunlu</span>' : ''}
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 12px;">`;
                
                opt.choices.forEach(choice => {
                    const inputType = opt.is_multiple ? 'checkbox' : 'radio';
                    const inputName = opt.is_multiple ? `chk_${opt.option_id}_${cartIndex}[]` : `rad_${opt.option_id}_${cartIndex}`;
                    const addPrice = parseFloat(choice.additional_price);
                    const priceText = addPrice > 0 ? `<strong style="color:#10b981;">(+₺${addPrice.toFixed(2)})</strong>` : '';
                    
                    // 🚀 SİHİRLİ EŞLEŞTİRME: Eğer bu ekstra eski siparişte varsa direkt işaretle!
                    const isChecked = selectedChoices.includes(String(choice.choice_id)) ? 'checked' : '';
                    
                    html += `
                        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #4b5563; cursor: pointer; font-weight: 500;">
                            <input type="${inputType}" name="${inputName}" value="${choice.choice_id}" class="choice-input" data-cart-index="${cartIndex}" ${isChecked} style="accent-color: #4f46e5; width: 16px; height: 16px;">
                            <span>${choice.choice_name} ${priceText}</span>
                        </label>
                    `;
                });
                html += `</div></div>`;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '';
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div style="color:#ef4444; font-size:12px;">Seçenekler yüklenemedi.</div>';
    }
}

// ==========================================
//  KURYE ATAMA MODALI (CANLI VERİ ÇEKER)
// ==========================================
function openCourierModal(orderId) {
    const inputEl = document.getElementById('courier-modal-order-id');
    const displayEl = document.getElementById('modal-display-order-id');
    const modalEl = document.getElementById('courierAssignModal');
    const selectEl = modalEl.querySelector('select[name="courier_id"]');
    
    if (inputEl) inputEl.value = orderId;
    if (displayEl) displayEl.innerText = "#" + orderId;
    
    if (selectEl) {
        selectEl.innerHTML = '<option value="" hidden>Kurye durumları güncelleniyor...</option>';
        
        fetch('/api/get_couriers')
            .then(res => res.json())
            .then(data => {
                let options = '<option value="" hidden>Atanacak Kuryeyi Seçin...</option>';
                if(data.success && data.couriers) {
                    data.couriers.forEach(c => {
                        const isOffline = (c.is_online === 0 || c.is_online === false);
                        options += `<option value="${c.courier_id}" ${isOffline ? 'disabled' : ''}>
                            ${c.name} ${isOffline ? '(🔴 Molada)' : ' (🟢 Müsait)'}
                        </option>`;
                    });
                }
                selectEl.innerHTML = options;
            })
            .catch(err => {
                selectEl.innerHTML = '<option value="" hidden>Hata oluştu, sayfayı yenileyin.</option>';
            });
    }

    if (modalEl) modalEl.style.display = 'flex';
}

function closeCourierModal() {
    const modalEl = document.getElementById('courierAssignModal');
    if (modalEl) modalEl.style.display = 'none';
}

// ==========================================
// 🔔 PROFESYONEL SESLİ BİLDİRİM VE SESSİZ GÜNCELLEME MOTORU
// ==========================================
let soundUnlocked = false;
const orderSound = new Audio("https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=ding-idea-40142.mp3");

document.addEventListener("DOMContentLoaded", function() {
    const overlay = document.getElementById('sound-unlock-overlay');
    const startBtn = document.getElementById('start-system-btn');
    const isSystemAlreadyStarted = sessionStorage.getItem('systemStarted') === 'true';

    if (!isSystemAlreadyStarted && overlay) {
        overlay.style.display = 'flex'; 
        if (startBtn) {
            startBtn.addEventListener('click', function() {
                orderSound.play().then(() => {
                    orderSound.pause(); orderSound.currentTime = 0; soundUnlocked = true;
                    sessionStorage.setItem('systemStarted', 'true');
                    overlay.style.opacity = '0';
                    overlay.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => overlay.style.display = 'none', 300);
                }).catch(err => console.log('Ses kilidi açılamadı:', err));
            });
        }
    } else if (isSystemAlreadyStarted) {
        soundUnlocked = true; 
        document.body.addEventListener('click', function unlockSilently() {
            orderSound.play().then(() => {
                orderSound.pause(); orderSound.currentTime = 0;
                document.body.removeEventListener('click', unlockSilently);
            }).catch(e => console.log('Sessiz kilit açma bekliyor...'));
        }, { once: true });
    }

    const alertBox = document.getElementById('new-order-alert');
    if (alertBox) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === "style") {
                    const currentDisplay = window.getComputedStyle(alertBox).getPropertyValue('display');
                    if (currentDisplay !== 'none' && soundUnlocked) {
                        orderSound.currentTime = 0;
                        orderSound.play().catch(e => console.log("Ses çalınamadı:", e));
                    }
                }
            });
        });
        observer.observe(alertBox, { attributes: true, attributeFilter: ['style'] });
    }
});

document.addEventListener("DOMContentLoaded", function() {
    let maxOrderId = 0;
    function updateMaxId() {
        document.querySelectorAll('.order-id').forEach(el => {
            let id = parseInt(el.textContent.trim());
            if (!isNaN(id) && id > maxOrderId) maxOrderId = id;
        });
    }
    
    updateMaxId(); 

    function checkAndRefreshTable() {
        const orderModal = document.getElementById('orderFormModal');
        const courierModal = document.getElementById('courierAssignModal');
        const detailModal = document.getElementById('detailModal');

        if ((orderModal && orderModal.style.display !== 'none') || (courierModal && courierModal.style.display !== 'none') || (detailModal && detailModal.style.display !== 'none')) {
            return; 
        }

        fetch(window.location.href)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTbody = doc.getElementById('orders-table-body');
                const currentTbody = document.getElementById('orders-table-body');

                if (newTbody && currentTbody && newTbody.innerHTML !== currentTbody.innerHTML) {
                    currentTbody.innerHTML = newTbody.innerHTML;
                    let oldMax = maxOrderId;
                    updateMaxId(); 
                    
                    if (maxOrderId > oldMax) {
                        const alertBox = document.getElementById('new-order-alert');
                        if (alertBox) {
                            alertBox.style.display = 'block'; 
                            setTimeout(() => { alertBox.style.display = 'none'; }, 5000);
                        }
                    }
                }
            }).catch(err => console.error("Sessiz güncelleme hatası:", err));
    }
    setInterval(checkAndRefreshTable, 5000);
});

document.addEventListener("DOMContentLoaded", function() {
    var phoneInput = document.getElementById('customer-phone');
    if (phoneInput) {
        window.orderPhoneMask = IMask(phoneInput, {
            mask: '\\0 (500) 000 00 00',
            lazy: false,  
            placeholderChar: '_' 
        });
            
        phoneInput.addEventListener('click', function() {
            var firstEmptyIndex = phoneInput.value.indexOf('_');
            if (firstEmptyIndex !== -1) {
                phoneInput.setSelectionRange(firstEmptyIndex, firstEmptyIndex);
            }
        });
    }
});

// ==========================================
// 🛡️ FORM GÖNDERİLMEDEN ÖNCE MASTER KONTROL (TÜM FORMU KAPSAR)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const orderForm = document.getElementById('order-form');
    
    if (orderForm) {
        orderForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const orderType = document.querySelector('[name="order_type"]').value;
            if (!orderType && !document.getElementById('update-only-fields').style.display.includes('flex')) {
                hasError = true;
                errorMessage = "Lütfen sipariş türünü (Masaya veya Paket) seçin.";
            }

            const foodSection = document.getElementById('food-section');
            if (!hasError && foodSection && foodSection.style.display !== 'none') {
                const addedFoods = document.querySelectorAll('.food-row');
                if (addedFoods.length === 0) {
                    hasError = true;
                    errorMessage = "Lütfen siparişe en az bir ürün ekleyin.";
                } else {
                    addedFoods.forEach(row => {
                        const select = row.querySelector('select');
                        const qty = row.querySelector('input[type="number"]');
                        if (!select.value || select.value === "None" || select.value === "") {
                            hasError = true;
                            errorMessage = "Lütfen eklediğiniz satırlarda bir ürün seçin.";
                        }
                        if (!qty.value || parseInt(qty.value) < 1) {
                            hasError = true;
                            errorMessage = "Lütfen geçerli bir ürün adedi girin.";
                        }
                    });
                }
            }

            if (!hasError && orderType === 'Delivery') {
                const name = document.querySelector('[name="customer_name"]').value.trim();
                const phone = document.querySelector('[name="customer_phone"]').value.trim();
                const address = document.querySelector('[name="customer_address"]').value.trim();
                const payment = document.querySelector('[name="payment_method"]');
                const paymentVal = payment ? payment.value.trim() : 'Cash'; 

                if (!name || !phone || !address || (payment && !paymentVal)) {
                    hasError = true;
                    errorMessage = "Lütfen müşteri bilgilerini ve ödeme yöntemini eksiksiz doldurun.";
                } else if (phone.includes('_') || phone.length < 15) {
                    hasError = true;
                    errorMessage = "Lütfen telefon numarasını tam ve eksiksiz girin.";
                }
            } 
            else if (!hasError && orderType === 'Dine-in') {
                const tableNo = document.querySelector('[name="table_no"]').value.trim();
                if (!tableNo) {
                    hasError = true;
                    errorMessage = "Masa siparişleri için lütfen Masa Numarasını girin.";
                }
            }

            if (!hasError && foodSection && foodSection.style.display !== 'none') {
                document.querySelectorAll('.admin-option-group').forEach(group => {
                    const isRequired = group.getAttribute('data-required');
                    if (isRequired === "1" || isRequired === "true") {
                        const checkedCount = group.querySelectorAll('.choice-input:checked').length;
                        if (checkedCount === 0) {
                            hasError = true;
                            errorMessage = "Lütfen kırmızı renkle işaretlenen zorunlu seçenekleri belirleyin!";
                            group.style.borderLeft = '4px solid #ef4444';
                            group.style.paddingLeft = '10px';
                            group.style.backgroundColor = '#fef2f2';
                        } else {
                            group.style.borderLeft = 'none';
                            group.style.paddingLeft = '0';
                            group.style.backgroundColor = 'transparent';
                        }
                    }
                });
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

            if (foodSection && foodSection.style.display !== 'none') {
                document.querySelectorAll('.dynamic-choice-hidden').forEach(el => el.remove());
                document.querySelectorAll('.choice-input:checked').forEach(input => {
                    const cartIndex = input.getAttribute('data-cart-index');
                    const hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.name = `choices_${cartIndex}[]`;
                    hidden.value = input.value;
                    hidden.className = 'dynamic-choice-hidden';
                    orderForm.appendChild(hidden);
                });
            }
        });
    }
});