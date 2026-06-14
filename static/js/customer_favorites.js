document.addEventListener("DOMContentLoaded", function() {
    const mainFavBtns = document.querySelectorAll('.main-page-fav-btn');
    
    mainFavBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const restaurantId = this.getAttribute('data-id');
            const card = document.getElementById(`rest-card-${restaurantId}`);
            
            // Tatlı bir küçülme ve kaybolma animasyonu
            card.style.transform = 'scale(0.9)';
            card.style.opacity = '0';
            card.style.transition = 'all 0.3s ease';

            fetch('/api/toggle_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
                body: JSON.stringify({ restaurant_id: restaurantId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.action === 'removed') {
                    showToast("Restoran favorilerden çıkarıldı.", "success");
                    setTimeout(() => { 
                        card.remove(); 
                        const remainingCards = document.querySelectorAll('.restaurant-card');
                        
                        // Eğer son kart silindiyse Jilet gibi bir boş durum (Empty State) göster
                        if (remainingCards.length === 0) {
                            const grid = document.getElementById('favorites-grid');
                            grid.style.display = 'block';
                            grid.innerHTML = `
                                <div style="grid-column: 1 / -1; text-align: center; padding: 80px 20px; background: white; border-radius: 24px; border: 2px dashed #e5e7eb; animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);">
                                    <div style="font-size: 70px; margin-bottom: 20px; color: #d1d5db;"><i class="ph-fill ph-heart-break"></i></div>
                                    <h3 style="margin: 0 0 10px 0; color: #111827; font-size: 22px;">Tüm favorilerinizi sildiniz.</h3>
                                    <p style="color: #6b7280; margin: 0 0 25px 0; font-size: 15px;">Yeni lezzetler keşfetme zamanı geldi.</p>
                                    <a href="/" style="display:inline-flex; align-items: center; gap: 8px; padding:14px 28px; background:#4f46e5; color:white; text-decoration:none; border-radius:12px; font-weight:700; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3); transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                                        <i class="ph-bold ph-magnifying-glass"></i> Hemen Keşfet
                                    </a>
                                </div>
                            `;
                        }
                    }, 300);
                } else {
                    card.style.transform = '';
                    card.style.opacity = '';
                    showToast(data.message || 'Bir hata oluştu.', 'error');
                }
            })
            .catch(error => {
                card.style.transform = '';
                card.style.opacity = '';
                showToast('Bağlantı Hatası', 'error');
                console.error('Favori Hatası:', error);
            });
        });
    });
});