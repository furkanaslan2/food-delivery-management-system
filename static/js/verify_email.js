// ==========================================
// 📧 E-POSTA DOĞRULAMA (OTP) VE SAYAÇ MOTORU
// ==========================================

let timeLeft;
let countdown;

document.addEventListener("DOMContentLoaded", function() {
    // 1. OTP Kutucukları Animasyon ve Mantığı
    const inputs = document.querySelectorAll('.otp-input');
    
    if (inputs.length > 0) {
        inputs.forEach((input, index) => {
            input.addEventListener('input', (e) => {
                if (e.target.value.length === 1) {
                    input.classList.add('filled');
                    if (index < inputs.length - 1) inputs[index + 1].focus();
                } else {
                    input.classList.remove('filled');
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !e.target.value && index > 0) {
                    inputs[index - 1].focus();
                    inputs[index - 1].value = '';
                    inputs[index - 1].classList.remove('filled');
                }
            });
            
            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const pastedData = e.clipboardData.getData('text').slice(0, 6).replace(/[^0-9]/g, '');
                pastedData.split('').forEach((char, i) => {
                    if (i < inputs.length) {
                        inputs[i].value = char;
                        inputs[i].classList.add('filled');
                        if (i < inputs.length - 1) inputs[i + 1].focus();
                    }
                });
            });
        });
    }

    // 2. Sayfa açıldığında sayacı başlat
    startTimer();
});

// ----------------------------------------------------
// 🚀 SAYAÇ VE BUTON FONKSİYONLARI
// ----------------------------------------------------

function startTimer() {
    const timerEl = document.getElementById('timer');
    const resendBtn = document.getElementById('resend-btn');
    if (!timerEl || !resendBtn) return;

    timeLeft = 60;
    timerEl.style.display = 'inline';
    resendBtn.style.opacity = '0.5';
    resendBtn.style.pointerEvents = 'none';
    resendBtn.innerText = 'Tekrar Gönder';

    clearInterval(countdown); // Önceki sayacı temizle
    countdown = setInterval(() => {
        timeLeft--;
        let seconds = timeLeft % 60;
        timerEl.innerText = `00:${seconds < 10 ? '0' : ''}${seconds}`;
        
        if (timeLeft <= 0) {
            clearInterval(countdown);
            timerEl.style.display = 'none';
            resendBtn.style.opacity = '1';
            resendBtn.style.pointerEvents = 'auto';
        }
    }, 1000);
}

window.submitVerification = function() {
    const inputs = document.querySelectorAll('.otp-input');
    let code = '';
    inputs.forEach(input => code += input.value);
    
    if (code.length === 6) {
        const btn = document.querySelector('.verify-btn');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Doğrulanıyor...';
        btn.disabled = true;

        fetch("/verify_email_code", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ verification_code: code })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect;
            } else {
                if(typeof window.showToast === 'function') window.showToast(data.message, 'error'); 
                inputs.forEach(input => { 
                    input.value = ''; 
                    input.classList.remove('filled');
                    input.style.borderColor = '#ef4444';
                    setTimeout(() => input.style.borderColor = '', 1500);
                });
                inputs[0].focus();
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        })
        .catch(err => {
            if(typeof window.showToast === 'function') window.showToast("Bağlantı hatası oluştu.", "error");
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
    } else {
        if(typeof window.showToast === 'function') window.showToast("Lütfen 6 haneli kodu eksiksiz girin.", "error");
    }
};

window.resendCode = function() {
    const resendBtn = document.getElementById('resend-btn');
    if (!resendBtn) return;

    resendBtn.innerText = 'Gönderiliyor...';
    resendBtn.style.opacity = '0.5';
    resendBtn.style.pointerEvents = 'none';

    fetch("/resend_verification_code", {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if(typeof window.showToast === 'function') window.showToast(data.message, 'success');
            startTimer();
        } else {
            if(typeof window.showToast === 'function') window.showToast(data.message, 'error');
            resendBtn.innerText = 'Tekrar Gönder';
            resendBtn.style.opacity = '1';
            resendBtn.style.pointerEvents = 'auto';
        }
    })
    .catch(err => {
        if(typeof window.showToast === 'function') window.showToast("Bir hata oluştu, tekrar deneyin.", "error");
        resendBtn.innerText = 'Tekrar Gönder';
        resendBtn.style.opacity = '1';
        resendBtn.style.pointerEvents = 'auto';
    });
};