"""
PDF Personal Information Anonymization - Using asterisks for specific personal information only
This only anonymizes names, emails, institutions, locations and phone numbers
"""
import fitz  # PyMuPDF
import re
import spacy
import io
import traceback
import os
import cv2
import numpy as np

try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    import sys
    print("spaCy model not found. Downloading...")
    from spacy.cli import download
    download("en_core_web_md")
    nlp = spacy.load("en_core_web_md")

email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
phone_pattern = re.compile(r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')

exclude_words = [
    'abstract', 'introduction', 'methodology', 'conclusion', 'references', 'table', 'figure',
    'analysis', 'result', 'discussion', 'appendix', 'journal', 'conference', 'proceedings',
    'review', 'article', 'paper', 'science', 'technology', 'engineering', 'mathematics',
    'theory', 'method', 'algorithm', 'system', 'model', 'data', 'research', 'study',
    'experiment', 'test', 'measure', 'evaluation', 'assessment', 'summary', 'results'
]

def blur_faces_in_pdf(pdf_content, article_id):
    """
    PDF içeriğindeki ilk ve son sayfalardaki yüzleri bulanıklaştır
    
    Args:
        pdf_content: PDF dosyasının içeriği (BytesIO)
        article_id: Makale ID'si (log için)
        
    Returns:
        BytesIO: Bulanıklaştırılmış PDF içeriği veya None (hata durumunda)
    """
    try:
        face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    
        if not os.path.exists(face_cascade_path):
            alt_path = r"C:\Users\{username}\AppData\Local\Programs\Python\Python3x\Lib\site-packages\cv2\data\haarcascade_frontalface_default.xml"
            print(f"Varsayılan cascade dosyası bulunamadı. Lütfen aşağıdaki yolu OpenCV kurulumunuza göre düzenleyin:\n{alt_path}")
            return
        if not os.path.exists(face_cascade_path):
            print(f"Cascade dosyası bulunamadı: {face_cascade_path}")
            return None
        
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        
        if face_cascade.empty():
            print("HATA: Haar cascade sınıflandırıcısı yüklenemedi!")
            return None
        
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
        except Exception as e:
            print(f"PDF açılırken hata oluştu: {e}")
            return None
            
        total_pages = len(doc)
        
        if total_pages == 0:
            print("PDF dosyası boş!")
            return None

        pages_to_process = [0]
        if total_pages > 1:
            pages_to_process.append(total_pages - 1)
        
        faces_found = 0
        
        for page_num in pages_to_process:
            print(f"Sayfa {page_num+1}/{total_pages} işleniyor...")
            
            page = doc[page_num]

            zoom_factor = 2.0
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if pix.n == 4: 
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:  # RGB formatı ise
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                print(f"Desteklenmeyen piksel formatı: {pix.n} kanal")
                continue
        
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            print(f"Sayfa {page_num+1}'de {len(faces)} yüz tespit edildi.")
            faces_found += len(faces)
            
            for (x, y, w, h) in faces:
                kernel_size = max(99, int(min(w, h) * 0.5))
                if kernel_size % 2 == 0:
                    kernel_size += 1
                    
                face_roi = img_bgr[y:y+h, x:x+w]
                
                blurred_face = cv2.GaussianBlur(face_roi, (kernel_size, kernel_size), 30)
                
                img_bgr[y:y+h, x:x+w] = blurred_face
            
            if len(faces) > 0:
                if pix.n == 4:
                    img_result = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGBA)
                else:
                    img_result = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                success, img_bytes = cv2.imencode(".png", img_result)
                
                if success:
                    page.clean_contents()
                    rect = page.rect
                    page.insert_image(rect, stream=img_bytes.tobytes())
                    print(f"Sayfa {page_num+1} güncellendi.")
        
        if faces_found > 0:
            try:
                output_buf = io.BytesIO()
                doc.save(output_buf)
                print(f"İşlem tamamlandı. Toplam {faces_found} yüz bulanıklaştırıldı.")
                doc.close()
                
                output_buf.seek(0)
                return output_buf
            except Exception as e:
                print(f"PDF kaydedilirken hata oluştu: {e}")
                doc.close()
                return None
        else:
            print("Hiç yüz tespit edilmedi, PDF değiştirilmedi.")
            pdf_content.seek(0)
            doc.close()
            return pdf_content
    except Exception as e:
        print(f"PDF işlenirken beklenmeyen hata: {e}")
        traceback.print_exc()
        return None

def create_asterisk_replacement(text):
    """
    Create an asterisk string with the same length as the input text
    Args:
        text: Original text to be replaced
    Returns:
        String of asterisks with same length
    """
    min_length = 5
    length = max(len(text), min_length)
    return '*' * length

def should_anonymize(text):
    """
    Determine if text should be anonymized based on content and context
    Args:
        text: Text to check
    Returns:
        Boolean indicating whether to anonymize
    """
    if text.lower() in exclude_words:
        return False
    
    if text.isupper() and len(text.split()) >= 3:
        return False
    
    if re.match(r'^(Fig\.|Figure|Table|Chart|Graph)\s+\d+', text, re.IGNORECASE):
        return False
    
    if re.match(r'^[\d\s\-\.\/]+$', text):
        return False
    
    return True

