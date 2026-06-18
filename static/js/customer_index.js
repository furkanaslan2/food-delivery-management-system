document.addEventListener("DOMContentLoaded", function() {
    
    // ==========================================
    // 1. KATEGORİ FİLTRELEME (TEK KAYNAK MİMARİSİ)
    // ==========================================
    const catBtns = document.querySelectorAll('.cat-btn');
    const filterForm = document.getElementById('sidebar-filter-form');

    catBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault(); 
            const filterValue = this.getAttribute('data-filter');
            
            if(filterForm) {
                // Üstten tıklanana karşılık gelen sol menüdeki radio butonunu bul
                const radioToSelect = filterForm.querySelector(`input[name="cuisine"][value="${filterValue}"]`);
                if(radioToSelect) {
                    radioToSelect.checked = true;
                    // Yandaki formu sunucuya gönder (Sayfa yenilenip filtrelenmiş gelecek)
                    filterForm.submit(); 
                }
            }
        });
    });

    // ==========================================
    // 2. ANA SAYFA FAVORİ BUTONLARI
    // ==========================================
    const favBtns = document.querySelectorAll('.main-page-fav-btn');
    favBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Kartın içine girilmesini engeller
            
            const restaurantId = this.getAttribute('data-id');
            const svg = this.querySelector('.heart-svg');

            fetch('/api/toggle_favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
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
                    if (typeof window.showToast === "function") window.showToast(data.message, "error");
                    if(data.message.includes('giriş')) window.location.href = '/customer_login';
                }
            })
            .catch(error => console.error('Favori Hatası:', error));
        });
    });

    // ==========================================
    // 3. CANLI SİPARİŞ TAKİBİ (DÖNGÜ)
    // ==========================================
    checkOrderStatus();
    setInterval(checkOrderStatus, 5000);
});

// ==========================================
// 🚀 SİPARİŞ TAKİP FONKSİYONLARI (BANNER)
// ==========================================
let lastOrderStatus = null;

function checkOrderStatus() {
    fetch('api/active_order_status')
    .then(res => res.json())
    .then(data => {
        const banner = document.getElementById('live-order-banner');
        if (!banner) return;

        if (data.has_active_order) {
            banner.style.display = 'block';
            const newStatus = data.order_status;
            const orderId = data.order_id;
            
            const titleEl = document.getElementById('tracker-title');
            const descEl = document.getElementById('tracker-desc');
            const iconEl = document.getElementById('tracker-icon');
            const accent = document.getElementById('tracker-accent');
            
            const trackBtn = document.getElementById('live-track-btn');
            const cancelBtn = document.getElementById('live-cancel-btn');
            
            const step1 = document.getElementById('step-1');
            const step2 = document.getElementById('step-2');
            const step3 = document.getElementById('step-3');

            trackBtn.setAttribute('data-id', orderId);
            trackBtn.onclick = function() { openTrackModal(orderId); }; 
            cancelBtn.onclick = function() { openCancelModal(orderId); };

            if (newStatus !== lastOrderStatus) {
                lastOrderStatus = newStatus;

                if(newStatus === 'pending') {
                    titleEl.innerText = 'Restoran Onayı Bekleniyor';
                    descEl.innerText = 'Siparişiniz restorana iletildi, onaylanması bekleniyor.';
                    iconEl.innerHTML = '<i class="ph-bold ph-clock" style="color: #f59e0b;"></i>';
                    iconEl.style.background = '#fffbeb';
                    accent.style.backgroundColor = '#f59e0b';
                    cancelBtn.style.display = 'flex';
                    trackBtn.style.display = 'none';
                    
                    step1.style.background = '#f59e0b';
                    step2.style.background = '#e5e7eb';
                    step3.style.background = '#e5e7eb';
                } 
                else if(newStatus === 'preparing' || newStatus === 'ready') {
                    titleEl.innerText = 'Siparişiniz Hazırlanıyor';
                    descEl.innerText = 'Restoran siparişinizi özenle hazırlıyor.';
                    iconEl.innerHTML = '<i class="ph-bold ph-cooking-pot" style="color: #3b82f6;"></i>';
                    iconEl.style.background = '#eff6ff';
                    accent.style.backgroundColor = '#3b82f6';
                    cancelBtn.style.display = 'none';
                    trackBtn.style.display = 'none';
                    
                    step1.style.background = '#3b82f6';
                    step2.style.background = '#3b82f6';
                    step3.style.background = '#e5e7eb';
                }
                else if(newStatus === 'on_the_way') {
                    titleEl.innerText = 'Kurye Yolda!';
                    descEl.innerText = 'Siparişiniz yola çıktı, haritadan canlı takip edebilirsiniz.';
                    iconEl.innerHTML = '<i class="ph-bold ph-moped" style="color: #10b981;"></i>';
                    iconEl.style.background = '#ecfdf5';
                    accent.style.backgroundColor = '#10b981';
                    cancelBtn.style.display = 'none';
                    trackBtn.style.display = 'flex';
                    
                    step1.style.background = '#10b981';
                    step2.style.background = '#10b981';
                    step3.style.background = '#10b981';
                }
            }
        } else {
            banner.style.display = 'none';
            if (lastOrderStatus === 'on_the_way') {
                if(typeof window.showToast === 'function') window.showToast("Siparişiniz teslim edildi! Afiyet olsun.", "success");
                setTimeout(() => { window.location.reload(); }, 3000);
            }
            lastOrderStatus = null;
        }
    })
    .catch(err => console.error("Takip Hatası:", err));
}

