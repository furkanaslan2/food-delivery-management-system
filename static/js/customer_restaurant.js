// ==========================================
// 🏪 RESTORAN DETAY & MENÜ YÖNETİM SİSTEMİ (ORİJİNAL ÇALIŞAN KOD)
// ==========================================

// ----------------------------------------------------
// 1. YAPIŞKAN KATEGORİ MENÜSÜ VE SCROLL TAKİBİ
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    const sections = document.querySelectorAll('.menu-section');
    const navLinks = document.querySelectorAll('.cat-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                const navHeight = document.getElementById('categoryNav').offsetHeight;
                const headerHeight = document.getElementById('main-navbar').offsetHeight;
                const targetPosition = targetSection.getBoundingClientRect().top + window.pageYOffset - navHeight - headerHeight - 10;
                
                window.scrollTo({ top: targetPosition, behavior: "smooth" });
            }
        });
    });

    window.addEventListener('scroll', () => {
        let current = '';
        const navHeight = document.getElementById('categoryNav').offsetHeight;
        const headerHeight = document.getElementById('main-navbar').offsetHeight;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (pageYOffset >= (sectionTop - navHeight - headerHeight - 30)) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
                link.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }
        });
    });
});

// ----------------------------------------------------
// 2. SEPETE EKLEME & EK SEÇENEKLER SİSTEMİ
// ----------------------------------------------------
let currentBasePrice = 0;
let activeFormData = null;
let activeFormElement = null;

document.addEventListener("DOMContentLoaded", function() {
    const addForms = document.querySelectorAll('.add-to-cart-form');
    
    addForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); 
            
            const btn = form.querySelector('.add-btn');
            if(btn.disabled) return;

            const formData = new FormData(form);
            const menuId = formData.get('menu_id');
            const basePrice = parseFloat(formData.get('price'));
            const foodName = formData.get('food_name');
            
            fetch('/api/menu_options?menu_id=' + menuId)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.options && data.options.length > 0) {
                    openCustomerOptionsModal(data.options, formData, basePrice, foodName, form);
                } else {
                    executeCartAjax(formData, form);
                }
            })
            .catch(err => {
                console.error('Opsiyon kontrol hatası:', err);
                executeCartAjax(formData, form); 
            });
        });
    });
});

function openCustomerOptionsModal(options, formData, basePrice, foodName, formEl) {
    activeFormData = formData;
    activeFormElement = formEl;
    currentBasePrice = basePrice;
    
    document.getElementById('opt-food-name').innerText = foodName;
    const container = document.getElementById('opt-dynamic-content');
    container.innerHTML = '';
    
    options.forEach(opt => {
        let html = `<div style="margin-bottom: 25px;" class="opt-group" data-is-required="${opt.is_required}" data-name="${opt.option_name}">
            <h4 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 700; color: #111827;">${opt.option_name} ${opt.is_required ? '<span style="color:#ef4444; font-size:12px; font-weight: 600; margin-left:5px;">(Zorunlu)</span>' : ''}</h4>
            <div style="display: flex; flex-direction: column; gap: 10px;">`;
        
        const inputType = opt.is_multiple ? 'checkbox' : 'radio';
        const reqAttr = opt.is_required && !opt.is_multiple ? 'required' : '';
        
        opt.choices.forEach(ch => {
            html += `
                <label style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 14px 16px; border: 1px solid #e5e7eb; border-radius: 12px; background: white; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.02);" onmouseover="this.style.borderColor='#4f46e5'" onmouseout="this.style.borderColor='#e5e7eb'">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <input type="${inputType}" name="opt_${opt.option_id}" value="${ch.choice_name}" data-id="${ch.choice_id}" data-price="${ch.additional_price}" onchange="calculateModalPrice()" ${reqAttr} style="transform: scale(1.3); cursor: pointer; accent-color: #4f46e5;">
                        <span style="font-size: 15px; font-weight: 600; color: #374151;">${ch.choice_name}</span>
                    </div>
                    ${ch.additional_price > 0 ? `<span style="color: #059669; font-weight: 700; font-size: 14px; background: #ecfdf5; padding: 4px 8px; border-radius: 8px;">+$${ch.additional_price}</span>` : ''}
                </label>
            `;
        });
        html += `</div></div>`;
        container.innerHTML += html;
    });
    
    calculateModalPrice();
    document.getElementById('customerOptionsModal').style.display = 'flex';
}

