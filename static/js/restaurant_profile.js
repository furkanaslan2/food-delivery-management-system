// ==========================================
// 🏪 RESTORAN PROFİLİ VE HARİTA AYARLARI
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    
    // ----------------------------------------------------
    // 1. FOTOĞRAF YÜKLEME ÖNİZLEMESİ
    // ----------------------------------------------------
    const imageInput = document.querySelector('input[name="restaurant_image"]');
    if (imageInput) {
        imageInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewContainer = document.querySelector('.image-preview');
                    if (previewContainer) {
                        previewContainer.innerHTML = `<img src="${e.target.result}" alt="Yeni Kapak">`;
                    }
                }
                reader.readAsDataURL(file);
            }
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