// ==========================================
// 🛵 KURYE CANLI TAKİP HARİTASI (LEAFLET)
// ==========================================
let trackMap = null;
let courierMarker = null;
let restMarker = null; // 🔥 KAYIP: Restoran Pini Geri Döndü
let custMarker = null; // 🔥 KAYIP: Ev (Müşteri) Pini Geri Döndü
let trackingInterval = null;

function openTrackModal(orderId) {
    const modal = document.getElementById('courierTrackModal');
    if (modal) modal.style.display = 'flex';
    
    setTimeout(() => {
        initTrackMap();
        fetchCourierLocation(orderId);
        
        trackingInterval = setInterval(() => {
            fetchCourierLocation(orderId);
        }, 5000);
    }, 300);
}

function closeTrackModal() {
    const modal = document.getElementById('courierTrackModal');
    if (modal) modal.style.display = 'none';
    
    if (trackingInterval) {
        clearInterval(trackingInterval);
        trackingInterval = null;
    }
}

function initTrackMap() {
    const mapEl = document.getElementById('live-tracking-map');
    if (!mapEl) return; 

    if (!trackMap) {
        trackMap = L.map('live-tracking-map').setView([41.0082, 28.9784], 13);
        // Eski şık (Voyager) harita temasını geri getirdik
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap & CARTO'
        }).addTo(trackMap);
    } else {
        trackMap.invalidateSize();
    }
}

