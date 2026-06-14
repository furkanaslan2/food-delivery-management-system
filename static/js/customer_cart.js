// ==========================================
// 🛒 MÜŞTERİ SEPET YÖNETİMİ (customer_cart.js)
// ==========================================

function applyPromoCode() {
    const code = document.getElementById('promo_input').value;
    if (!code) {
        if (typeof window.showToast === "function") window.showToast("Lütfen bir kupon kodu girin.", "error");
        return;
    }

    const btn = document.getElementById('promo_btn');
    const originalText = btn.innerText;
    btn.innerText = "Uygulanıyor...";
    btn.disabled = true;

    // NOT: Harici JS dosyasında olduğumuz için url_for yerine düz URL kullanıyoruz.
    fetch('/api/apply_promo', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ promo_code: code })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if (typeof window.showToast === "function") window.showToast(data.message, "success");

            // Başarılı olursa input'u kitle ve gizli input'a değeri yaz (Siparişte yollamak için)
            document.getElementById('hidden_promo_code').value = code;
            document.getElementById('promo_input').disabled = true;

            // Butonu İptal Et butonuna çevir
            btn.innerText = "İptal Et";
            btn.style.background = "#ef4444";
            btn.onclick = removePromoCode;
            btn.disabled = false;

            // Fiyat Arayüzünü Güncelle
            const discountRow = document.getElementById('ui_discount_row');
            if (discountRow) discountRow.style.display = "flex";

            const discountAmountEl = document.getElementById('ui_discount_amount');
            if (discountAmountEl) discountAmountEl.innerText = '-₺' + data.discount_amount.toFixed(2);

            const totalElements = document.querySelectorAll('.summary-total span:last-child');
            totalElements.forEach(el => {
                el.innerText = '₺' + data.new_total.toFixed(2);
            });
        } else {
            if (typeof window.showToast === "function") window.showToast(data.message, "error");
            btn.innerText = originalText;
            btn.disabled = false;
        }
    })
    .catch(err => {
        console.error(err);
        if (typeof window.showToast === "function") window.showToast("Bağlantı hatası.", "error");
        btn.innerText = originalText;
        btn.disabled = false;
    });
}

function removePromoCode() {
    document.getElementById('hidden_promo_code').value = "";
    
    const input = document.getElementById('promo_input');
    input.value = "";
    input.disabled = false;

    const btn = document.getElementById('promo_btn');
    btn.innerText = "Uygula";
    btn.style.background = "#111827";
    btn.onclick = applyPromoCode;

    const discountRow = document.getElementById('ui_discount_row');
    if (discountRow) discountRow.style.display = "none";
    
    // Fiyatı hesaplanan eski orijinal tutara geri döndür
    const origAmountEl = document.getElementById('original_total_amount');
    if (origAmountEl) {
        const origAmount = parseFloat(origAmountEl.value);
        const totalElements = document.querySelectorAll('.summary-total span:last-child');
        totalElements.forEach(el => {
            el.innerText = '₺' + origAmount.toFixed(2);
        });
    }
}

window.addEventListener("pageshow", function(event) {
    if (event.persisted) {
        window.location.reload(); 
    }
});