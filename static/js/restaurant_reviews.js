// ==========================================
// 🛡️ YORUM YANITLAMA MASTER KONTROL (AKILLI BİLDİRİM)
// ==========================================
function submitReply(orderId) {
    const replyInput = document.getElementById(`reply-input-${orderId}`);
    const replyText = replyInput.value.trim();
    
    // 1. Akıllı Doğrulama: Yanıt boş mu?
    if (!replyText) {
        if (typeof window.showToast === 'function') {
            window.showToast("Lütfen göndermeden önce bir yanıt yazın.", "error");
        } else {
            alert("Lütfen bir yanıt yazın.");
        }
        return;
    }

    // 2. Arka Planda Gönderim (Sayfa Yenilenmez)
    fetch('/api/reply_review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId, reply_text: replyText })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // ✅ BAŞARILI: Şık yeşil bildirim ve anında ekrana yansıtma
            if (typeof window.showToast === 'function') {
                window.showToast("Yanıtınız başarıyla müşteriye iletildi!", "success");
            }
            
            const container = document.getElementById(`reply-container-${orderId}`);
            container.innerHTML = `
                <div style="background: #e0f2fe; padding: 15px; border-radius: 8px; border-left: 4px solid #0ea5e9; animation: fadeIn 0.4s ease;">
                    <span style="font-size: 12px; font-weight: 700; color: #0284c7; text-transform: uppercase;">Restoranınızın Yanıtı:</span>
                    <p style="margin: 5px 0 0 0; color: #0f172a; font-size: 15px;">${replyText}</p>
                </div>
            `;
        } else {
            // ❌ SUNUCU HATASI: İşlem reddedildiğinde şık kırmızı bildirim
            if (typeof window.showToast === 'function') {
                window.showToast(data.message || "Yanıt gönderilemedi.", "error");
            } else {
                alert(data.message || "Yanıt gönderilemedi.");
            }
        }
    })
    .catch(err => {
        console.error(err);
        // ❌ BAĞLANTI HATASI: İnternet koptuğunda şık bildirim
        if (typeof window.showToast === 'function') {
            window.showToast("Sunucu ile bağlantı kurulurken bir hata oluştu.", "error");
        } else {
            alert("Bir hata oluştu.");
        }
    });
}