def anonymize_personal_info_in_pdf(pdf_content, article_id=None):
    """
    Find specific personal information and replace with asterisks
    Only anonymizes names, emails, institutions, locations and phone numbers
    
    Args:
        pdf_content: PDF content (BytesIO)
        article_id: Article ID (for logging)
        
    Returns:
        BytesIO: Anonymized PDF content or None (in case of error)
    """
    try:
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return None
            
        total_pages = len(doc)
        
        if total_pages == 0:
            print("PDF file is empty!")
            return None
        
        total_replacements = 0
        personal_info_found = []
        
        for page_num in range(total_pages):
            print(f"Scanning page {page_num+1}/{total_pages} for personal information...")
            
            page = doc[page_num]
            
            page_text = page.get_text()
            if not page_text:
                continue
                
            personal_info_items = []
            
            try:
                doc_nlp = nlp(page_text)
                
                for ent in doc_nlp.ents:
                    if not should_anonymize(ent.text):
                        continue
                        
                    if ent.label_ == "PERSON":
                        if len(ent.text.split()) >= 2 or ' ' in ent.text:
                            asterisks = create_asterisk_replacement(ent.text)
                            personal_info_items.append((ent.text, asterisks))
                            personal_info_found.append(f"PERSON: {ent.text}")
                    
                    elif ent.label_ == "ORG":
                        org_keywords = ['university', 'institute', 'college', 'school', 'department',
                                       'lab', 'laboratory', 'center', 'research', 'ltd', 'tech']
                        
                        if any(keyword in ent.text.lower() for keyword in org_keywords) or "of " in ent.text:
                            skip_keywords = ['journal', 'conference', 'proceedings', 'society']
                            if not any(kw in ent.text.lower() for kw in skip_keywords):
                                asterisks = create_asterisk_replacement(ent.text)
                                personal_info_items.append((ent.text, asterisks))
                                personal_info_found.append(f"ORG: {ent.text}")
                    
                    elif ent.label_ in ["GPE", "LOC"]:
                        if len(ent.text) > 3 and not ent.text.isdigit():
                            asterisks = create_asterisk_replacement(ent.text)
                            personal_info_items.append((ent.text, asterisks))
                            personal_info_found.append(f"{ent.label_}: {ent.text}")
            except Exception as e:
                print(f"Error in NER processing: {e}")
                traceback.print_exc()
            
            try:
                for match in re.finditer(email_pattern, page_text):
                    email = match.group(0)
                    asterisks = create_asterisk_replacement(email)
                    personal_info_items.append((email, asterisks))
                    personal_info_found.append(f"EMAIL: {email}")
                
                for match in re.finditer(phone_pattern, page_text):
                    phone = match.group(0)
                    asterisks = create_asterisk_replacement(phone)
                    personal_info_items.append((phone, asterisks))
                    personal_info_found.append(f"PHONE: {phone}")
            except Exception as e:
                print(f"Error in regex pattern matching: {e}")
                traceback.print_exc()
            
            if personal_info_items:
                total_replacements += len(personal_info_items)
                
                personal_info_items.sort(key=lambda x: len(x[0]), reverse=True)
                
                new_doc = fitz.open()
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                new_page.show_pdf_page(new_page.rect, doc, page_num)
                
                try:
                    text_blocks = page.get_text("dict")["blocks"]
                    for block in text_blocks:
                        if "lines" not in block:
                            continue
                            
                        for line in block["lines"]:
                            if "spans" not in line:
                                continue
                                
                            for span in line["spans"]:
                                original_text = span["text"]
                                replacement_text = original_text
                                made_replacements = False
                                
                                is_heading = span.get("size", 0) > 14
                                if is_heading:
                                    continue
                                
                                for info_text, asterisks in personal_info_items:
                                    if info_text in replacement_text:
                                        replacement_text = replacement_text.replace(info_text, asterisks)
                                        made_replacements = True
                                
                                if made_replacements:
                                    rect = fitz.Rect(span["bbox"])
                                    new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    font_size = span["size"]
                                    new_page.insert_text(
                                        rect.tl,
                                        replacement_text,
                                        fontsize=font_size
                                    )
                    doc.delete_page(page_num)
                    doc.insert_pdf(new_doc, from_page=0, to_page=0, start_at=page_num)

                    new_doc.close()
                
                except Exception as inner_e:
                    print(f"Error replacing text with asterisks: {inner_e}")
                    traceback.print_exc()
                    if new_doc:
                        new_doc.close()
        
        if total_replacements > 0:
            try:
                output_buf = io.BytesIO()
                doc.save(output_buf)
                print(f"Process completed. Total {total_replacements} personal information items anonymized.")
                print("Personal information found:")
                for info in personal_info_found[:10]:
                    print(f"- {info}")
                if len(personal_info_found) > 10:
                    print(f"... and {len(personal_info_found) - 10} more items.")
                doc.close()
                
                output_buf.seek(0)
                return output_buf
            except Exception as e:
                print(f"Error saving PDF: {e}")
                traceback.print_exc()
                doc.close()
                return None
        else:
            print("No personal information detected, PDF unchanged.")
            pdf_content.seek(0)
            doc.close()
            return pdf_content
            
    except Exception as e:
        print(f"Unexpected error processing PDF: {e}")
        traceback.print_exc()
        return None

def anonymize_pdf_complete(pdf_content, article_id=None):
    """
    Performs both face blurring and personal information anonymization
    
    Args:
        pdf_content: PDF content (BytesIO)
        article_id: Article ID (for logging)
        
    Returns:
        BytesIO: Processed PDF content or None (in case of error)
    """
    try:
        blurred_pdf = blur_faces_in_pdf(pdf_content, article_id)
        
        if blurred_pdf is None:
            print("Face blurring failed, using original PDF for personal information anonymization")
            blurred_pdf = pdf_content
            blurred_pdf.seek(0)
        
        anonymized_pdf = anonymize_personal_info_in_pdf(blurred_pdf, article_id)
        
        return anonymized_pdf
    except Exception as e:
        print(f"Unexpected error processing PDF: {e}")
        traceback.print_exc()
        return None