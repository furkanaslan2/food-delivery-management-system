// YENİ SİPARİŞ BİLDİRİMİ (API Polling)
document.addEventListener("DOMContentLoaded", function() {
    let maxOrderId = 0;
    document.querySelectorAll('.order-id').forEach(el => {
        let id = parseInt(el.textContent.trim());
        if (!isNaN(id) && id > maxOrderId) maxOrderId = id;
    });

    function checkForNewOrders() {
        fetch(`/api/check_new_orders?last_id=${maxOrderId}`)
            .then(response => response.json())
            .then(data => {
                if (data.new_orders) {
                    const alertBox = document.getElementById('new-order-alert');
                    if (alertBox) alertBox.style.display = 'block';
                    clearInterval(orderPolling); 
                }
            })
            .catch(err => console.error('API Hatası:', err));
    }
    const orderPolling = setInterval(checkForNewOrders, 10000);
});

// SİPARİŞ DETAYLARINI GETİRME (YENİ EKLENDİ)
function showOrderDetails(event, orderId) {
    event.preventDefault();
    
    // Modalı aç ve yükleniyor durumuna getir
    document.getElementById('detailModal').style.display = 'flex';
    document.getElementById('modal-items').innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px; color: #6b7280;">Yükleniyor...</td></tr>';
    document.getElementById('grand-total').innerText = '$0.00';

    // API'den sipariş kalemlerini çek
    fetch(`/order_details/${orderId}`)
        .then(response => response.json())
        .then(data => {
            let itemsHtml = '';
            let grandTotal = 0;

            if(data.error) {
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
            document.getElementById('modal-items').innerHTML = '<tr><td colspan="4" style="text-align:center; color:red; padding: 20px;">Bağlantı hatası!</td></tr>';
        });
}

// SİPARİŞ EKLE/DÜZENLE MODALI
function openOrderModal(isUpdate = false, btn = null) {
    document.getElementById('orderFormModal').style.display = 'flex';
    
    if (isUpdate && btn) {
        document.getElementById('orderModalTitle').innerText = 'Siparişi Düzenle';
        document.getElementById('modal-add-btn').style.display = 'none';
        document.getElementById('modal-update-btn').style.display = 'block';
        
        // GÜNCELLEME MODU: Durum ve Tarih kutularını GÖSTER
        document.getElementById('update-only-fields').style.display = 'flex';
        
        // GÜNCELLEME MODU: Zaten var olan siparişte yeni yemek eklenmez, kafa karışıklığını önlemek için yemek alanını gizle
        document.getElementById('food-section').style.display = 'none';
        
        // BUTONDAN GELEN VERİLERİ FORMA DOLDUR
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
        
        // İlgili kutuları otomatik aç (Dine-in ise masa numarası kutusunu, Delivery ise adres kutularını getirir)
        toggleOrderFields();
        
    } else {
        document.getElementById('orderModalTitle').innerText = 'Yeni Sipariş Ekle';
        document.getElementById('modal-add-btn').style.display = 'block';
        document.getElementById('modal-update-btn').style.display = 'none';
        
        // YENİ EKLEME MODU: Durum ve Tarih kutularını GİZLE
        document.getElementById('update-only-fields').style.display = 'none';
        
        // YENİ EKLEME MODU: Yemek seçim alanını GÖSTER
        document.getElementById('food-section').style.display = 'block';
        
        document.getElementById('order-form').reset();
        document.getElementById('update-order-id').value = '';
        
        document.getElementById('dine-in-fields').style.display = 'none';
        document.getElementById('delivery-fields').style.display = 'none';
    }
}

function closeOrderModal() {
    document.getElementById('orderFormModal').style.display = 'none';
}

// DETAY MODALINI KAPATMA 
function closeModal() {
    document.getElementById('detailModal').style.display = 'none';
}

// FORM İÇİ DİNAMİK ALANLAR (Dine-in / Delivery Geçişi)
function toggleOrderFields() {
    const type = document.getElementById('order-type').value;
    if (type === 'Dine-in') {
        document.getElementById('dine-in-fields').style.display = 'block';
        document.getElementById('delivery-fields').style.display = 'none';
    } else if (type === 'Delivery') {
        document.getElementById('dine-in-fields').style.display = 'none';
        document.getElementById('delivery-fields').style.display = 'block';
    } else {
        document.getElementById('dine-in-fields').style.display = 'none';
        document.getElementById('delivery-fields').style.display = 'none';
    }
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