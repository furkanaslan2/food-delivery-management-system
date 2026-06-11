document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach((msg) => {
        setTimeout(() => {
            msg.style.display = "none";
        }, 5000);
    });

    const actionButtons = document.querySelector('.action-buttons');
    
    if (!actionButtons) return;

    let selectAllBtn = document.getElementById('select-all-btn');
    if (!selectAllBtn) {
        selectAllBtn = document.createElement('button');
        selectAllBtn.type = "button"; 
        
        selectAllBtn.style.display = 'none'; 
        
        selectAllBtn.className = 'filter-button'; 
        selectAllBtn.id = 'select-all-btn';
        selectAllBtn.style.backgroundColor = '#17a2b8'; 
        selectAllBtn.style.color = 'white';
        
        const sortContainer = actionButtons.querySelector('.sort-container');
        if (sortContainer) {
            sortContainer.insertAdjacentElement('afterend', selectAllBtn);
            selectAllBtn.style.marginLeft = '5px'; 
        } else {
            actionButtons.appendChild(selectAllBtn);
            selectAllBtn.style.marginLeft = '5px'; 
        }

        selectAllBtn.innerHTML = 'Tümünü Seç';
        selectAllBtn.dataset.action = 'select'; 
    }

    function updateSelectAllState() {
        const checkboxes = document.querySelectorAll('.table-card input[type="checkbox"]');
        const total = checkboxes.length;
        
        if (total === 0) return;

        const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

        if (checkedCount > 0) {
            selectAllBtn.style.display = 'inline-flex';
            
            if (checkedCount === total) {
                selectAllBtn.innerText = "Deselect All";
                selectAllBtn.style.backgroundColor = "#6c757d"; 
                selectAllBtn.dataset.action = "deselect";
            } else {
                selectAllBtn.innerText = "Select All";
                selectAllBtn.style.backgroundColor = "#17a2b8"; 
                selectAllBtn.dataset.action = "select";
            }
        } else {
            selectAllBtn.style.display = 'none';
            
            selectAllBtn.innerText = "Select All";
            selectAllBtn.style.backgroundColor = "#17a2b8";
            selectAllBtn.dataset.action = "select";
        }
    }

    document.addEventListener('change', function(e) {
        if (e.target && e.target.matches('.table-card input[type="checkbox"]')) {
            updateSelectAllState();
        }
    });

    selectAllBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        const checkboxes = document.querySelectorAll('.table-card input[type="checkbox"]');
        const isSelectAction = selectAllBtn.dataset.action === 'select';

        checkboxes.forEach(cb => {
            cb.checked = isSelectAction;
        });
        
        updateSelectAllState();

        if (checkboxes.length > 0) {
            checkboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    
    updateSelectAllState();
});

// ==========================================
// 🛡️ SİTE GENELİ ÖZEL ONAY (CONFIRM) MOTORU
// ==========================================
window.showCustomConfirm = function(message, onConfirm) {
    const modal = document.getElementById('global-confirm-modal');
    const msgEl = document.getElementById('global-confirm-message');
    const btnOk = document.getElementById('global-confirm-ok');
    const btnCancel = document.getElementById('global-confirm-cancel');

    if (!modal) return window.confirm(message); // Eğer HTML unutulursa varsayılanı kullan (Güvenlik)

    msgEl.innerText = message;
    modal.style.display = 'flex';

    // Önceki buton dinleyicilerini temizlemek için butonları kopyalayıp yeniliyoruz
    const newBtnOk = btnOk.cloneNode(true);
    btnOk.parentNode.replaceChild(newBtnOk, btnOk);
    
    const newBtnCancel = btnCancel.cloneNode(true);
    btnCancel.parentNode.replaceChild(newBtnCancel, btnCancel);

    // İptal Butonu
    newBtnCancel.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // Onay (Evet) Butonu
    newBtnOk.addEventListener('click', function() {
        modal.style.display = 'none';
        if (onConfirm) onConfirm(); // İşlemi çalıştır!
    });
};

// Form Silme İşlemleri İçin Kısa Yol Fonksiyonu
window.confirmFormSubmit = function(event, formElement, message) {
    event.preventDefault(); // Tıklanır tıklanmaz sayfanın yenilenmesini durdur
    
    // Özel modalı çağır, kullanıcı "Evet" derse formu kod ile gönder (submit)
    window.showCustomConfirm(message, function() {
        formElement.submit(); 
    });
};

