import io
import PyPDF2
import pdfplumber
import spacy
import re
import traceback
from collections import Counter
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from author.models import UncensoredArticles
from .models import ArticleKeywords

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def authenticate():
    """Google Drive API için kimlik doğrulama"""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def download_pdf_from_drive(drive_id):
    """Google Drive'dan PDF dosyasını indir"""
    try:
        creds = authenticate()
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=drive_id)
        pdf_file = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_file, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        pdf_file.seek(0)
        return pdf_file
    except Exception as e:
        print(f"PDF indirme hatası: {str(e)}")
        return None

def extract_text_from_pdf(pdf_file):
    """
    PDF dosyasından metin çıkar - birden fazla kütüphane kullanarak
    daha güvenilir metin çıkarma
    """
    text_from_pypdf = ""
    text_from_pdfplumber = ""
    
    try:
        # PyPDF2 ile metin çıkarma dene
        pdf_file.seek(0)  # Dosya konumunu başa al
        reader = PyPDF2.PdfReader(pdf_file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:  # Boş olmayan metinleri ekle
                text_from_pypdf += page_text + "\n"
    except Exception as e:
        print(f"PyPDF2 metin çıkarma hatası: {str(e)}")
    
    try:
        pdf_file.seek(0)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_from_pdfplumber += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber metin çıkarma hatası: {str(e)}")
    
    # En uzun metni döndür
    if len(text_from_pdfplumber) > len(text_from_pypdf):
        return text_from_pdfplumber
    return text_from_pypdf

def clean_keyword(keyword):
    """Anahtar kelimelerden gereksiz noktalama işaretlerini temizle"""
    cleaned = keyword.strip()
    

    cleaned = re.sub(r'(\w)-(\w)', r'\1 \2', cleaned)
    
    cleaned = re.sub(r'[,.;:!?()[\]{}]', ' ', cleaned)
    

    cleaned = re.sub(r'\s+', ' ', cleaned)
    

    cleaned = cleaned.strip()
    

    cleaned = cleaned.lower()
    
    return cleaned

def extract_ieee_keywords(text):
    """IEEE makalelerindeki belirtilmiş anahtar kelimeleri bul - geliştirilmiş kalıplar"""
    keywords = []
    
    patterns = [
        r'(?:Index Terms|Keywords|Key\s*words)[—:\s]+([^\n\.]+)',
        r'KEYWORDS:?\s+([^\n\.]+)',
        r'Key\s+words:?\s+([^\n\.]+)',
        r'KEY\s+WORDS:?\s+([^\n\.]+)',
        r'Key terms:?\s+([^\n\.]+)',
        r'Index Terms—([^\n\.]+)',
        r'Keywords—([^\n\.]+)',
        r'Keywords/Index Terms:?\s+([^\n\.]+)',
        r'Key-words:?\s+([^\n\.]+)',
        r'(?:^|\n)Keywords:?\s+([^\n\.]+)',
        r'(?<=Abstract)[\s\n]+(?:Index Terms|Keywords):[\s\n]+([^\.]+\.)',
        r'Index Terms:?[\s\n]+([^\.]+\.)',
        r'Keywords:[\s\n]+([^\.]+\.)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            for match in matches:
                if ',' in match:
                    keyword_list = match.split(',')
                else:

                    keyword_list = re.split(r'\.(?=\s+[A-Z])', match)
                
                for keyword in keyword_list:
                    cleaned_keyword = clean_keyword(keyword)
                    if cleaned_keyword and len(cleaned_keyword) > 2:
                        if " and " in cleaned_keyword:
                            parts = cleaned_keyword.split(" and ")
                            for part in parts:
                                part = part.strip()
                                if part and len(part) > 2:
                                    keywords.append(part)
                        else:
                            keywords.append(cleaned_keyword)
            
            if keywords:
                return list(set(keywords))
    
    paper_end_patterns = [
        r'keywords:?\s+([^\n\.]+)\s+(?=references|bibliography)',
        r'index terms:?\s+([^\n\.]+)\s+(?=references|bibliography)',
    ]
    
    for pattern in paper_end_patterns:
        matches = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            match = matches.group(1)
            keyword_list = match.split(',')
            for keyword in keyword_list:
                cleaned_keyword = clean_keyword(keyword)
                if cleaned_keyword and len(cleaned_keyword) > 2:
                    keywords.append(cleaned_keyword)
    
    return list(set(keywords))

def extract_abstract_based_keywords(text, top_n=8):
    """Makalenin özetinden anahtar kelimeleri çıkar"""
    abstract_patterns = [
        r'(?:Abstract|ABSTRACT)[:\s—]+(.+?)(?=\bIntroduction\b|\bI\.\s+Introduction\b|\n\n)',
        r'Abstract(?:—|\s—\s)(.+?)(?=\bIntroduction\b|\bI\.\s+Introduction\b|\n\n)',
        r'(?:^|\n)ABSTRACT(?:\.|:|\s|\n)(.+?)(?=\bIntroduction\b|\bI\.\s+Introduction\b|\n\n)',
        r'Abstract:?\s*\n+(.+?)(?=\n+\s*(?:Keywords:|Index Terms:|I\.|1\.|Introduction|INTRODUCTION))'
    ]
    
    abstract_text = ""
    for pattern in abstract_patterns:
        matches = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            abstract_text = matches.group(1)
            break
    
    if not abstract_text and len(text) > 100:
        first_section = text[:min(2000, len(text))]
        paragraphs = re.split(r'\n\s*\n', first_section)
        if len(paragraphs) > 1:

            abstract_text = paragraphs[1]
        else:
            abstract_text = first_section
    
    if not abstract_text:
        return []
    
    try:

        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(abstract_text)
            
            noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks 
                          if 2 <= len(chunk.text.split()) <= 4]
            

            stop_patterns = [
                r"^\d+$", r"^fig\b", r"^figure\b", r"^table\b", r"^et al\b", 
                r"^ieee\b", r"^copyright\b", r"^abstract\b", r"^\w+ \d+$", r"^introduction\b",
                r"^proposed\s+\w+$", r"^our\s+\w+$", r"^this\s+\w+$"
            ]
            
            filtered_phrases = []
            for phrase in noun_chunks:
                cleaned = clean_keyword(phrase)
                if len(cleaned) > 3 and not any(re.search(pattern, cleaned) for pattern in stop_patterns):
                    filtered_phrases.append(cleaned)
            

            technical_terms = [
                "neural network", "deep learning", "machine learning", "artificial intelligence", 
                "eeg", "security", "cryptography", "wireless", "5g", "cloud computing",
                "big data", "internet of things", "blockchain", "edge computing"
            ]
            

            for term in technical_terms:
                if term in abstract_text.lower() and term not in filtered_phrases:
                    filtered_phrases.append(term)
            

            counter = Counter(filtered_phrases)
            return [phrase for phrase, _ in counter.most_common(top_n)]
        
        except ImportError:

            words = re.findall(r'\b[a-zA-Z]{3,}\b', abstract_text.lower())

            stop_words = {'the', 'and', 'for', 'this', 'that', 'with', 'from', 'are', 'was', 'were', 
                         'has', 'have', 'our', 'their', 'these', 'those', 'such', 'which', 'when',
                         'what', 'where', 'who', 'how', 'why', 'can', 'all', 'any', 'been', 'will'}
            filtered_words = [w for w in words if w not in stop_words]
            

            phrases = []
            words_list = abstract_text.lower().split()
            for i in range(len(words_list) - 1):
                if words_list[i] not in stop_words and words_list[i+1] not in stop_words:
                    phrases.append(f"{words_list[i]} {words_list[i+1]}")
                    if i < len(words_list) - 2 and words_list[i+2] not in stop_words:
                        phrases.append(f"{words_list[i]} {words_list[i+1]} {words_list[i+2]}")
            
            all_terms = filtered_words + phrases
            word_freq = Counter(all_terms)
            return [word for word, _ in word_freq.most_common(top_n)]
            
    except Exception as e:
        print(f"Özet tabanlı anahtar kelime çıkarma hatası: {str(e)}")
        return []

def extract_technical_terms(text, domain_terms, top_n=10):
    """Metinden teknik terimleri çıkar"""
    found_terms = []
    

    for term in domain_terms:

        pattern = r'\b' + re.escape(term) + r'\b'
        matches = re.findall(pattern, text.lower())
        

        if matches:
            found_terms.append((term, len(matches)))

    sorted_terms = sorted(found_terms, key=lambda x: x[1], reverse=True)
    return [term for term, _ in sorted_terms[:top_n]]

def extract_keywords_with_spacy(text, top_n=8):
    """
    Geliştirilmiş spaCy tabanlı anahtar kelime çıkarma
    1. Önce IEEE formatındaki anahtar kelimeleri kontrol et
    2. Sonra özet tabanlı anahtar kelimeleri çıkar
    3. Teknik terimler sözlüğü ile eşleştirme yap
    4. Son olarak spaCy NER ve noun chunk analizi yap
    """
    try:
        ieee_keywords = extract_ieee_keywords(text)
        if ieee_keywords and len(ieee_keywords) >= 3:
            print(f"IEEE anahtar kelimeleri bulundu: {ieee_keywords}")
            return ieee_keywords[:top_n]
        
        abstract_keywords = extract_abstract_based_keywords(text, top_n=top_n)
        
        technical_terms = [
            "neural network", "convolutional neural network", "cnn", "rnn", "lstm", 
            "deep learning", "machine learning", "supervised learning", "unsupervised learning",
            "eeg", "eeg signal", "signal processing", "feature extraction", "classification",
            "reinforcement learning", "natural language processing", "nlp", "computer vision",
            "support vector machine", "svm", "random forest", "decision tree", "naive bayes",
            "k-means", "clustering", "regression", "logistic regression", "linear regression",
            "transfer learning", "sentiment analysis", "time series", "data mining",
            "artificial intelligence", "ai", "pattern recognition", "image processing",
            "python", "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
            "data science", "big data", "cloud computing", "iot", "internet of things",
            "blockchain", "cryptography", "cyber security", "network security",
            "optimization", "genetic algorithm", "evolutionary algorithm", "fuzzy logic",
            "human-computer interaction", "hci", "virtual reality", "vr", "augmented reality", "ar",
            "database", "sql", "nosql", "data warehouse", "data visualization",
            "web development", "mobile development", "api", "microservices", "devops",
            "distributed systems", "parallel computing", "high performance computing", "hpc",
            "quantum computing", "graph theory", "algorithm", "data structure"
        ]
        
        domain_keywords = extract_technical_terms(text, technical_terms, top_n=top_n)
        
        nlp = spacy.load("en_core_web_sm")
        

        clean_text = re.sub(r'\[\d+\]|\d+\s*\|\s*Page|\bFig\.\s*\d+\b|\bTable\s*\d+\b', '', text)
        text_sample = clean_text[:min(50000, len(clean_text))]
        
        doc = nlp(text_sample)
        
        entities = [ent.text.lower() for ent in doc.ents 
                  if ent.label_ in ["ORG", "PRODUCT", "GPE", "LOC", "WORK_OF_ART"] 
                  and len(ent.text) > 3]
        
        noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks 
                      if 2 <= len(chunk.text.split()) <= 4]
        
        stop_patterns = [
            r"^\d+$", r"^fig\b", r"^figure\b", r"^table\b", r"^et al\b", 
            r"^ieee\b", r"^copyright\b", r"^abstract\b", r"^introduction\b",
            r"^conclusion\b", r"^references\b", r"^acknowledgment\b"
        ]
        
        candidates = []
        
        for phrase in noun_chunks:
            cleaned = clean_keyword(phrase)
            if len(cleaned) > 3 and not any(re.search(pattern, cleaned) for pattern in stop_patterns):
                candidates.append(cleaned)
        

        for entity in entities:
            cleaned = clean_keyword(entity)
            if len(cleaned) > 3 and not any(re.search(pattern, cleaned) for pattern in stop_patterns):
                candidates.append(cleaned)
        

        counter = Counter(candidates)
        spacy_keywords = [phrase for phrase, _ in counter.most_common(top_n * 2)]
        
        all_keywords = []
        
        if ieee_keywords:
            all_keywords.extend(ieee_keywords)
        
        all_keywords.extend([term for term in domain_keywords if term not in all_keywords])
        
        all_keywords.extend([term for term in abstract_keywords if term not in all_keywords])
        
        all_keywords.extend([term for term in spacy_keywords if term not in all_keywords])
        
        return all_keywords[:top_n]
        
    except Exception as e:
        print(f"Geliştirilmiş anahtar kelime çıkarma hatası: {str(e)}")
        # En azından boş dönme, hata alındığında yedek anahtar kelimeler döndür
        return ["error", "keyword extraction", "failed"]

