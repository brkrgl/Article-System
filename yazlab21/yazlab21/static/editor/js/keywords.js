document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM yüklendi, geliştirilmiş anahtar kelime fonksiyonları başlatılıyor...");

    setupKeywordSections();
    
    const checkInterval = setInterval(checkPendingKeywords, 3000);

    setTimeout(() => {
        clearInterval(checkInterval);
        console.log("Otomatik anahtar kelime kontrolü durduruluyor (60 saniye limiti)");
    }, 60 * 1000);
});

function setupKeywordSections() {
    const articleCards = document.querySelectorAll(".card");
    
    articleCards.forEach(card => {
        const cardBody = card.querySelector(".card-body");
        const articleId = card.getAttribute("data-article-id");
        
        if (!articleId) {
            console.warn("Makale ID'si bulunamadı!");
            return;
        }
        
        const keywordsSection = document.createElement("div");
        keywordsSection.className = "keywords-section mt-3";
        keywordsSection.setAttribute("data-article-id", articleId);
        
        keywordsSection.innerHTML = createLoadingHTML();
        
        const buttonsDiv = cardBody.querySelector(".d-flex.flex-wrap");
        if (buttonsDiv && buttonsDiv.parentNode) {
            buttonsDiv.parentNode.insertBefore(keywordsSection, buttonsDiv.nextSibling);
            
            fetchKeywords(articleId);
        } else {
            console.warn(`Makale #${articleId} için buton bölümü bulunamadı`);
        }
    });
}

/**
 * Yükleniyor HTML'i oluşturur
 * @returns {string} HTML içeriği
 */
function createLoadingHTML() {
    return `
        <div class="d-flex align-items-center">
            <span class="spinner-border spinner-border-sm text-primary me-2" role="status"></span>
            <small class="text-muted">Anahtar kelimeler çıkarılıyor...</small>
        </div>
    `;
}

/**
 * Yeniden deneme HTML'i oluşturur
 * @param {string} articleId - Makalenin ID'si
 * @returns {string} HTML içeriği
 */
function createRetryHTML(articleId) {
    return `
        <div class="d-flex align-items-center justify-content-between">
            <small class="text-danger">Anahtar kelimeler çıkarılamadı.</small>
            <button class="btn btn-sm btn-outline-secondary retry-keywords" 
                    data-article-id="${articleId}">
                <i class="fas fa-sync-alt"></i> Yeniden Dene
            </button>
        </div>
    `;
}

/**
 * Belirli bir makale için anahtar kelimeleri almak için AJAX isteği gönderir
 * @param {string} articleId - Makalenin Drive ID'si (birincil anahtar)
 */
function fetchKeywords(articleId) {
    const keywordsSection = document.querySelector(`.keywords-section[data-article-id="${articleId}"]`);
    
    if (!keywordsSection) {
        console.warn(`Makale #${articleId} için anahtar kelime bölümü bulunamadı`);
        return;
    }
    
    keywordsSection.innerHTML = createLoadingHTML();
    keywordsSection.setAttribute("data-pending", "true");
    
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch('/editor/get_article_keywords/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            article_id: articleId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Sunucu hatası: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`Makale #${articleId} durumu: ${data.status}, anahtar kelimeler:`, data.keywords);
            

            if (data.status === 'completed') {
                keywordsSection.removeAttribute("data-pending");
                console.log(`Makale #${articleId} işlemi tamamlandı, polling durduruluyor.`);
            }
            
            updateKeywordsUI(articleId, data.keywords, data.status, data.error_message);
        } else {
            console.error("Anahtar kelime alma hatası:", data.message);
            keywordsSection.removeAttribute("data-pending");
            showKeywordError(articleId, data.message || "Bilinmeyen hata");
        }
    })
    .catch(error => {
        console.error("Anahtar kelime istek hatası:", error);
        keywordsSection.removeAttribute("data-pending");
        showKeywordError(articleId, "İstek hatası: " + error.message);
    });
}

/**
 * Anahtar kelime bölümünü güncelle
 * @param {string} articleId - Makalenin Drive ID'si
 * @param {Array} keywords - Anahtar kelimeler dizisi
 * @param {string} status - Anahtar kelime çıkarma durumu (pending, completed veya failed)
 * @param {string} errorMessage - Hata mesajı (varsa)
 */