// ==========================================
// 🍞 SİTE GENELİ AKILLI TOAST BİLDİRİM SİSTEMİ (DARK PREMIUM VERSİYON)
// ==========================================
window.showToast = function(message, type = 'success') {
    // 1. Container Yoksa Yarat
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 99999; display: flex; flex-direction: column-reverse; gap: 12px;';
        document.body.appendChild(container);
    }

    // 2. CSS Animasyonlarını HTML'e Enjekte Et
    if (!document.getElementById('toast-premium-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-premium-styles';
        style.innerHTML = `
            @keyframes shrinkBar { from { width: 100%; } to { width: 0%; } }
            @keyframes iconBounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
        `;
        document.head.appendChild(style);
    }

    // 3. Duruma Göre Renk, İkon ve Başlıkları Belirle
    const isSuccess = (type === 'success');
    const themeColor = isSuccess ? '#10b981' : '#ef4444'; 
    const iconClass = isSuccess ? 'ph-fill ph-check-circle' : 'ph-fill ph-warning-circle';
    const titleText = isSuccess ? 'Harika! 🎉' : 'Bir Sorun Var 😔';

    // 4. Toast HTML Elementini İnşa Et (DARK MODE UYARLI)
    const toast = document.createElement('div');
    toast.style.cssText = `
        background: #111827; /* 🌙 JİLET GİBİ GECE MAVİSİ/SİYAH ARKA PLAN */
        width: 320px;
        border-radius: 16px;
        box-shadow: 0 20px 40px -5px rgba(0,0,0,0.4), 0 8px 10px -6px rgba(0,0,0,0.2); /* Gölgeyi koyulaştırdık */
        display: flex;
        flex-direction: column;
        overflow: hidden;
        opacity: 0;
        transform: translateX(120%);
        transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        border: 1px solid #374151; /* İncecik antrasit bir çerçeve */
        border-left: 6px solid ${themeColor}; 
    `;
    
    toast.innerHTML = `
        <div style="padding: 16px 20px; display: flex; align-items: flex-start; gap: 14px;">
            <div style="font-size: 26px; color: ${themeColor}; animation: iconBounce 2s infinite ease-in-out;">
                <i class="${iconClass}"></i>
            </div>
            <div style="flex: 1; margin-top: 2px;">
                <div style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 15px; color: #f9fafb; margin-bottom: 4px; letter-spacing: -0.3px;">
                    ${titleText}
                </div>
                <div style="font-family: 'Inter', sans-serif; font-weight: 500; font-size: 13.5px; color: #9ca3af; line-height: 1.4;">
                    ${message}
                </div>
            </div>
            <div style="cursor: pointer; color: #6b7280; font-size: 18px; transition: 0.2s;" onclick="this.closest('div').parentElement.style.display='none'" onmouseover="this.style.color='#f9fafb'" onmouseout="this.style.color='#6b7280'">
                <i class="ph-bold ph-x"></i>
            </div>
        </div>
        <div style="height: 4px; background: #374151; width: 100%;">
            <div style="height: 100%; background: ${themeColor}; width: 100%; animation: shrinkBar 3s linear forwards;"></div>
        </div>
    `;

    container.appendChild(toast);

    // 5. Giriş Çıkış Animasyonları
    setTimeout(() => { toast.style.opacity = '1'; toast.style.transform = 'translateX(0)'; }, 10);
    setTimeout(() => { 
        toast.style.opacity = '0'; 
        toast.style.transform = 'translateX(100%)'; 
        setTimeout(() => toast.remove(), 400); 
    }, 3000);
};

// ==========================================
// 🚀 FLASK "FLASH" MESAJLARINI OTOMATİK YAKALAYICI
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const flashElements = document.querySelectorAll('.flash-message-data');
    flashElements.forEach((el, index) => {
        let msgType = el.getAttribute('data-category'); 
        let msgText = el.getAttribute('data-message');
        if (msgType === 'danger' || msgType === 'warning') msgType = 'error';
        
        // Bildirimlerin şelale gibi sırayla kayarak gelmesi için gecikme (delay) ekliyoruz
        setTimeout(() => { 
            window.showToast(msgText, msgType); 
            el.remove(); // İşlem bitince HTML'i temizle
        }, 100 + (index * 150)); 
    });
});