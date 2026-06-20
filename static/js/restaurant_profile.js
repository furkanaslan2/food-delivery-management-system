// ==========================================
// 🏪 RESTORAN PROFİLİ VE HARİTA AYARLARI
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    
    // ----------------------------------------------------
    // 1. FOTOĞRAF YÜKLEME VE GÜVENLİK KONTROLÜ
    // ----------------------------------------------------
    const imageInput = document.querySelector('input[name="restaurant_image"]');
    if (imageInput) {
        imageInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (!file) return;

            const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
            if (!validTypes.includes(file.type)) {
                if (typeof window.showToast === 'function') window.showToast("Sadece JPG, PNG veya WEBP formatında resim yükleyebilirsiniz.", "error");
                else alert("Sadece JPG, PNG veya WEBP formatında resim yükleyebilirsiniz.");
                this.value = ''; 
                return;
            }

            const maxSizeInBytes = 3 * 1024 * 1024; 
            if (file.size > maxSizeInBytes) {
                if (typeof window.showToast === 'function') window.showToast("Fotoğraf boyutu 3 MB'dan küçük olmalıdır. Lütfen görseli küçültüp tekrar deneyin.", "error");
                else alert("Fotoğraf boyutu 3 MB'dan küçük olmalıdır. Lütfen görseli küçültüp tekrar deneyin.");
                this.value = ''; 
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                const previewContainer = document.querySelector('.image-preview');
                if (previewContainer) {
                    previewContainer.innerHTML = `<img src="${e.target.result}" alt="Yeni Kapak">`;
                }
            }
            reader.readAsDataURL(file);
        });
    }

    // ----------------------------------------------------
    // 2. HARİTA YÜKLEMESİ VE KONUM SEÇİMİ (LEAFLET)
    // ----------------------------------------------------
    const mapElement = document.getElementById('map');
    
    // Harita div'i ve Leaflet kütüphanesi (L) yüklü mü kontrol et
    if (mapElement && typeof L !== 'undefined') {
        const latInput = document.getElementById('latitude');
        const lonInput = document.getElementById('longitude');
        
        let initialLat = latInput.value ? parseFloat(latInput.value) : 41.0082;
        let initialLon = lonInput.value ? parseFloat(lonInput.value) : 28.9784;
        let isConfigured = latInput.value ? true : false;
        
        let map = L.map('map').setView([initialLat, initialLon], isConfigured ? 15 : 11);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        let marker = L.marker([initialLat, initialLon], {draggable: true}).addTo(map);

        function syncCoordinates(lat, lon) {
            if (latInput) latInput.value = lat.toFixed(6);
            if (lonInput) lonInput.value = lon.toFixed(6);
        }
        
        if (!isConfigured) syncCoordinates(initialLat, initialLon);

        // Marker sürüklendiğinde koordinatları güncelle
        marker.on('dragend', function(e) { 
            let pos = marker.getLatLng(); 
            syncCoordinates(pos.lat, pos.lng); 
        });
        
        // Haritaya tıklandığında marker'ı oraya taşı
        map.on('click', function(e) { 
            marker.setLatLng(e.latlng); 
            syncCoordinates(e.latlng.lat, e.latlng.lng); 
        });

        // Sol üstteki "Şu anki konumumu bul" (GPS) Butonu
        let gpsControl = L.control({position: 'topleft'});
        gpsControl.onAdd = function(mapObj) {
            let btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control');
            btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#374151" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top:3px;"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><circle cx="12" cy="12" r="8"></circle></svg>';
            btn.style.cssText = 'background-color: white; width: 34px; height: 34px; cursor: pointer; display: flex; justify-content: center; align-items: center;';
            
            btn.onclick = function(e) {
                e.preventDefault(); 
                e.stopPropagation();
                if(navigator.geolocation) {
                    btn.style.opacity = '0.5'; 
                    navigator.geolocation.getCurrentPosition(function(pos) {
                        let lat = pos.coords.latitude; 
                        let lon = pos.coords.longitude;
                        map.setView([lat, lon], 16); 
                        marker.setLatLng([lat, lon]); 
                        syncCoordinates(lat, lon); 
                        btn.style.opacity = '1';
                    });
                }
            };
            return btn;
        };
        gpsControl.addTo(map);
    }
});

// ==========================================
// 🛡️ RESTORAN PROFİLİ MASTER KONTROL (AKILLI DOĞRULAMA)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const profileForm = document.getElementById('restaurant-profile-form');
    
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            let hasError = false;
            let errorMessage = "";

            const name = document.querySelector('[name="restaurant_name"]').value.trim();
            const cuisine = document.querySelector('[name="cuisine"]').value;
            const city = document.querySelector('[name="city"]').value.trim(); 
            const tableCount = document.querySelector('[name="table_count"]').value.trim(); 
            const openTime = document.querySelector('[name="opening_time"]').value.trim();
            const closeTime = document.querySelector('[name="closing_time"]').value.trim();
            const minOrder = document.querySelector('[name="min_order_amount"]').value.trim();
            const address = document.querySelector('[name="restaurant_address"]').value.trim();
            
            const lat = document.getElementById('latitude').value.trim();
            const lon = document.getElementById('longitude').value.trim();

            if (!name) {
                hasError = true;
                errorMessage = "Lütfen restoranınızın adını girin.";
            } else if (!cuisine) {
                hasError = true;
                errorMessage = "Lütfen mutfak türünü (Kategori) seçin.";
            } else if (!city) {
                hasError = true;
                errorMessage = "Lütfen bulunduğunuz şehri girin.";
            } else if (!tableCount || parseInt(tableCount) < 1) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir masa kapasitesi (en az 1) girin.";
            } else if (!openTime) {
                hasError = true;
                errorMessage = "Lütfen restoranınızın açılış saatini belirleyin.";
            } else if (!closeTime) {
                hasError = true;
                errorMessage = "Lütfen restoranınızın kapanış saatini belirleyin.";
            } else if (!minOrder || parseFloat(minOrder) < 0) {
                hasError = true;
                errorMessage = "Lütfen geçerli bir minimum sipariş tutarı girin (0 veya daha büyük olmalıdır).";
            } else if (!address) { 
                hasError = true;
                errorMessage = "Lütfen açık adresinizi girin.";
            } else if (!lat || !lon) {
                hasError = true;
                errorMessage = "Lütfen harita üzerinden restoranınızın tam konumunu işaretleyin.";
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
            
            // ✅ HATA YOKSA: Form sorunsuzca Python'a gider
        });
    }
});