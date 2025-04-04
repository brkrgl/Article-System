from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from logs.models import *

from .models import referee, RefereeEvaluation
from author.models import BlurredPDF, UncensoredArticles
from editor.models import *
from referee.models import *
import mimetypes

# Dosya işleme 
import os
import tempfile
import requests
from datetime import datetime
from io import BytesIO
import json
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Google Drive API
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account

# Drive klasör ID
ORIGINAL_PDF_FOLDER = "1B_MvMlKPYG-LKcbomQCjWYvoWyd1cJ73"  # Orjinal PDF'lerin bulunduğu klasör
EVALUATED_PDF_FOLDER = "1OK8NPGrUHdc9ksUpoyKCiOQqVhKKrNxY"  # Değerlendirilen PDF'lerin yükleneceği klasör

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def authenticate():
    """Google Drive API için kimlik doğrulama"""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def dashboard(request):
    """
    Hakem kontrol paneli görünümü
    """
    # İstatistikler
    assigned_count = 0
    completed_count = 0
    pending_count = 0
    recent_evaluations = []
    user_referee = None
    
    # Tüm değerlendirmeleri al
    recent_evaluations = RefereeEvaluation.objects.all().order_by('-evaluation_date')[:5]
    
    # Tamamlanmış değerlendirme sayısı
    completed_count = RefereeEvaluation.objects.count()
    
    assigned_count = BlurredPDF.objects.filter(is_referee_assigned=True).count()

    pending_count = assigned_count - completed_count
    
    if request.user.is_authenticated:
        try:

            user_referee = referee.objects.filter(referee_name__icontains=request.user.username).first()
            
            if user_referee:
                # Bu hakeme atanmış makaleleri bul
                assigned_pdfs = BlurredPDF.objects.filter(
                    referee_name=user_referee.referee_name,
                    is_referee_assigned=True
                )

                assigned_count = assigned_pdfs.count()
                completed_evals = RefereeEvaluation.objects.filter(
                    blurred_pdf__in=assigned_pdfs
                )
                completed_count = completed_evals.count()
                pending_count = assigned_count - completed_count
                
                recent_evaluations = completed_evals.order_by('-evaluation_date')[:5]
                
        except Exception as e:
            print(f"Hakem bilgisi alınırken hata: {str(e)}")
    
    context = {
        'user_referee': user_referee,
        'assigned_count': assigned_count,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'recent_evaluations': recent_evaluations,
    }
    
    return render(request, "referee/dashboard.html", context)

def referee_page(request):
    """
    Ana hakem sayfası
    """
    categories = {
        "Yapay Zeka ve Makine Öğrenimi": ["Derin öğrenme", "Doğal dil işleme", "Bilgisayarla görü", "Generatif yapay zeka"],
        "İnsan-Bilgisayar Etkileşimi": ["Beyin-bilgisayar arayüzleri (BCI)", "Kullanıcı deneyimi tasarımı", "Artırılmış ve sanal gerçeklik (AR/VR)"],
        "Büyük Veri ve Veri Analitiği": ["Veri madenciliği", "Veri görselleştirme", "Veri işleme sistemleri (Hadoop, Spark)", "Zaman serisi analizi"],
        "Siber Güvenlik": ["Şifreleme algoritmaları", "Güvenli yazılım geliştirme", "Ağ güvenliği", "Kimlik doğrulama sistemleri", "Adli bilişim"],
        "Ağ ve Dağıtık Sistemler": ["5G ve yeni nesil ağlar", "Bulut bilişim", "Blockchain teknolojisi", "P2P ve merkeziyetsiz sistemler"]
    }
    
    specializations = []
    for category, topics in categories.items():
        for topic in topics:
            specializations.append(f"{category} - {topic}")
    
    referees = []
    for i in range(1, 26):
        specialization_index = (i - 1) % len(specializations)
        
        referee_item = {
            "id": i,
            "name": f"Hakem-{i}",
            "specialization": specializations[specialization_index]
        }
        referees.append(referee_item)
    
    context = {
        "referees": referees
    }
    
    return render(request, "referee/referee_page.html", context)


def referee_list(request):
    """
    Hakem listesini görüntüleme sayfası
    """
    referees = referee.objects.all().order_by('referee_name')

    branch_stats = {}
    for ref in referees:
        branch = ref.referee_branch.split(' - ')[0] if ' - ' in ref.referee_branch else ref.referee_branch
        if branch in branch_stats:
            branch_stats[branch] += 1
        else:
            branch_stats[branch] = 1
    
    context = {
        'referees': referees,
        'branch_stats': branch_stats,
        'total_referees': referees.count()
    }
    
    return render(request, 'referee/referee_list.html', context)