function calculateModalPrice() {
    let totalExtra = 0;
    const inputs = document.querySelectorAll('#customer-options-form input:checked');
    inputs.forEach(input => {
        totalExtra += parseFloat(input.getAttribute('data-price'));
    });
    
    const qty = parseInt(activeFormData.get('quantity'));
    const finalPrice = (currentBasePrice + totalExtra) * qty;
    document.getElementById('opt-total-price').innerText = finalPrice.toFixed(2);
    return currentBasePrice + totalExtra;
}

function submitOptionsToCart() {
    const form = document.getElementById('customer-options-form');
    
    let isValid = true;
    let errorMessage = "";
    const groups = form.querySelectorAll('.opt-group');
    
    for (let group of groups) {
        if (group.getAttribute('data-is-required') === 'true' || group.getAttribute('data-is-required') === '1') {
            const checkedItems = group.querySelectorAll('input:checked');
            if (checkedItems.length === 0) {
                isValid = false;
                errorMessage = `Lütfen "${group.getAttribute('data-name')}" seçeneğinden en az birini işaretleyin.`;
                break; 
            }
        }
    }
    
    if (!isValid) {
        if (typeof showToast === "function") showToast(errorMessage, "error");
        else alert(errorMessage);
        return; 
    }
    
    if(!form.checkValidity()) { form.reportValidity(); return; } 

    let selectedTexts = [];
    let totalExtra = 0;
    
    activeFormData.delete('choices');
    
    document.querySelectorAll('#customer-options-form input:checked').forEach(input => {
        selectedTexts.push(input.value);
        let valStr = input.getAttribute('data-price') || "0";
        totalExtra += parseFloat(valStr.replace(',', '.')) || 0;
        activeFormData.append('choices', input.getAttribute('data-id'));
    });
    
    if(selectedTexts.length > 0) {
        const currentName = activeFormData.get('food_name');
        activeFormData.set('food_name', currentName + ' (' + selectedTexts.join(', ') + ')');
    }
    
    // 🛠️ DÜZELTME 1: Backend iki kere eklemesin diye SADECE baz fiyatı yolluyoruz!
    activeFormData.set('price', currentBasePrice); 
    
    // 🛠️ DÜZELTME 2: Navbar'ın doğru hesaplaması için toplam fiyatı özel parametre olarak yolluyoruz!
    const finalUnitPrice = currentBasePrice + totalExtra;
    executeCartAjax(activeFormData, activeFormElement, finalUnitPrice);
    
    closeCustomerOptionsModal();
}

function closeCustomerOptionsModal() { document.getElementById('customerOptionsModal').style.display = 'none'; }

// 🛠️ DÜZELTME 3: "customPrice" parametresi eklendi
function executeCartAjax(formData, formElement, customPrice = null) {
    const btn = formElement.querySelector('.add-btn');
    const originalText = btn.innerHTML;
    
    // 🛠️ DÜZELTME 4: Eğer ekstralı bir fiyatsa customPrice'ı kullan, yoksa formdan çek
    let itemPrice;
    if (customPrice !== null && customPrice !== undefined) {
        itemPrice = customPrice;
    } else {
        itemPrice = parseFloat(formData.get('price')) || 0;
    }
    
    const itemQty = parseInt(formData.get('quantity')) || 1;
    const addedTotal = itemPrice * itemQty;
    
    fetch(formElement.action, {
        method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            btn.innerHTML = '<i class="ph-bold ph-check"></i> Eklendi';
            btn.style.backgroundColor = '#059669'; 
            btn.style.transform = 'scale(1.05)';
            
            setTimeout(() => { btn.innerHTML = originalText; btn.style.backgroundColor = '#10b981'; btn.style.transform = 'scale(1)'; }, 1500);
            
            let badge = document.getElementById('nav-cart-badge');
            if (badge) {
                badge.innerText = data.total_cart_qty;
                badge.style.display = data.total_cart_qty > 0 ? 'flex' : 'none';
            }
            
            let priceTag = document.getElementById('nav-cart-total');
            if (priceTag) {
                let currentTotal = parseFloat(priceTag.getAttribute('data-total')) || 0;
                
                if (data.cart_cleared) {
                    currentTotal = addedTotal;
                    if (typeof showToast === "function") showToast("Yeni restoran seçildiği için sepet yenilendi.", "success");
                } else {
                    currentTotal += addedTotal;
                }
                
                priceTag.setAttribute('data-total', currentTotal);
                priceTag.innerText = '$' + currentTotal.toFixed(2);
                priceTag.style.display = 'inline-block'; 
                
                priceTag.style.transform = 'scale(1.15)';
                setTimeout(() => { priceTag.style.transform = 'scale(1)'; }, 200);
            }
        } else {
            if (typeof showToast === "function") showToast(data.message || 'Sepete eklenirken bir hata oluştu.', 'error');
            if(data.message.includes('giriş')) setTimeout(() => { window.location.href = '/customer_login'; }, 1500);
        }
    })
    .catch(error => console.error('AJAX Hatası:', error));
}