def extract_keywords_from_pdf(drive_id, top_n=8):
    """Drive ID'si verilen PDF'den anahtar kelimeleri çıkar"""

    pdf_file = download_pdf_from_drive(drive_id)
    if not pdf_file:
        return ["pdf download error"]
    
    # PDF'den metni çıkar
    text = extract_text_from_pdf(pdf_file)
    if not text or len(text) < 100:  # Minimum bir uzunluk kontrolü ekle
        return ["no text extracted", "pdf extraction error"]
    
    ieee_keywords = extract_ieee_keywords(text)
    if ieee_keywords and len(ieee_keywords) >= 3:
        print(f"IEEE anahtar kelimeleri bulundu: {ieee_keywords}")
        return ieee_keywords[:top_n]
    
    abstract_keywords = extract_abstract_based_keywords(text, top_n=top_n)
    
    domain_keywords = extract_technical_terms(text, get_technical_terms(), top_n=top_n)
    
    combined_keywords = []
    combined_keywords.extend([term for term in domain_keywords if term not in combined_keywords])
    combined_keywords.extend([term for term in abstract_keywords if term not in combined_keywords])
    
    return combined_keywords[:top_n]

def extract_keywords_background(article_id, drive_id):
    """Arka planda anahtar kelimeleri çıkar ve veritabanına kaydet - hata yakalama geliştirildi"""
    try:
        article = UncensoredArticles.objects.get(article_drive_id=article_id)
        
        # Anahtar kelime kaydını al veya oluştur
        keyword_obj, created = ArticleKeywords.objects.get_or_create(
            article=article,
            defaults={
                'extraction_status': 'pending',
                'keywords': []
            }
        )
        
        keyword_obj.extraction_status = 'pending'
        keyword_obj.save()
        
        try:
            # Anahtar kelimeleri çıkar
            keywords = extract_keywords_from_pdf(drive_id)
            
            # Boş veya hata içeren anahtar kelimeler mi kontrol et
            if not keywords or any(kw.startswith("error") for kw in keywords):
                # PDF işleme hatası
                error_message = "PDF işleme veya anahtar kelime çıkarma hatası"
                keyword_obj.extraction_status = 'failed'
                keyword_obj.error_message = error_message
                keyword_obj.save()
                print(f"Makale #{article_id} için anahtar kelime çıkarma hatası: {error_message}")
                return {"keywords": [], "status": "failed", "error": error_message}
            
            # Başarılı sonuçları kaydet
            keyword_obj.keywords = keywords
            keyword_obj.extraction_status = 'completed'
            keyword_obj.error_message = None
            keyword_obj.save()
            
            print(f"Makale #{article_id} için anahtar kelimeler başarıyla çıkarıldı: {keywords}")
            return {"keywords": keywords, "status": "completed"}
        
        except Exception as e:
            error_message = f"Hata: {str(e)}"
            traceback_str = traceback.format_exc()
            print(f"Anahtar kelime çıkarma hatası (makale #{article_id}):\n{traceback_str}")
            
            keyword_obj.extraction_status = 'failed'
            keyword_obj.error_message = error_message
            keyword_obj.save()
            return {"keywords": [], "status": "failed", "error": error_message}
    
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Arka plan işlemi hatası (makale #{article_id}):\n{traceback_str}")
        return {"keywords": [], "status": "failed", "error": f"Arka plan işlemi hatası: {str(e)}"}

def get_technical_terms():
    """Teknik terimler sözlüğünü oluştur"""
    return [
        # AI/ML
        "neural network", "deep learning", "machine learning", "artificial intelligence", 
        "natural language processing", "nlp", "computer vision", "sentiment analysis",
        
        # Network & Communication
        "5g", "wireless network", "substrate integrated waveguide", "antenna", "waveguide",
        
        # Security
        "cybersecurity", "encryption", "security", "authentication", 
        
        # EEG/Brain
        "eeg", "brain computer interface", "brain signals", "electroencephalogram",
        "brain activity", "mental arithmetic", "cognitive",
        
        # Big Data
        "big data", "data analytics", "data mining", "cloud computing",
        
        # Engineering
        "signal processing", "wavelet transform", "fourier transform", "frequency analysis",
        
        # General technical
        "algorithm", "optimization", "simulation", "embedded systems"
    ]

def extract_technical_terms(text, domain_terms, top_n=10):
    """Metinden teknik terimleri çıkar"""
    found_terms = []
    
    for term in domain_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = re.findall(pattern, text.lower())
        
        if matches:
            found_terms.append((term, len(matches)))
    sorted_terms = sorted(found_terms, key=lambda x: x[1], reverse=True)
    return [term for term, _ in sorted_terms[:top_n]]


def get_technical_terms():
    """Teknik terimler sözlüğünü oluştur"""
    return [
        # AI/ML
        "neural network", "deep learning", "machine learning", "artificial intelligence", 
        "natural language processing", "nlp", "computer vision", "sentiment analysis",
        
        # Network & Communication
        "5g", "wireless network", "substrate integrated waveguide", "antenna", "waveguide",
        
        # Security
        "cybersecurity", "encryption", "security", "authentication", 
        
        # EEG/Brain
        "eeg", "brain computer interface", "brain signals", "electroencephalogram",
        "brain activity", "mental arithmetic", "cognitive",
        
        # Big Data
        "big data", "data analytics", "data mining", "cloud computing",
        
        # Engineering
        "signal processing", "wavelet transform", "fourier transform", "frequency analysis",
        
        # General technical
        "algorithm", "optimization", "simulation", "embedded systems"
    ]