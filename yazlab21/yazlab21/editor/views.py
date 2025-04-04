from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse,FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q


import os
import io
import json
import threading
import tempfile
import traceback


from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


import fitz
import cv2
import numpy as np


from author.models import UncensoredArticles, BlurredPDF, Messages
from referee.models import referee, RefereeEvaluation
from logs.models import log
from .models import EditorReply, ArticleKeywords

from .keyword_extractor import extract_keywords_background
from .keyword_based_classifier import *

PROCESSING_ARTICLES = {}

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

SOURCE_FOLDER_ID = "1B_MvMlKPYG-LKcbomQCjWYvoWyd1cJ73"
TARGET_FOLDER_ID = "1XoQvL3T6EJ2K3h6vQB29DhieStdhq6r-"


def authenticate():
    """Google Drive API için kimlik doğrulama"""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def editor_page(request):
    """Editör ana sayfası (makale listesi, vb.)"""
    articles = UncensoredArticles.objects.all()

    for article in articles:
        try:
            keyword_obj, created = ArticleKeywords.objects.get_or_create(
                article=article,
                defaults={
                    'extraction_status': 'pending',
                    'keywords': [],
                    'retry_count': 0
                }
            )
            if keyword_obj.extraction_status == 'completed':
                continue

            if keyword_obj.extraction_status in ['pending', 'failed']:
                article_key = f"article_{article.article_drive_id}"


                if not PROCESSING_ARTICLES.get(article_key, False):

                    PROCESSING_ARTICLES[article_key] = True

                    if keyword_obj.extraction_status == 'failed':
                        retry_count = getattr(keyword_obj, 'retry_count', 0)
                        if retry_count >= 3:
                            continue
                        else:
                            keyword_obj.retry_count = retry_count + 1
                            keyword_obj.extraction_status = 'pending'
                            keyword_obj.save()

                    thread = threading.Thread(
                        target=modified_extract_keywords_background,
                        args=(article.article_drive_id, article.article_drive_id, article_key)
                    )
                    thread.daemon = True
                    thread.start()

        except Exception as e:
            print(f"Makale ön işleme hatası (makale #{article.article_drive_id}): {str(e)}")

    context = {
        'article_list': articles,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/editor_page.html', context)


def modified_extract_keywords_background(article_id, drive_id, processing_key):
    """
    extract_keywords_background fonksiyonunu çağırıp
    işlem bittiğinde PROCESSING_ARTICLES kilidini kapatır.
    """
    try:
        extract_keywords_background_with_completion(article_id, drive_id)
    except Exception as e:
        try:
            article = UncensoredArticles.objects.get(pk=article_id)
            keyword_obj = ArticleKeywords.objects.get(article=article)
            keyword_obj.extraction_status = 'failed'
            keyword_obj.error_message = str(e)
            keyword_obj.save()
        except Exception as inner_e:
            print(f"İç hata: {str(inner_e)}")
        print(f"Anahtar kelime çıkarma hatası: {str(e)}")
        traceback.print_exc()
    finally:
        PROCESSING_ARTICLES[processing_key] = False

def extract_keywords_background_with_completion(article_id, drive_id):
    """
    Orijinal 'extract_keywords_background' fonksiyonunuzu çağırır
    ve başarıyla bitince ArticleKeywords kaydını 'completed' yapar.
    """
    extracted_data = extract_keywords_background(article_id, drive_id)
    article = UncensoredArticles.objects.get(pk=article_id)
    keyword_obj = ArticleKeywords.objects.get(article=article)

    keyword_obj.extraction_status = 'completed'
    keyword_obj.error_message = ''
    if extracted_data:
        keyword_obj.keywords = extracted_data.get("keywords", [])
    keyword_obj.save()


@csrf_exempt
@require_POST
def get_article_keywords(request):
    """Makale ID'ye göre anahtar kelimeleri döndürme (AJAX)"""
    try:
        data = json.loads(request.body)
        article_id = data.get('article_id')
        if not article_id:
            return JsonResponse({'success': False, 'message': 'Makale ID gereklidir'})

        article = get_object_or_404(UncensoredArticles, article_drive_id=article_id)
        keyword_obj, created = ArticleKeywords.objects.get_or_create(
            article=article,
            defaults={'extraction_status': 'pending', 'keywords': []}
        )

        if keyword_obj.extraction_status == 'completed':
            return JsonResponse({
                'success': True,
                'keywords': keyword_obj.keywords or [],
                'category': getattr(keyword_obj, 'category', None),
                'category_keywords': getattr(keyword_obj, 'category_keywords', []),
                'status': 'completed',
                'error_message': None
            })

        article_key = f"article_{article.article_drive_id}"
        is_processing = PROCESSING_ARTICLES.get(article_key, False)

        if is_processing:
            return JsonResponse({
                'success': True,
                'status': 'processing',
                'message': 'Anahtar kelimeler çıkarılıyor, lütfen bekleyin...',
                'keywords': keyword_obj.keywords or []
            })


        if keyword_obj.extraction_status in ['pending', 'failed']:
            if keyword_obj.extraction_status == 'failed':
                retry_count = getattr(keyword_obj, 'retry_count', 0)
                if retry_count >= 3:
                    return JsonResponse({
                        'success': True,
                        'message': 'Anahtar kelime çıkarma işlemi maksimum deneme sayısına ulaştı',
                        'status': 'completed',
                        'keywords': [],
                        'error_message': getattr(keyword_obj, 'error_message', 'Bilinmeyen hata')
                    })
                keyword_obj.retry_count = retry_count + 1
                keyword_obj.extraction_status = 'pending'
                keyword_obj.save()

            PROCESSING_ARTICLES[article_key] = True
            thread = threading.Thread(
                target=modified_extract_keywords_background,
                args=(article.article_drive_id, article.article_drive_id, article_key)
            )
            thread.daemon = True
            thread.start()

            return JsonResponse({
                'success': True,
                'status': 'processing',
                'message': 'Anahtar kelime çıkarma işlemi başlatıldı',
                'keywords': keyword_obj.keywords or []
            })

        return JsonResponse({
            'success': True,
            'keywords': keyword_obj.keywords or [],
            'category': getattr(keyword_obj, 'category', None),
            'category_keywords': getattr(keyword_obj, 'category_keywords', []),
            'status': keyword_obj.extraction_status,
            'error_message': getattr(keyword_obj, 'error_message', None)
        })

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Anahtar kelime getirme hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({
            'success': False, 
            'message': str(e),
            'details': traceback_str,
            'status': 'completed'
        })


@csrf_exempt
def get_blurred_status(request, article_drive_id):
    """
    Makalenin bulanıklaştırma durumunu kontrol eder.
    """
    try:
        article = get_object_or_404(UncensoredArticles, pk=article_drive_id)

        try:
            blurred_pdf = BlurredPDF.objects.get(original_article=article)
            return JsonResponse({
                'success': True,
                'status': 'completed',
                'blurred_file_id': blurred_pdf.blurred_drive_id
            })
        except BlurredPDF.DoesNotExist:
            return JsonResponse({
                'success': True,
                'status': 'processing',
                'blurred_file_id': None
            })
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Blurred status hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({
            'success': False,
            'message': str(e),
            'details': traceback_str
        }, status=500)


def download_pdf(request, drive_id):
    """Google Drive'dan PDF dosyasını indir ve kullanıcıya sun"""
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = service.files().get(fileId=drive_id, fields="name").execute()
        file_name = file_metadata.get("name", "makale.pdf")
        
        request_obj = service.files().get_media(fileId=drive_id)
        pdf_file = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_file, request_obj)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        pdf_file.seek(0)
        
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
        
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"PDF indirme hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({
            'success': False,
            'message': f'Dosya indirme hatası: {str(e)}'
        }, status=500)

