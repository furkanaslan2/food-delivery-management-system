// ==========================================
// 📦 SİPARİŞ DETAY MODALI VE API İSTEĞİ
// ==========================================
function showOrderDetails(event, orderId) {
    event.preventDefault();
    
    document.getElementById('detailModal').style.display = 'flex';
    document.getElementById('modal-items').innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px; color: #6b7280;">Yükleniyor...</td></tr>';
    document.getElementById('grand-total').innerText = '$0.00';

    fetch(`/order_details/${orderId}`)
        .then(response => response.json())
        .then(data => {
            let itemsHtml = '';
            let grandTotal = 0;

            if(data.error) {
                if(typeof window.showToast === 'function') window.showToast(data.error, "error");
                itemsHtml = `<tr><td colspan="4" style="text-align:center; color:red; padding: 20px;">Hata: ${data.error}</td></tr>`;
            } else if(data.length === 0) {
                itemsHtml = '<tr><td colspan="4" style="text-align:center; padding: 20px; color: #6b7280;">Bu siparişe ait ürün bulunamadı.</td></tr>';
            } else {
                data.forEach(item => {
                    let total = item.quantity * parseFloat(item.unit_price);
                    grandTotal += total;
                    itemsHtml += `
                        <tr style="border-bottom: 1px solid #e5e7eb;">
                            <td style="padding: 12px; font-weight: 600; color: #111827;">${item.item_name}</td>
                            <td style="padding: 12px;">${item.quantity}</td>
                            <td style="padding: 12px;">$${parseFloat(item.unit_price).toFixed(2)}</td>
                            <td style="padding: 12px; font-weight: 600; color: #059669;">$${total.toFixed(2)}</td>
                        </tr>
                    `;
                });
            }
            
            document.getElementById('modal-items').innerHTML = itemsHtml;
            document.getElementById('grand-total').innerText = '$' + grandTotal.toFixed(2);
        })
        .catch(err => {
            if(typeof window.showToast === 'function') window.showToast("Sipariş detayları alınırken bağlantı hatası oluştu.", "error");
            document.getElementById('modal-items').innerHTML = '<tr><td colspan="4" style="text-align:center; color:red; padding: 20px;">Bağlantı hatası!</td></tr>';
        });
}

// ==========================================
// ✏️ SİPARİŞ EKLE/DÜZENLE MODALI
// ==========================================
function openOrderModal(isUpdate = false, btn = null) {
    document.getElementById('orderFormModal').style.display = 'flex';
    
    if (isUpdate && btn) {
        document.getElementById('orderModalTitle').innerText = 'Siparişi Düzenle';
        document.getElementById('modal-add-btn').style.display = 'none';
        document.getElementById('modal-update-btn').style.display = 'block';
        document.getElementById('update-only-fields').style.display = 'flex';
        document.getElementById('food-section').style.display = 'none';
        
        document.getElementById('update-order-id').value = btn.getAttribute('data-id');
        document.getElementById('order-status').value = btn.getAttribute('data-status');
        
        const dateVal = btn.getAttribute('data-date');
        if(dateVal) document.getElementById('order-date').value = dateVal;
        
        document.getElementById('order-type').value = btn.getAttribute('data-type');
        document.getElementById('order-table-no').value = btn.getAttribute('data-table');
        document.getElementById('customer-name').value = btn.getAttribute('data-customer-name');
        document.getElementById('customer-phone').value = btn.getAttribute('data-customer-phone');
        document.getElementById('customer-address').value = btn.getAttribute('data-customer-address');
        document.getElementById('dynamic-courier-list').value = btn.getAttribute('data-courier');
        
        toggleOrderFields();
    } else {
        document.getElementById('orderModalTitle').innerText = 'Yeni Sipariş Ekle';
        document.getElementById('modal-add-btn').style.display = 'block';
        document.getElementById('modal-update-btn').style.display = 'none';
        document.getElementById('update-only-fields').style.display = 'none';
        document.getElementById('food-section').style.display = 'block';
        
        document.getElementById('order-form').reset();
        document.getElementById('update-order-id').value = '';
        
        document.getElementById('dine-in-fields').style.display = 'none';
        document.getElementById('delivery-fields').style.display = 'none';
    }
}

function closeOrderModal() { document.getElementById('orderFormModal').style.display = 'none'; }
function closeModal() { document.getElementById('detailModal').style.display = 'none'; }

function toggleOrderFields() {
    const type = document.getElementById('order-type').value;
    document.getElementById('dine-in-fields').style.display = (type === 'Dine-in') ? 'block' : 'none';
    document.getElementById('delivery-fields').style.display = (type === 'Delivery') ? 'block' : 'none';
}

function addFoodRow() {
    const container = document.getElementById('food-items-container');
    const firstRow = container.querySelector('.food-row');
    if (firstRow) {
        const newRow = firstRow.cloneNode(true);
        newRow.querySelector('input').value = 1; 
        container.appendChild(newRow);
    }
}

// ==========================================
// 🛵 KURYE ATAMA MODALI (HTML'DEN TAŞINDI)
// ==========================================
function openCourierModal(orderId) {
    const inputEl = document.getElementById('courier-modal-order-id');
    const displayEl = document.getElementById('modal-display-order-id');
    const modalEl = document.getElementById('courierAssignModal');
    
    if (inputEl) inputEl.value = orderId;
    if (displayEl) displayEl.innerText = "#" + orderId;
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