function fetchCourierLocation(orderId) {
    fetch('/api/get_courier_location', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order_id: orderId})
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.lat && data.lon) {
            const courierLatLng = new L.LatLng(data.lat, data.lon);
            
            // 🔥 KAYIP: İkon Tasarımları Geri Döndü
            const courierIcon = L.divIcon({ html: '<div style="background:#10b981; color:white; width:36px; height:36px; border-radius:50%; display:flex; justify-content:center; align-items:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); border:2px solid white;"><i class="ph-bold ph-moped" style="font-size:20px;"></i></div>', className: '', iconSize: [40, 40], iconAnchor: [20, 20], popupAnchor: [0, -20] });
            const restIcon = L.divIcon({ html: '<div style="background:#4f46e5; color:white; width:32px; height:32px; border-radius:50%; display:flex; justify-content:center; align-items:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); border:2px solid white;"><i class="ph-bold ph-storefront" style="font-size:16px;"></i></div>', className: '', iconSize: [36, 36], iconAnchor: [18, 18], popupAnchor: [0, -18] });
            const homeIcon = L.divIcon({ html: '<div style="background:#f59e0b; color:white; width:32px; height:32px; border-radius:50%; display:flex; justify-content:center; align-items:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); border:2px solid white;"><i class="ph-bold ph-house" style="font-size:16px;"></i></div>', className: '', iconSize: [36, 36], iconAnchor: [18, 18], popupAnchor: [0, -18] });

            // Restoran ve Ev Pinlerini haritaya ekle (Eğer yoklarsa)
            if (!restMarker && data.rest_lat && data.rest_lon) { 
                restMarker = L.marker([data.rest_lat, data.rest_lon], {icon: restIcon}).addTo(trackMap); 
                restMarker.bindPopup(`<b>${data.rest_name}</b><br>Siparişi Hazırlayan`); 
            }
            if (!custMarker && data.cust_lat && data.cust_lon) { 
                custMarker = L.marker([data.cust_lat, data.cust_lon], {icon: homeIcon}).addTo(trackMap); 
                custMarker.bindPopup(`<b>Teslimat Adresiniz</b>`); 
            }
            
            // Kurye Pini ve Otomatik Odaklama (fitBounds) mantığı
            if (!courierMarker) {
                courierMarker = L.marker(courierLatLng, {icon: courierIcon}).addTo(trackMap); 
                courierMarker.bindPopup(`<b>${data.name}</b><br>Size doğru geliyor!`).openPopup();
                
                // 🔥 KAYIP: İlk açılışta 3 pini birden ekrana sığdıracak şekilde kamerayı ayarla!
                const group = new L.featureGroup([restMarker, custMarker, courierMarker].filter(Boolean)); 
                trackMap.fitBounds(group.getBounds(), {padding: [40, 40]});
            } else { 
                // Kurye zaten varsa sadece yerini yumuşakça güncelle
                courierMarker.setLatLng(courierLatLng); 
                // Kuryeyi takip etmesi için kamerayı kaydır
                trackMap.flyTo(courierLatLng, 16, { animate: true, duration: 1.5 });
            }

            // 🔥 KAYIP: Sipariş Teslim Edilince Çalışan UI Animasyonları Geri Döndü!
            if (data.order_status === 'delivered') {
                clearInterval(trackingInterval);
                document.getElementById('modal-progress-line').style.width = '100%';
                document.getElementById('modal-step-2').style.animation = 'none';
                document.getElementById('modal-step-2').style.boxShadow = 'none';
                document.getElementById('modal-text-2').style.color = '#374151';
                
                const step3 = document.getElementById('modal-step-3'); 
                if(step3) {
                    step3.style.background = '#10b981'; 
                    step3.style.color = 'white'; 
                    step3.style.borderColor = '#10b981'; 
                    step3.innerHTML = '<i class="ph-bold ph-check"></i>';
                }
                
                const text3 = document.getElementById('modal-text-3');
                if(text3) text3.style.color = '#10b981';
                
                const title = document.getElementById('track-modal-title');
                if(title) title.innerText = 'Sipariş Teslim Edildi! Afiyet olsun.';
                
                setTimeout(() => { closeTrackModal(); window.location.reload(); }, 4000);
            }
        }
    })
    .catch(err => console.error("Kurye konumu çekilirken hata:", err));
}

function openCancelModal(orderId) {
    document.getElementById('cancelConfirmModal').style.display = 'flex';
    document.getElementById('btn-cancel-yes').onclick = function() {
        cancelOrderAjax(orderId);
    };
    document.getElementById('btn-cancel-no').onclick = function() {
        document.getElementById('cancelConfirmModal').style.display = 'none';
    };
}