def view_article(request, drive_id, blurred=False):
    """PDF dosyasını görüntülemek için"""
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        
        request_obj = service.files().get_media(fileId=drive_id)
        pdf_file = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_file, request_obj)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        pdf_file.seek(0)
        
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        return response
        
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"PDF görüntüleme hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({
            'success': False,
            'message': f'Dosya görüntüleme hatası: {str(e)}'
        }, status=500)

    """Yazar mesajlarını göster"""
    # Mesajları en yeniden eskiye sırala
    messages_list = Messages.objects.all().order_by('-message_time')
    
    # Sayfalama
    paginator = Paginator(messages_list, 10)  # Her sayfada 10 mesaj
    page = request.GET.get('page', 1)
    messages = paginator.get_page(page)
    
    context = {
        'messages': messages,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/author_messages.html', context)


    """Yazara yanıt gönder"""
    try:
        data = json.loads(request.body)
        to = data.get('to')
        subject = data.get('subject')
        content = data.get('content')
        original_message_id = data.get('original_message_id')
        
        # Gerekli alanların kontrolü
        if not all([to, subject, content, original_message_id]):
            return JsonResponse({
                'success': False, 
                'message': 'Tüm gerekli alanları doldurun (alıcı, konu, içerik)'
            })
        
        # Orjinal mesajı kontrol et
        original_message = get_object_or_404(Messages, id=original_message_id)
        
        # Yanıtı kaydet
        reply = EditorReply(
            original_message=original_message,
            reply_to=to,
            reply_subject=subject,
            reply_text=content,
            reply_time=timezone.now()
        )
        reply.save()
        
        # Orijinal mesajı okundu olarak işaretle
        original_message.is_read = True
        original_message.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Yanıt gönderme hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({'success': False, 'message': str(e)})


@csrf_exempt
@require_POST
def hide_personal_info(request):
    """
    "Belgeyi Anonimleştir" butonuna basıldığında tetiklenir.
    Arka planda blur işlemini başlatır.
    """
    try:
        data = request.POST or json.loads(request.body)
        article_drive_id = data.get('article_id')
        if not article_drive_id:
            return JsonResponse({'success': False, 'message': 'Makale ID gereklidir'})

        article = get_object_or_404(UncensoredArticles, pk=article_drive_id)

        if hasattr(article, 'blurred_pdf'):
            return JsonResponse({
                'success': True,
                'message': 'Zaten anonimleştirilmiş.',
                'status': 'completed',
                'blurred_file_id': article.blurred_pdf.blurred_drive_id
            })

        thread = threading.Thread(
            target=process_personal_info_background,
            args=(article_drive_id,)
        )
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'success': True,
            'message': 'Yüzleri blurlama işlemi başlatıldı',
            'status': 'processing'
        })
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Hata (hide_personal_info): {str(e)}\n{traceback_str}")
        return JsonResponse({'success': False, 'message': str(e)})


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
            elif pix.n == 3:
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


