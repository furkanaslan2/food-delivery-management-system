document.addEventListener("DOMContentLoaded", function() {
    
    // ==========================================
    // 1. KATEGORİ FİLTRELEME
    // ==========================================
    const catBtns = document.querySelectorAll('.cat-btn');
    const restCards = document.querySelectorAll('.filterable-card');

    catBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Aktif buton stilini değiştir
            catBtns.forEach(b => {
                b.classList.remove('active');
                const iconDiv = b.querySelector('div');
                if(iconDiv) {
                    iconDiv.style.background = '#f3f4f6';
                    iconDiv.style.color = '#4b5563';
                }
            });
            this.classList.add('active');
            const activeIconDiv = this.querySelector('div');
            if(activeIconDiv) {
                activeIconDiv.style.background = '#374151';
                activeIconDiv.style.color = 'white';
            }

            // Kartları filtrele
            const filterValue = this.getAttribute('data-filter');
            restCards.forEach(card => {
                if (filterValue === 'all') {
                    card.style.display = 'flex';
                } else {
                    const cardCat = card.getAttribute('data-category').toLowerCase();
                    if (cardCat.includes(filterValue.toLowerCase())) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
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
let trackingInterval = null;

function openTrackModal(orderId) {
    const modal = document.getElementById('courierTrackModal');
    if (modal) modal.style.display = 'flex';
    
    // Modalın açılma animasyonunu bekle ve haritayı çiz (Gri ekran hatasını çözer)
    setTimeout(() => {
        initTrackMap();
        fetchCourierLocation(orderId); // İlk konumu anında çek
        
        // Her 5 saniyede bir kuryenin konumunu arka planda güncelle
        trackingInterval = setInterval(() => {
            fetchCourierLocation(orderId);
        }, 5000);
    }, 300);
}

function closeTrackModal() {
    const modal = document.getElementById('courierTrackModal');
    if (modal) modal.style.display = 'none';
    
    // Modalı kapatınca interneti yormamak için arka plandaki sorguyu durdur
    if (trackingInterval) {
        clearInterval(trackingInterval);
        trackingInterval = null;
    }
}

function initTrackMap() {
    const mapEl = document.getElementById('live-tracking-map');
    if (!mapEl) return; 

    if (!trackMap) {
        // Haritayı doğru ID'nin içine çiz
        trackMap = L.map('live-tracking-map').setView([41.0082, 28.9784], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(trackMap);
        
        // Kurye İkonu
        const courierIcon = L.divIcon({
            html: '<div style="background:#10b981; color:white; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.3);"><i class="ph-bold ph-moped" style="font-size:20px;"></i></div>',
            className: '',
            iconSize: [34, 34],
            iconAnchor: [17, 17]
        });

        courierMarker = L.marker([41.0082, 28.9784], {icon: courierIcon}).addTo(trackMap);
    } else {
        // Harita zaten açıksa boyutlarını tazele 
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
            const newPos = [data.lat, data.lon];
            
            // Kurye pin'ini yeni konuma taşı
            if(courierMarker) {
                courierMarker.setLatLng(newPos);
                courierMarker.bindPopup(`<b>${data.name}</b><br>Kurye hızla yaklaşıyor!`).openPopup();
            }
            
            // Harita kamerasını yumuşak bir şekilde kuryeye kaydır
            if(trackMap) {
                trackMap.flyTo(newPos, 16, { animate: true, duration: 1.5 });
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


// ==========================================
// 🤖 YAPAY ZEKA GURME ASİSTAN
// ==========================================
function toggleChat() {
    const chatWindow = document.getElementById('ai-chat-window');
    if (chatWindow.style.display === 'none' || chatWindow.style.display === '') {
        chatWindow.style.display = 'flex';
    } else {
        chatWindow.style.display = 'none';
    }
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
// 📍 ADRES VE HARİTA (LEAFLET)
// ==========================================
let map;
let marker;

function openAddressModal() {
    document.getElementById('addressListModal').style.display = 'flex';
}

function closeAddressModal() {
    document.getElementById('addressListModal').style.display = 'none';
}

function openNewAddressModal() {
    document.getElementById('addressListModal').style.display = 'none';
    document.getElementById('addressFormModal').style.display = 'flex';
    document.getElementById('addressMapModal').style.display = 'flex';
    
    setTimeout(() => { initMap(); }, 300);
}

function initMap() {
    if (map) { map.invalidateSize(); return; }
    
    map = L.map('address-picker-map').setView([41.0082, 28.9784], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    marker = L.marker([41.0082, 28.9784], {draggable: true}).addTo(map);

    map.on('click', function(e) {
        marker.setLatLng(e.latlng);
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(position => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            map.setView([lat, lon], 15);
            marker.setLatLng([lat, lon]);
        });
    }
}

function confirmMapLocation() {
    const pos = marker.getLatLng();
    document.getElementById('addr-lat').value = pos.lat;
    document.getElementById('addr-lon').value = pos.lng;
    document.getElementById('addressMapModal').style.display = 'none';
}

function submitAddressForm() {
    const data = {
        city: document.getElementById('addr-city').value,
        district: document.getElementById('addr-district').value,
        neighborhood: document.getElementById('addr-neighborhood').value,
        street: document.getElementById('addr-street').value,
        building_no: document.getElementById('addr-building').value,
        floor_no: document.getElementById('addr-floor').value,
        apt_no: document.getElementById('addr-apt').value,
        directions: document.getElementById('addr-directions').value,
        title: document.getElementById('addr-title').value,
        contact_name: document.getElementById('addr-cname').value,
        contact_phone: document.getElementById('addr-cphone').value,
        latitude: document.getElementById('addr-lat').value,
        longitude: document.getElementById('addr-lon').value
    };

    if(!data.city || !data.district || !data.neighborhood || !data.street || !data.building_no || !data.title || !data.contact_name || !data.contact_phone) {
        if(typeof window.showToast === 'function') window.showToast("Lütfen zorunlu alanları doldurun.", "error");
        return;
    }

    const btn = document.getElementById('form-submit-btn');
    const oldText = btn.innerHTML;
    btn.innerHTML = "Kaydediliyor...";
    btn.disabled = true;

    fetch('/api/add_address', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
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