def referee_info(request, referee_id):
    """
    Belirli bir hakemin bilgilerini ve atanmış makalelerini görüntüler
    """
    referee_obj = get_object_or_404(referee, id=referee_id)

    assigned_pdfs = BlurredPDF.objects.filter(
        referee_name=referee_obj.referee_name,
        is_referee_assigned=True
    )

    assigned_articles = []
    for pdf in assigned_pdfs:
        assigned_articles.append(pdf.original_article)
    
    context = {
        'referee': referee_obj,
        'assigned_articles': assigned_articles,
    }
    
    return render(request, 'referee/referee_info.html', context)


def referee_assignment(request, referee_id, article_id):
    """
    Hakemin makale değerlendirme sayfasını görüntüler
    """
    referee_obj = get_object_or_404(referee, id=referee_id)
    article = get_object_or_404(UncensoredArticles, article_drive_id=article_id)

    blurred_pdf = get_object_or_404(BlurredPDF, original_article=article)

    if blurred_pdf.referee_name != referee_obj.referee_name:
        messages.error(request, "Bu makale size atanmamış.")
        return redirect(reverse('referee:referee_info', args=[referee_id]))
    
    context = {
        'referee': referee_obj,
        'article': article,
        'blurred_pdf': blurred_pdf,
        'back_url': reverse('referee:referee_info', args=[referee_id]),
    }
    
    return render(request, 'referee/evaluate_article.html', context)


@csrf_exempt
def submit_evaluation(request, pdf_id):
    """
    Hakem değerlendirmesini alır ve PDF olarak kaydeder
    """
    blurred_pdf = get_object_or_404(BlurredPDF, id=pdf_id)
    
    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                decision = data.get('decision')
                comments = data.get('comments')
                merge_with_original = data.get('merge_with_original', True)

                if not decision or not comments:
                    return JsonResponse({'status': 'error', 'message': 'Tüm alanları doldurun.'}, status=400)

                evaluation_result = process_evaluation(blurred_pdf, decision, comments, merge_with_original)
                
                if evaluation_result['success']:
                    return JsonResponse({
                        'status': 'success', 
                        'message': evaluation_result['message']
                    })
                else:
                    return JsonResponse({
                        'status': 'error', 
                        'message': evaluation_result['message']
                    }, status=500)
                
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        
        else:
            decision = request.POST.get('decision')
            comments = request.POST.get('comments')
            
            if not decision or not comments:
                messages.error(request, 'Lütfen tüm alanları doldurun.')
                return redirect('referee:evaluate_article', pdf_id=pdf_id)
            
            try:
                evaluation_result = process_evaluation(blurred_pdf, decision, comments, True)
                
                if evaluation_result['success']:
                    messages.success(request, evaluation_result['message'])
                else:
                    messages.error(request, evaluation_result['message'])
                
                return redirect('referee:dashboard')
                
            except Exception as e:
                messages.error(request, f'Hata oluştu: {str(e)}')
                return redirect('referee:evaluate_article', pdf_id=pdf_id)
            
    return render(request, 'referee/evaluate_article.html', {'blurred_pdf': blurred_pdf})