def process_personal_info_background(article_drive_id):
    """
    1) Drive'dan belirli bir makale PDF'ini indir (article_drive_id).
    2) İlk/son sayfayı rasterize edip OpenCV ile yüz bulanıklaştır.
    3) spaCy ve regex ile kişisel bilgileri tespit edip RSA ile şifrele
    4) Yeni PDF'i Drive'da TARGET_FOLDER_ID içine yükle, ID'sini BlurredPDF tablosuna kaydet.
    """
    try:
        article = UncensoredArticles.objects.get(pk=article_drive_id)

        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        request_obj = service.files().get_media(fileId=article_drive_id)
        pdf_file = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_file, request_obj)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        pdf_file.seek(0)

        from .pdf_info_anonymizer import anonymize_pdf_complete
        
        anonymized_pdf = anonymize_pdf_complete(pdf_file, article_drive_id)
        
        if anonymized_pdf is None:
            print(f"[HATA] Makale {article_drive_id} için anonimleştirme başarısız oldu.")
            return

        file_metadata = {
            'name': f"anonymized_{article_drive_id}.pdf",
            'parents': [TARGET_FOLDER_ID]
        }

        log_message = f"{article.article_name} isimli makalede sansürleme ve kişisel bilgi anonimleştirme işlemi yapıldı."
        
        log.objects.create(
            log_type="Editör",
            log_message=log_message
        )

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(anonymized_pdf.getvalue())
        temp_file.close()
        
        media = MediaFileUpload(temp_file.name, mimetype='application/pdf')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        new_file_id = file.get('id')
        print(f"[OK] Anonimleştirilmiş PDF Drive ID = {new_file_id}")

        BlurredPDF.objects.create(
            original_article=article,
            blurred_drive_id=new_file_id,
            is_referee_assigned=False,
            referee_name="" 
        )

        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
            
        print(f"[OK] Makale {article_drive_id} için anonimleştirme işlemi tamamlandı.")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Hata (process_personal_info_background): {str(e)}\n{traceback_str}")