function cancelOrderAjax(orderId) {
    const btn = document.getElementById('btn-cancel-yes');
    const originalText = btn.innerHTML;
    btn.innerHTML = "İptal Ediliyor...";
    btn.disabled = true;

    fetch('/api/cancel_order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            window.location.reload();
        } else {
            if(typeof window.showToast === 'function') window.showToast(data.message, "error");
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    })
    .catch(err => {
        console.error(err);
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    const chatBox = document.getElementById('chat-messages');
    
    chatBox.innerHTML += `
        <div style="align-self: flex-end; background: #4f46e5; color: white; padding: 12px 16px; border-radius: 16px 16px 4px 16px; font-size: 14px; max-width: 85%; line-height: 1.5; box-shadow: 0 2px 5px rgba(79, 70, 229, 0.2);">
            ${message}
        </div>
    `;
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    const loadingId = 'loading-' + Date.now();
    chatBox.innerHTML += `
        <div id="${loadingId}" style="align-self: flex-start; background: white; padding: 12px 16px; border-radius: 16px 16px 16px 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); font-size: 14px; color: #6b7280; border: 1px solid #f3f4f6;">
            <i class="ph-bold ph-spinner ph-spin"></i> Düşünüyor...
        </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    fetch('/api/ask_ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById(loadingId).remove();
        if (data.success) {
            chatBox.innerHTML += `
                <div style="align-self: flex-start; background: white; padding: 12px 16px; border-radius: 16px 16px 16px 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); font-size: 14px; color: #374151; max-width: 85%; border: 1px solid #f3f4f6; line-height: 1.5;">
                    ${data.response.replace(/\n/g, '<br>')}
                </div>
            `;

            if (data.action_taken === 'cart_updated') {
                let badge = document.getElementById('nav-cart-badge');
                if (badge) {
                    badge.innerText = data.total_cart_qty;
                    badge.style.display = data.total_cart_qty > 0 ? 'flex' : 'none';
                }
                
                let priceTag = document.getElementById('nav-cart-total');
                if (priceTag) {
                    priceTag.setAttribute('data-total', data.total_cart_price);
                    priceTag.innerText = '₺' + parseFloat(data.total_cart_price).toFixed(2);
                    priceTag.style.display = data.total_cart_price > 0 ? 'inline-block' : 'none';
                    
                    priceTag.style.transform = 'scale(1.15)';
                    setTimeout(() => { priceTag.style.transform = 'scale(1)'; }, 200);
                }
            }

        } else {
            chatBox.innerHTML += `
                <div style="align-self: flex-start; background: #fee2e2; color: #dc2626; padding: 12px 16px; border-radius: 16px 16px 16px 4px; font-size: 14px;">
                    ${data.message}
                </div>
            `;
        }
        chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(err => {
        document.getElementById(loadingId).remove();
        console.error('Chat hatası:', err);
    });
}

// ==========================================
// 🤖 YAPAY ZEKA GURME ASİSTAN KONTROLLERİ
// ==========================================
function toggleChat() {
    const chatWindow = document.getElementById('ai-chat-window');
    const badge = document.getElementById('ai-fab-badge');
    const icon = document.getElementById('ai-fab-icon');
    
    // Eğer kapalıysa aç
    if (chatWindow.style.display === 'none' || chatWindow.style.display === '') {
        chatWindow.style.display = 'flex';
        // 🚀 Açıldığında rozeti gizle, ikonu robota çevir
        if(badge) badge.style.display = 'none';
        if(icon) icon.className = 'ph-bold ph-robot';
    } else {
        // Zaten açıksa ana butona tıklandığında "Minimize" et
        minimizeChat();
    }
}

function minimizeChat() {
    // Sadece pencereyi gizler, hafızayı veya yazışmaları SİLMEZ (Aşağı Ok işlemi)
    document.getElementById('ai-chat-window').style.display = 'none';
    
    // 🚀 YENİ: Küçültüldüğünde aktif sohbet olduğunu belirt!
    const badge = document.getElementById('ai-fab-badge');
    const icon = document.getElementById('ai-fab-icon');
    if(badge) badge.style.display = 'block';
    if(icon) icon.className = 'ph-bold ph-chats'; // İkonu konuşma balonuna çevir
}

function promptCloseChat() {
    document.getElementById('ai-close-confirm').style.display = 'flex';
}

function cancelCloseChat() {
    document.getElementById('ai-close-confirm').style.display = 'none';
}

function confirmCloseChat() {
    const chatBox = document.getElementById('chat-messages');
    const confirmOverlay = document.getElementById('ai-close-confirm');
    const chatWindow = document.getElementById('ai-chat-window');
    
    confirmOverlay.innerHTML = '<div style="color: #4f46e5; font-size: 30px;"><i class="ph-bold ph-spinner ph-spin"></i></div><h4 style="margin-top:15px; color:#111827;">Sohbet Temizleniyor...</h4>';
    
    fetch('/api/ask_ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '/reset_memory' })
    })
    .then(res => res.json())
    .then(data => {
        chatBox.innerHTML = `
            <div style="align-self: flex-start; background: white; padding: 12px 16px; border-radius: 16px 16px 16px 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); font-size: 14px; color: #374151; max-width: 85%; border: 1px solid #f3f4f6; line-height: 1.5;">
                Merhaba! Ben Gurme Asistan. <i class="ph-fill ph-cooking-pot"></i><br>Bugün canın ne çekiyor? Sana en uygun restoranları ve yemekleri hemen bulabilirim!
            </div>
        `;
        
        confirmOverlay.innerHTML = `
            <div style="width: 60px; height: 60px; background: #fee2e2; color: #dc2626; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; margin-bottom: 15px;"><i class="ph-bold ph-warning-circle"></i></div>
            <h4 style="margin: 0 0 10px 0; color: #111827; font-size: 18px; font-weight: 800;">Sohbeti Sonlandır</h4>
            <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 14px; font-weight: 500; line-height: 1.5;">Sohbeti kapatırsanız asistan önceki konuştuklarınızı ve seçimlerinizi unutacaktır. Emin misiniz?</p>
            <div style="display: flex; gap: 10px; width: 100%;">
                <button onclick="cancelCloseChat()" style="flex: 1; background: #f3f4f6; color: #374151; border: none; padding: 12px; border-radius: 12px; font-weight: 700; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'">Vazgeç</button>
                <button onclick="confirmCloseChat()" style="flex: 1; background: #ef4444; color: white; border: none; padding: 12px; border-radius: 12px; font-weight: 700; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">Evet, Kapat</button>
            </div>
        `;
        
        confirmOverlay.style.display = 'none';
        chatWindow.style.display = 'none';
        
        // 🚀 YENİ: İkonu fabrika ayarlarına (Robot) döndür ve rozeti kapat
        const badge = document.getElementById('ai-fab-badge');
        const icon = document.getElementById('ai-fab-icon');
        if(badge) badge.style.display = 'none';
        if(icon) icon.className = 'ph-bold ph-robot';
    })
    .catch(err => console.error("Hafıza temizleme hatası:", err));
}

// ==========================================
// 📍 ADRES VE HARİTA (LEAFLET)
// ==========================================
let map = null;
let marker = null;
let gpsControl = null; // YENİ (Geri getirildi)
let selectedLat = null; // YENİ (Geri getirildi)
let selectedLon = null; // YENİ (Geri getirildi)
let editingAddressId = null; // YENİ (Geri getirildi)

// Adresleri düzenlerken formda göstermek için global değişkende tutacağız
window.globalAddresses = [];

function openAddressModal() {
    document.getElementById('addressListModal').style.display = 'flex';
    
    const container = document.getElementById('addresses-container');
    container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="ph-bold ph-spinner ph-spin" style="font-size: 24px;"></i> Yükleniyor...</div>';
    
    // Sunucudan müşterinin adreslerini çekiyoruz
    fetch('/api/get_addresses')
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            window.globalAddresses = data.addresses; 
            
            container.innerHTML = '';
            if (data.addresses.length === 0) {
                container.innerHTML = '<div style="text-align:center; color:#6b7280; padding:15px; font-weight: 500;">Henüz kayıtlı bir adresiniz yok.</div>';
                return;
            }
            
            data.addresses.forEach(addr => {
                const isActive = addr.is_active ? 'border-color: #4f46e5; background: #eef2ff;' : 'border-color: #e5e7eb; background: white;';
                const activeIcon = addr.is_active ? '<i class="ph-fill ph-check-circle" style="color: #4f46e5; font-size: 28px;"></i>' : '<i class="ph-bold ph-circle" style="color:#d1d5db; font-size:28px;"></i>';
                
                container.innerHTML += `
                    <div style="border: 2px solid; ${isActive} border-radius: 12px; padding: 15px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: 0.2s;" onclick="selectAddress(${addr.address_id})">
                        <div>
                            <div style="font-weight: 800; color: #111827; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                                <i class="ph-bold ph-map-pin" style="color: #4f46e5;"></i> ${addr.title}
                            </div>
                            <div style="font-size: 13px; color: #4b5563; line-height: 1.4;">
                                ${addr.neighborhood} Mah. ${addr.street} Sok. No: ${addr.building_no}
                                ${addr.floor_no ? 'Kat: ' + addr.floor_no : ''} ${addr.apt_no ? 'Daire: ' + addr.apt_no : ''}<br>
                                <strong>${addr.district} / ${addr.city}</strong>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:12px;">
                            <button onclick="startEditingAddress(event, ${addr.address_id})" style="background:#f3f4f6; border:1px solid #d1d5db; border-radius:8px; padding:6px 10px; font-size:18px; cursor:pointer; transition:0.2s; color:#4b5563; display: flex; align-items: center; justify-content: center;" onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'" title="Adresi Düzenle">
                                <i class="ph-bold ph-pencil-simple"></i>
                            </button>
                            ${activeIcon}
                        </div>
                    </div>
                `;
            });
        } else {
            container.innerHTML = `<div style="text-align:center; color:#ef4444; padding:15px;">${data.message}</div>`;
        }
    })
    .catch(err => {
        console.error(err);
        container.innerHTML = '<div style="text-align:center; color:#ef4444; padding:15px;">Adresler yüklenirken bir hata oluştu.</div>';
    });
}

function closeAddressModal() {
    document.getElementById('addressListModal').style.display = 'none';
}

// 🔥 KAYIP: Adres Seçme (Aktif yapma) Fonksiyonu Geri Döndü
function selectAddress(addressId) {
    fetch('/api/select_address', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address_id: addressId })
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            window.location.reload(); 
        } else {
            if(typeof window.showToast === 'function') window.showToast(data.message, "error");
        }
    });
}

// 🔥 KAYIP: Haritada GPS (Mevcut Konum) Butonu Geri Döndü
function addGpsButtonToMap() {
    if(gpsControl) return; 
    gpsControl = L.control({position: 'topleft'});
    gpsControl.onAdd = function(map) {
        let btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control');
        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#374151" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top:3px;"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><circle cx="12" cy="12" r="8"></circle></svg>';
        btn.style.backgroundColor = 'white'; btn.style.width = '34px'; btn.style.height = '34px'; btn.style.cursor = 'pointer'; btn.style.display = 'flex'; btn.style.justifyContent = 'center'; btn.style.alignItems = 'center'; btn.title = "Mevcut Konumumu Bul";
        
        btn.onclick = function(e) {
            e.preventDefault(); e.stopPropagation();
            if(navigator.geolocation) {
                btn.style.opacity = '0.5'; 
                navigator.geolocation.getCurrentPosition(function(pos) {
                    let lat = pos.coords.latitude; let lon = pos.coords.longitude;
                    map.setView([lat, lon], 16); marker.setLatLng([lat, lon]); btn.style.opacity = '1';
                }, function() { 
                    if(typeof window.showToast === 'function') window.showToast("Konum alınamadı. Tarayıcı izinlerini kontrol edin.", "error"); 
                    btn.style.opacity = '1'; 
                });
            } else { 
                if(typeof window.showToast === 'function') window.showToast("Tarayıcınız konum özelliğini desteklemiyor.", "error"); 
            }
        };
        return btn;
    };
    gpsControl.addTo(map);
}

function openNewAddressModal() {
    editingAddressId = null; 
    
    document.getElementById('map-modal-title').innerText = "Yeni Harita Konumu Seçin";
    document.getElementById('form-modal-title').innerText = "Yeni Adres Ekle";
    document.getElementById('form-submit-btn').innerText = "Adresi Kaydet ve Kullan";
    
    document.querySelectorAll('#addressFormModal input[type="text"], #addressFormModal textarea').forEach(el => el.value = '');
    if (window.addrPhoneMask) {
        window.addrPhoneMask.unmaskedValue = ''; 
    } else {
        document.getElementById('addr-cphone').value = '';
    }
    
    document.getElementById('addressListModal').style.display = 'none';
    document.getElementById('addressMapModal').style.display = 'flex';
    
    setTimeout(() => { 
        if (!map) {
            map = L.map('address-picker-map').setView([41.0082, 28.9784], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            marker = L.marker([41.0082, 28.9784], {draggable: true}).addTo(map);
            
            map.on('click', function(e) { marker.setLatLng(e.latlng); });
            addGpsButtonToMap(); 
        } else {
            map.invalidateSize(); 
        }
        
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(position => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                map.setView([lat, lon], 15);
                marker.setLatLng([lat, lon]);
            });
        }
    }, 300);
}

function startEditingAddress(event, id) {
    event.stopPropagation(); 
    editingAddressId = id; 
    
    const addr = window.globalAddresses.find(a => a.address_id === id);
    if(!addr) return;
    
    document.getElementById('map-modal-title').innerText = "Konumu Güncelleyin";
    document.getElementById('form-modal-title').innerText = "Adresi Düzenle";
    document.getElementById('form-submit-btn').innerText = "Değişiklikleri Kaydet";
    
    document.getElementById('addr-title').value = addr.title; 
    document.getElementById('addr-city').value = addr.city; 
    document.getElementById('addr-district').value = addr.district; 
    document.getElementById('addr-neighborhood').value = addr.neighborhood; 
    document.getElementById('addr-street').value = addr.street; 
    document.getElementById('addr-building').value = addr.building_no; 
    document.getElementById('addr-floor').value = addr.floor_no || ''; 
    document.getElementById('addr-apt').value = addr.apt_no || ''; 
    document.getElementById('addr-directions').value = addr.directions || ''; 
    document.getElementById('addr-cname').value = addr.contact_name || ''; 
    
    if (window.addrPhoneMask) {
        window.addrPhoneMask.unmaskedValue = addr.contact_phone || '';
    } else {
        document.getElementById('addr-cphone').value = addr.contact_phone || '';
    }
    
    selectedLat = addr.latitude; 
    selectedLon = addr.longitude;
    
    closeAddressModal(); 
    document.getElementById('addressMapModal').style.display = 'flex';
    
    setTimeout(() => {
        if (!map) {
            map = L.map('address-picker-map').setView([selectedLat, selectedLon], 16);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            marker = L.marker([selectedLat, selectedLon], {draggable: true}).addTo(map);
            map.on('click', function(e) { marker.setLatLng(e.latlng); });
            addGpsButtonToMap(); 
        } else {
            map.setView([selectedLat, selectedLon], 16); 
            marker.setLatLng([selectedLat, selectedLon]); 
            map.invalidateSize();
        }
    }, 300);
}

function confirmMapLocation() {
    const pos = marker.getLatLng();
    selectedLat = pos.lat;
    selectedLon = pos.lng;
    
    document.getElementById('addr-lat').value = selectedLat;
    document.getElementById('addr-lon').value = selectedLon;
    document.getElementById('addressMapModal').style.display = 'none';
    document.getElementById('addressFormModal').style.display = 'flex';
}

function submitAddressForm() {
    const payload = {
        city: document.getElementById('addr-city').value.trim(),
        district: document.getElementById('addr-district').value.trim(),
        neighborhood: document.getElementById('addr-neighborhood').value.trim(),
        street: document.getElementById('addr-street').value.trim(),
        building_no: document.getElementById('addr-building').value.trim(),
        floor_no: document.getElementById('addr-floor').value.trim(),
        apt_no: document.getElementById('addr-apt').value.trim(),
        directions: document.getElementById('addr-directions').value.trim(),
        title: document.getElementById('addr-title').value.trim(),
        contact_name: document.getElementById('addr-cname').value.trim(),
        contact_phone: document.getElementById('addr-cphone').value.trim(),
        latitude: selectedLat,
        longitude: selectedLon
    };

    // ==========================================
    // 🛡️ ADRES FORMU MASTER KONTROL (AKILLI DOĞRULAMA)
    // ==========================================
    let hasError = false;
    let errorMessage = "";

    const isPhoneEmpty = (payload.contact_phone === '' || payload.contact_phone === '0 (5__) ___ __ __');

    if (!payload.city || !payload.district || !payload.neighborhood || !payload.street || !payload.building_no) {
        hasError = true;
        errorMessage = "Lütfen İl, İlçe, Mahalle, Sokak ve Bina No gibi temel adres detaylarını eksiksiz girin.";
    } else if (!payload.title) {
        hasError = true;
        errorMessage = "Lütfen bu adres için bir başlık belirleyin (Örn: Evim, İş Yerim).";
    } else if (!payload.contact_name) {
        hasError = true;
        errorMessage = "Lütfen teslimat için ad ve soyad bilgisini girin.";
    } else if (isPhoneEmpty || payload.contact_phone.includes('_') || payload.contact_phone.length < 15) {
        hasError = true;
        errorMessage = "Lütfen iletişim numaranızı tam ve eksiksiz girin.";
    }

    if (hasError) {
        if(typeof window.showToast === 'function') {
            window.showToast(errorMessage, "error");
        } else {
            alert(errorMessage);
        }
        return;
    }

    const btn = document.getElementById('form-submit-btn');
    const oldText = btn.innerHTML;
    btn.innerHTML = "Kaydediliyor...";
    btn.disabled = true;

    let apiEndpoint = '/api/add_address';
    if(editingAddressId !== null) { 
        payload.address_id = editingAddressId; 
        apiEndpoint = '/api/update_address'; 
    }

    fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            window.location.reload();
        } else {
            if(typeof window.showToast === 'function') window.showToast(data.message, "error");
            btn.innerHTML = oldText;
            btn.disabled = false;
        }
    })
    .catch(err => {
        console.error(err);
        if(typeof window.showToast === 'function') window.showToast("Bağlantı hatası oluştu.", "error");
        btn.innerHTML = oldText;
        btn.disabled = false;
    });
}

    const filterForm = document.getElementById('sidebar-filter-form');
    if(filterForm) {
        const filterRadios = filterForm.querySelectorAll('.filter-radio');
        filterRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                filterForm.submit();
            });
        });
    }

    const categorySlider = document.querySelector('.category-filters');
    let isDown = false;
    let startX;
    let scrollLeft;
    let isDragging = false; 

    if (categorySlider) {
        categorySlider.addEventListener('mousedown', (e) => {
            isDown = true;
            isDragging = false; 
            categorySlider.style.cursor = 'grabbing';
            startX = e.pageX - categorySlider.offsetLeft;
            scrollLeft = categorySlider.scrollLeft;
        });
        
        categorySlider.addEventListener('mouseleave', () => {
            isDown = false;
            categorySlider.style.cursor = 'grab';
        });
        
        categorySlider.addEventListener('mouseup', () => {
            isDown = false;
            categorySlider.style.cursor = 'grab';
        });
        
        categorySlider.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            
            const x = e.pageX - categorySlider.offsetLeft;
            const walk = (x - startX); 
            
            if (Math.abs(walk) > 3) {
                isDragging = true; 
            }
            
            categorySlider.scrollLeft = scrollLeft - walk;
        });

        categorySlider.addEventListener('click', (e) => {
            if (isDragging) {
                e.preventDefault();
                e.stopPropagation(); 
            }
        }, true); 
    }

document.addEventListener("DOMContentLoaded", function() {
    const restaurantCards = document.querySelectorAll('.restaurant-card');
    if (restaurantCards.length === 0) return;

    const restaurantIds = Array.from(restaurantCards)
        .map(card => card.getAttribute('data-rest-id'))
        .filter(id => id); 

    if (restaurantIds.length === 0) return;

    setInterval(() => {
        fetch('/api/restaurant_statuses', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            body: JSON.stringify({ restaurant_ids: restaurantIds })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.statuses) {
                restaurantCards.forEach(card => {
                    const id = card.getAttribute('data-rest-id');
                    if (!id || data.statuses[id] === undefined) return;
                    
                    const isOpen = data.statuses[id];
                    const isCurrentlyClosed = card.classList.contains('closed-restaurant');
                    const imageContainer = card.querySelector('.card-image');
                    
                    if (!isOpen && !isCurrentlyClosed) {
                        card.classList.add('closed-restaurant');
                        
                        if (imageContainer && !imageContainer.innerHTML.includes('ŞU AN KAPALI')) {
                            const overlay = document.createElement('div');
                            overlay.className = 'live-closed-overlay';
                            overlay.style.cssText = "position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 15; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); transition: opacity 0.3s; opacity: 0;";
                            overlay.innerHTML = '<span style="background: #ef4444; color: white; padding: 10px 20px; border-radius: 10px; font-weight: 800; font-size: 14px; letter-spacing: 0.5px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">ŞU AN KAPALI</span>';
                            
                            imageContainer.appendChild(overlay);
                            
                            requestAnimationFrame(() => {
                                overlay.style.opacity = '1';
                            });
                        }
                    } 
                    else if (isOpen && isCurrentlyClosed) {
                        card.classList.remove('closed-restaurant');
                        
                        if (imageContainer) {
                            Array.from(imageContainer.children).forEach(child => {
                                if (child.innerHTML.includes('ŞU AN KAPALI') || child.classList.contains('live-closed-overlay')) {
                                    child.style.opacity = '0'; // Önce görünmez yap (Fade-out)
                                    setTimeout(() => child.remove(), 300); 
                                }
                            });
                        }
                    }
                });
            }
        })
        .catch(err => console.log('Ana sayfa canlı durum hatası:', err));
    }, 15000); 
});

document.addEventListener("DOMContentLoaded", function() {
    var phoneInput = document.getElementById('addr-cphone');
    if (phoneInput) {
        window.addrPhoneMask = IMask(phoneInput, {
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