function updateKeywordsUI(articleId, keywords, status, errorMessage) {
    const keywordsSection = document.querySelector(`.keywords-section[data-article-id="${articleId}"]`);
    
    if (!keywordsSection) {
        console.warn(`Makale #${articleId} için anahtar kelime bölümü bulunamadı`);
        return;
    }
    
    if (status === "completed") {
        if (keywords && keywords.length > 0) {
            keywordsSection.innerHTML = `
                <div class="mt-2">
                    <small class="text-muted fw-bold">Anahtar Kelimeler:</small>
                    <div class="d-flex flex-wrap mt-1">
                        ${keywords.map(keyword => 
                            `<span class="badge bg-info text-dark me-1 mb-1">${keyword}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        } else {
            keywordsSection.innerHTML = `
                <small class="text-muted">Anahtar kelimeler bulunamadı.</small>
            `;
        }
        keywordsSection.removeAttribute("data-pending");
        
    } else if (status === "pending") {
        keywordsSection.innerHTML = createLoadingHTML();
        keywordsSection.setAttribute("data-pending", "true");
        
    } else if (status === "failed") {
        keywordsSection.innerHTML = createRetryHTML(articleId);
        keywordsSection.removeAttribute("data-pending");
        
        const retryButton = keywordsSection.querySelector('.retry-keywords');
        if (retryButton) {
            retryButton.addEventListener('click', function() {
                fetchKeywords(articleId);
            });
        }
        
    } else {
        keywordsSection.innerHTML = `
            <small class="text-muted">Anahtar kelimeler bulunamadı.</small>
            <button class="btn btn-sm btn-outline-secondary retry-keywords mt-1" 
                    data-article-id="${articleId}">
                <i class="fas fa-sync-alt"></i> Yeniden Dene
            </button>
        `;

        keywordsSection.removeAttribute("data-pending");
        
        const retryButton = keywordsSection.querySelector('.retry-keywords');
        if (retryButton) {
            retryButton.addEventListener('click', function() {
                fetchKeywords(articleId);
            });
        }
    }
}

/**
 * Anahtar kelime çıkarma hatası gösterir
 * @param {string} articleId
 * @param {string} errorMessage
 */
function showKeywordError(articleId, errorMessage) {
    const keywordsSection = document.querySelector(`.keywords-section[data-article-id="${articleId}"]`);
    
    if (!keywordsSection) return;

    keywordsSection.removeAttribute("data-pending");
    
    keywordsSection.innerHTML = `
        <div class="d-flex align-items-center justify-content-between">
            <small class="text-danger">Hata: ${errorMessage}</small>
            <button class="btn btn-sm btn-outline-secondary retry-keywords" 
                    data-article-id="${articleId}">
                <i class="fas fa-sync-alt"></i> Yeniden Dene
            </button>
        </div>
    `;

    const retryButton = keywordsSection.querySelector('.retry-keywords');
    if (retryButton) {
        retryButton.addEventListener('click', function() {
            fetchKeywords(articleId);
        });
    }
}

function checkPendingKeywords() {
    const pendingKeywordSections = document.querySelectorAll('.keywords-section[data-pending="true"]');
    
    if (pendingKeywordSections.length === 0) {
        console.log("Bekleyen anahtar kelime işlemi kalmadı.");
        return;
    }
    
    console.log(`${pendingKeywordSections.length} adet bekleyen anahtar kelime işlemi kontrol ediliyor...`);
    
    const maxConcurrentRequests = 3;
    const sections = Array.from(pendingKeywordSections).slice(0, maxConcurrentRequests);
    
    sections.forEach(section => {
        const articleId = section.getAttribute("data-article-id");
        if (articleId) {
            fetchKeywords(articleId);
        }
    });
}

function refreshKeywordSections() {
    // Mevcut anahtar kelime bölümlerini temizle
    document.querySelectorAll('.keywords-section').forEach(section => {
        section.remove();
    });
    
    setupKeywordSections();
}

window.refreshKeywords = refreshKeywordSections;