@csrf_exempt
@require_POST
def get_referees_by_category(request):
    """Kategoriye göre hakemleri getiren AJAX view"""
    try:
        data = json.loads(request.body)
        category = data.get('category')
        
        if not category:
            referees = referee.objects.all()
        else:
            category_prefix = category.split('-')[0].strip() if '-' in category else ''
            
            if category_prefix:
                matching_referees = referee.objects.filter(referee_branch__startswith=category_prefix)
                other_referees = referee.objects.exclude(referee_branch__startswith=category_prefix)
                
                referees = list(matching_referees) + list(other_referees)
            else:
                referees = referee.objects.all()
        
        referee_data = []
        for ref in referees:
            referee_data.append({
                'id': ref.id,
                'name': ref.referee_name,
                'branch': ref.referee_branch
            })
        
        return JsonResponse({
            'success': True,
            'referees': referee_data
        })
    
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False, 
            'message': str(e),
            'details': traceback.format_exc()
        })
    
def assign_referee_page(request):
    """Hakem atama sayfası - makalelere ait anahtar kelime ve kategori bilgileri ile birlikte"""
    articles = UncensoredArticles.objects.all()

    articles_with_data = []
    for article in articles:
        article_data = {
            'article': article,
            'keywords': [],
            'keywords_status': 'not_started',
            'category': None,
            'category_keywords': []
        }

        try:
            keyword_obj = ArticleKeywords.objects.get(article=article)
            article_data['keywords'] = keyword_obj.keywords
            article_data['keywords_status'] = keyword_obj.extraction_status

            if keyword_obj.extraction_status == 'completed' and keyword_obj.keywords:
                category, matched_keywords = classify_by_keywords(keyword_obj.keywords)
                article_data['category'] = category
                article_data['category_keywords'] = matched_keywords
        except ArticleKeywords.DoesNotExist:
            pass

        articles_with_data.append(article_data)

    context = {
        'article_list': articles_with_data,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/assign_referee.html', context)

@csrf_exempt
@require_POST
def assign_referee_action(request):
    """Makaleye hakem atama işlemi (AJAX POST)"""
    try:
        data = json.loads(request.body)
        article_id = data.get('article_id')
        referee_id = data.get('referee_id')
        
        if not article_id or not referee_id:
            return JsonResponse({
                'success': False, 
                'message': 'Makale ID ve Hakem ID gereklidir'
            })

        article = get_object_or_404(UncensoredArticles, article_drive_id=article_id)
        referee_obj = get_object_or_404(referee, id=referee_id)

        blurred_pdf, created = BlurredPDF.objects.get_or_create(
            original_article=article,
            defaults={'referee_name': 'Hakem ataması bekleniyor.', 'blurred_drive_id': ''}
        )
        
        blurred_pdf.is_referee_assigned = True
        blurred_pdf.referee_name = referee_obj.referee_name
        blurred_pdf.save()

        article.article_status = "Hakem Ataması yapıldı"
        article.save()

        return JsonResponse({
            'success': True,
            'message': f'{referee_obj.referee_name} başarıyla {article.article_name} makalesine hakem olarak atandı.'
        })
    
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False, 
            'message': str(e),
            'details': traceback.format_exc()
        })