// ----------------------------------------------------
// 3. FAVORİ EKLE/ÇIKAR
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    const favBtn = document.getElementById('fav-btn');
    
    if (favBtn) {
        favBtn.addEventListener('click', function() {
            const restaurantId = this.getAttribute('data-id');
            const svg = this.querySelector('.heart-svg');
            
            this.classList.remove('heart-animate');
            void this.offsetWidth; 
            this.classList.add('heart-animate');

            fetch('/api/toggle_favorite', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ restaurant_id: restaurantId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.action === 'added') {
                        svg.setAttribute('fill', '#ef4444');
                        svg.setAttribute('stroke', '#ef4444');
                    } else {
                        svg.setAttribute('fill', 'none');
                        svg.setAttribute('stroke', '#6b7280');
                    }
                } else {
                    if (typeof showToast === "function") showToast(data.message, "error");
                    if(data.message.includes('giriş')) window.location.href = '/customer_login';
                }
            })
            .catch(error => console.error('Favori AJAX Hatası:', error));
        });
    }
});


// ----------------------------------------------------
// 4. RESTORAN CANLI DURUMU (AÇIK/KAPALI)
// ----------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    const dataElement = document.getElementById('live-restaurant-data');
    if (!dataElement) return;

    let isRestaurantOpen = dataElement.getAttribute('data-is-open') === 'true';
    const currentRestaurantId = dataElement.getAttribute('data-restaurant-id');

    setInterval(() => {
        fetch('/api/restaurant_statuses', {
            method: 'POST', headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            body: JSON.stringify({ restaurant_ids: [currentRestaurantId] })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.statuses && data.statuses[currentRestaurantId] !== undefined) {
                const newStatus = data.statuses[currentRestaurantId];
                
                if (newStatus === false && isRestaurantOpen) {
                    isRestaurantOpen = false;
                    document.querySelector('.restaurant-header').classList.add('closed-header');
                    document.querySelectorAll('.menu-item').forEach(item => item.classList.add('closed-menu-item'));
                    document.querySelectorAll('.add-btn').forEach(btn => btn.disabled = true);
                    document.querySelectorAll('.qty-input').forEach(input => input.disabled = true);
                    if (typeof showToast === "function") showToast("Üzgünüz, restoran şu an kapandığı için yeni sipariş alamıyor.", "error");
                } 
                else if (newStatus === true && !isRestaurantOpen) {
                    isRestaurantOpen = true;
                    document.querySelector('.restaurant-header').classList.remove('closed-header');
                    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('closed-menu-item'));
                    document.querySelectorAll('.add-btn').forEach(btn => btn.disabled = false);
                    document.querySelectorAll('.qty-input').forEach(input => input.disabled = false);
                    if (typeof showToast === "function") showToast("Harika! Restoran tekrar sipariş almaya başladı.", "success");
                }
            }
        })
        .catch(err => console.log('Canlı durum kontrolü hatası:', err));
    }, 10000); 
});