def process_evaluation(blurred_pdf, decision, comments, merge_with_original=True):
    """
    Değerlendirme işlemini gerçekleştirir ve sonucu döndürür.
    
    Args:
        blurred_pdf: PDF nesnesi
        decision: Değerlendirme kararı (success/reject)
        comments: Değerlendirme yorumları
        merge_with_original: True ise orijinal PDF ile birleştirilir, False ise sadece değerlendirme PDF'i kullanılır
    """
    try:
        evaluation_pdf_path = create_evaluation_pdf(blurred_pdf, decision, comments)
        
        article = blurred_pdf.original_article
        article_drive_id = article.article_drive_id
        
        merged_pdf_path = None
        merged_pdf_name = f"{article.article_name}_{article.tracking_number}_degerlendirme.pdf"
        result = None
        
        if merge_with_original:
            try:
                print(f"Orijinal PDF aranıyor. Makale ID: {article_drive_id}")
                
                service = get_drive_service()
                
                found_file = None
                query = f"'{ORIGINAL_PDF_FOLDER}' in parents and name contains '{article_drive_id}'"
                results = service.files().list(q=query, fields="files(id, name)").execute()
                files = results.get('files', [])
                if files:
                    found_file = files[0]
                    print(f"Drive ID ile dosya bulundu: {found_file['name']}")
                if not found_file:
                    safe_name = article.article_name.replace("'", "").replace('"', '')
                    query = f"'{ORIGINAL_PDF_FOLDER}' in parents and name contains '{safe_name}'"
                    results = service.files().list(q=query, fields="files(id, name)").execute()
                    files = results.get('files', [])
                    if files:
                        found_file = files[0]
                        print(f"Makale adı ile dosya bulundu: {found_file['name']}")
                

                if not found_file:
                    query = f"'{ORIGINAL_PDF_FOLDER}' in parents and name contains '{article.tracking_number}'"
                    results = service.files().list(q=query, fields="files(id, name)").execute()
                    files = results.get('files', [])
                    if files:
                        found_file = files[0]
                        print(f"Takip numarası ile dosya bulundu: {found_file['name']}")
                

                if not found_file:
                    query = f"'{ORIGINAL_PDF_FOLDER}' in parents"
                    results = service.files().list(q=query, fields="files(id, name)", pageSize=10).execute()
                    files = results.get('files', [])
                    if files:
                        found_file = files[0]
                        print(f"Klasördeki ilk dosya seçildi: {found_file['name']}")
                
                if not found_file:
                    print("Orijinal PDF bulunamadı, sadece değerlendirme PDF'i kullanılacak")
                    result = upload_pdf_to_drive(evaluation_pdf_path, merged_pdf_name, folder_id=EVALUATED_PDF_FOLDER)
                else:
                    original_pdf_id = found_file['id']
                    print(f"Orijinal PDF indiriliyor: {found_file['name']}")
                    original_pdf = download_pdf_from_drive(original_pdf_id)

                    merged_pdf_path = merge_pdfs(original_pdf, evaluation_pdf_path)

                    result = upload_pdf_to_drive(merged_pdf_path, merged_pdf_name, folder_id=EVALUATED_PDF_FOLDER)
                    print(f"Birleştirilmiş PDF yüklendi: {merged_pdf_name}")
            except Exception as e:
                print(f"Birleştirme işleminde hata: {str(e)}")
                print("Sadece değerlendirme PDF'i yüklenecek")
                result = upload_pdf_to_drive(evaluation_pdf_path, merged_pdf_name, folder_id=EVALUATED_PDF_FOLDER)
        else:
            result = upload_pdf_to_drive(evaluation_pdf_path, merged_pdf_name, folder_id=EVALUATED_PDF_FOLDER)
            
        pdf_id = result['file_id']
        web_view_link = result['web_view_link']
        
        evaluation = RefereeEvaluation.objects.create(
            blurred_pdf=blurred_pdf,
            decision=decision,
            comments=comments,
            evaluation_pdf_id=pdf_id,
            evaluation_date=timezone.now(),
            is_evaluation_sent = False
        )
        
        decision_text = "Başarılı" if decision == "success" else "Reddedildi"
        article.article_status = f"Makale Değerlendirmesi Tamamlandı. Editör yönlendirmesi bekleniyor."
        
        article.save()
        
        from logs.models import log
        
        log_message = f"{article.tracking_number} takip numaralı {article.article_name} adlı makale {blurred_pdf.referee_name} hakem tarafından değerlendirildi. Makale başarı durumu: {decision_text}"
        
        log.objects.create(
            log_type="Hakem",
            log_message=log_message
        )
        try:
            if os.path.exists(evaluation_pdf_path):
                os.remove(evaluation_pdf_path)
            if merged_pdf_path and os.path.exists(merged_pdf_path):
                os.remove(merged_pdf_path)
        except Exception as clean_error:
            print(f"Geçici dosyaları temizlerken hata: {str(clean_error)}")
        
        return {
            'success': True,
            'message': f'Değerlendirmeniz başarıyla kaydedildi. Link: {web_view_link}',
            'pdf_id': pdf_id,
            'web_view_link': web_view_link
        }
        
    except Exception as e:
        print(f"Değerlendirme işleminde genel hata: {str(e)}")
        return {
            'success': False,
            'message': f'Değerlendirme işlemi sırasında hata oluştu: {str(e)}'
        }
    