def referee_list_page(request):
    """Hakem listesini görüntüleme sayfası"""
    referees = referee.objects.all()
    
    context = {
        'referees': referees,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/referee_list.html', context)

def assign_referee(request):
    """Hakem atama sayfası - anahtar kelimeleri ve kategorileri göster"""
    articles = UncensoredArticles.objects.all().prefetch_related('blurred_pdf')
    
    articles_with_data = []
    for article in articles:
        article_data = {
            'article': article,
            'keywords': [],
            'keywords_status': 'not_started',
            'category': None,
            'category_keywords': []
        }
        
        try:
            keyword_obj = ArticleKeywords.objects.get(article=article)
            article_data['keywords'] = keyword_obj.keywords
            article_data['keywords_status'] = keyword_obj.extraction_status
            
            if keyword_obj.extraction_status == 'completed' and keyword_obj.keywords:
                category, matched_keywords = classify_by_keywords(keyword_obj.keywords)
                article_data['category'] = category
                article_data['category_keywords'] = matched_keywords
        except ArticleKeywords.DoesNotExist:
            pass
        
        articles_with_data.append(article_data)
    
    context = {
        'article_list': articles_with_data,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/assign_referee.html', context)


def author_messages(request):

    """Yazar mesajlarını göster"""
    messages_list = Messages.objects.all().order_by('-message_time')
    
    paginator = Paginator(messages_list, 10)
    page = request.GET.get('page', 1)
    messages = paginator.get_page(page)
    
    context = {
        'messages': messages,
        'unread_messages_count': Messages.objects.filter(is_read=False).count()
    }
    return render(request, 'editor/author_messages.html', context)

@csrf_exempt
@require_POST
def send_reply_to_author(request):
    """Yazara yanıt gönder"""
    try:
        data = json.loads(request.body)
        to = data.get('to')
        subject = data.get('subject')
        content = data.get('content')
        original_message_id = data.get('original_message_id')
        
        if not all([to, subject, content]):
            return JsonResponse({
                'success': False, 
                'message': 'Tüm gerekli alanları doldurun (alıcı, konu, içerik)'
            })
        
        reply_message = Messages(
            message_sender_email=to,
            message_title=subject,
            message_text=content,
            message_time=timezone.now(),
            is_from_author=False
        )
        reply_message.save()
        
        return JsonResponse({'success': True, 'message': 'Mesaj başarıyla gönderildi'})
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Yanıt gönderme hatası: {str(e)}\n{traceback_str}")
        return JsonResponse({'success': False, 'message': str(e)})

def list_articles(request):
    """
    Editörün, hakemlerin değerlendirdiği makaleleri onaylayabileceği sayfa
    """
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    evaluations = RefereeEvaluation.objects.select_related(
        'blurred_pdf__original_article'
    ).order_by('-evaluation_date')
    
    if status:
        evaluations = evaluations.filter(decision=status)
    
    if search:
        evaluations = evaluations.filter(
            Q(blurred_pdf__original_article__article_name__icontains=search) | 
            Q(blurred_pdf__original_article__article_owner__icontains=search) |
            Q(blurred_pdf__referee_name__icontains=search)
        )
    
    paginator = Paginator(evaluations, 10)
    page_number = request.GET.get('page', 1)
    evaluations_page = paginator.get_page(page_number)
    
    context = {
        'evaluations': evaluations_page,
        'status': status,
        'search': search
    }
    
    return render(request, 'editor/list_articles.html', context)


def approve_evaluation(request, evaluation_id):
    """
    Hakem değerlendirmesini onaylama işlemi
    Bu fonksiyon is_evaluation_sent değerini True olarak günceller
    """
    if request.method == 'POST':
        evaluation = get_object_or_404(RefereeEvaluation, id=evaluation_id)
        
        evaluation.is_evaluation_sent = True
        evaluation.save()
        
        original_article = evaluation.blurred_pdf.original_article
        decision_text = "Başarılı" if evaluation.decision == "success" else "Reddedildi"
        original_article.article_status = f"Makale Değerlendirmesi Tamamlandı. Değerlendirme: {decision_text}"
        original_article.article_finish = True
        original_article.save()
        
        log_message = f"Editör {original_article.article_owner} tarafından {original_article.article_name} adlı makalenin değerlendirmesi onaylandı. Sonuç: {decision_text}"
        log.objects.create(
            log_type="Editör",
            log_message=log_message
        )
        
        messages.success(request, "Değerlendirme başarıyla onaylandı ve ilgili kişiler bilgilendirildi.")
        
        return redirect('editor:list_articles')
    
    return redirect('editor:list_articles')

def download_evaluation_pdf(request, evaluation_id):
    """
    Hakem değerlendirme PDF'ini indirme
    """
    evaluation = get_object_or_404(RefereeEvaluation, id=evaluation_id)
    
    if not evaluation.evaluation_pdf_id:
        messages.error(request, "Bu değerlendirme için PDF dosyası bulunmamaktadır.")
        return redirect('editor:list_articles')
    
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        
        file_id = evaluation.evaluation_pdf_id
        
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'evaluation.pdf')
        
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return FileResponse(fh, as_attachment=True, filename=file_name)
        
    except Exception as e:
        messages.error(request, f"Dosya indirilirken bir hata oluştu: {str(e)}")
        return redirect('editor:list_articles')
    

def log_view(request):
    """
    View function to display system logs.
    Lists all log entries sorted by date (newest first).
    """
    logs = log.objects.all().order_by('-log_date')
    
    context = {
        'logs': logs,
        'unread_messages_count': 0,
    }
    
    return render(request, 'editor/log_page.html', context)