def create_evaluation_pdf(blurred_pdf, decision, comments):
    """
    Hakem değerlendirmesi için PDF oluşturur
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.close()
    temp_path = temp_file.name
    

    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    
    try:

        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
            font_name = 'DejaVuSans'
            font_bold = 'DejaVuSans-Bold'
        except:
            try:
                pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/Arialbd.ttf'))
                font_name = 'Arial'
                font_bold = 'Arial-Bold'
            except:
                print("Türkçe uyumlu fontlar yüklenemedi, varsayılan font kullanılıyor")
    except:
        print("TTF font desteği bulunamadı, varsayılan font kullanılıyor")
    

    doc = SimpleDocTemplate(temp_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=16,
        alignment=1,  # Ortalanmış
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        spaceAfter=10
    )

    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=11,
        spaceAfter=10
    )
    italic_style = ParagraphStyle(
        'Italic',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=10,
        italic=True
    )
    title = Paragraph("MAKALE DEĞERLENDİRME RAPORU", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))

    article_data = [
        ["Makale Adı:", blurred_pdf.original_article.article_name],
        ["Takip Numarası:", blurred_pdf.original_article.tracking_number],
        ["Değerlendirme Tarihi:", timezone.now().strftime("%d.%m.%Y")],
    ]
    
    article_table = Table(article_data, colWidths=[120, 360])
    article_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, 0), (0, -1), font_bold),
    ]))
    
    elements.append(article_table)
    elements.append(Spacer(1, 20))

    decision_text = "Başarılı" if decision == "success" else "Reddedildi"
    decision_color = colors.green if decision == "success" else colors.red

    decision_para = Paragraph(f"<b>Değerlendirme Kararı:</b> <font color={decision_color}>{decision_text}</font>", bold_style)
    elements.append(decision_para)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>Değerlendirme:</b>", bold_style))

    comment_lines = comments.split("\n")
    for line in comment_lines:
        if line.strip():
            p = Paragraph(line, normal_style)
            elements.append(p)
    
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"<i>Bu değerlendirme raporu {timezone.now().strftime('%d.%m.%Y')} tarihinde oluşturulmuştur.</i>", italic_style))
    
    doc.build(elements)
    
    return temp_path

def merge_pdfs(original_pdf_stream, evaluation_pdf_path):
    """
    Orijinal PDF ile değerlendirme PDF'ini birleştirir
    """
    merged_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    merged_file.close()
    merged_path = merged_file.name
    
    original_pdf = PdfReader(original_pdf_stream)
    evaluation_pdf = PdfReader(evaluation_pdf_path)

    output_pdf = PdfWriter()
   
    for page in original_pdf.pages:
        output_pdf.add_page(page)
    
    for page in evaluation_pdf.pages:
        output_pdf.add_page(page)
    
    with open(merged_path, 'wb') as f:
        output_pdf.write(f)
    
    return merged_path

def get_drive_service():
    """
    Google Drive API servisini oluşturur
    """
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Drive servis hatası: {str(e)}")
        raise Exception(f"Google Drive API erişim hatası: {str(e)}")

def download_pdf_from_drive(file_id):
    """
    Google Drive'dan PDF dosyasını indirir
    """
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    
    pdf_content = BytesIO()
    downloader = MediaIoBaseDownload(pdf_content, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    pdf_content.seek(0)
    return pdf_content

def upload_pdf_to_drive(file_path, filename, folder_id=None):
    """
    Google Drive'a yeni bir PDF dosyası yükler
    """
    service = get_drive_service()
    
    file_metadata = {
        'name': filename,
        'mimeType': 'application/pdf'
    }

    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Yüklenecek dosya bulunamadı: {file_path}")

        file_size = os.path.getsize(file_path)
        print(f"Yüklenen dosya boyutu: {file_size} byte")
        
        if file_size == 0:
            raise ValueError(f"Dosya boyutu sıfır: {file_path}")
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/pdf'

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        web_view_link = file.get('webViewLink')
        
        permission = {
            'type': 'anyone',
            'role': 'writer'
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        
        print(f"PDF başarıyla yüklendi. Drive ID: {file_id}, Link: {web_view_link}")
        
        return {
            'file_id': file_id,
            'web_view_link': web_view_link
        }
        
    except Exception as e:
        error_message = f"PDF yükleme hatası: {str(e)}"
        print(error_message)
        raise Exception(error_message)

def view_pdf(request, file_id):
    """
    Google Drive'dan PDF dosyasını indirip kullanıcıya sunar.
    Sadece değerlendirme PDF'ini gösterir, orjinal makale ile birleştirmeden.
    """
    try:
        evaluation = RefereeEvaluation.objects.filter(evaluation_pdf_id=file_id).first()
        
        pdf_content = download_pdf_from_drive(file_id)
        
        response = HttpResponse(pdf_content.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="evaluation.pdf"'
        return response
        
    except Exception as e:
        return HttpResponse(f"PDF yüklenirken hata oluştu: {str(e)}", status=500)
    
@csrf_exempt
def preview_evaluation(request, pdf_id):
    """
    Değerlendirme önizlemesi için - sadece değerlendirme PDF'ini gösterir
    """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            blurred_pdf = get_object_or_404(BlurredPDF, id=pdf_id)
            data = json.loads(request.body)
            decision = data.get('decision')
            comments = data.get('comments')
            
            if not decision or not comments:
                return HttpResponse('Eksik değerlendirme bilgileri', status=400)
            
            evaluation_pdf_path = create_evaluation_pdf(blurred_pdf, decision, comments)
            
            with open(evaluation_pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="evaluation_preview.pdf"'

            try:
                os.remove(evaluation_pdf_path)
            except:
                pass
                
            return response
            
        except Exception as e:
            return HttpResponse(str(e), status=500)
            
    return HttpResponse("Geçersiz istek", status=400)