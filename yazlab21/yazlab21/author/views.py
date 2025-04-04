from django.shortcuts import render
import mimetypes
import os
import random
import string
import json
import uuid
import time
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils import timezone
from googleapiclient.discovery import build
from django.http import HttpResponse
from google.oauth2 import service_account
from .models import UncensoredArticles, Messages
from logs.models import log
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Google Drive ayarları
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'
OrjinalPDF = "1B_MvMlKPYG-LKcbomQCjWYvoWyd1cJ73"


def upload_article(request):
    # E-posta doğrulamasını kaldırdık - doğrudan şablonu oluşturuyoruz
    return render(request, "author/upload_article.html")


def authenticate():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return creds


def generate_tracking_number():
    return str(uuid.uuid4().hex[:8]).upper()


def generate_access_code():
    """6 haneli rastgele alfanumerik kod oluşturur."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))


@csrf_exempt
def upload_file(request):
    if request.method == "POST":
        try:
            file = request.FILES.get("file")
            email = request.POST.get("email")
            
            # E-posta bilgisi request.POST'ta yoksa, request.body'den JSON olarak almayı dene
            if not email and request.content_type and 'application/json' in request.content_type:
                try:
                    body_data = json.loads(request.body)
                    email = body_data.get('email')
                except:
                    pass
            
            if not file:
                return JsonResponse({"message": "Dosya seçilmedi!"}, status=400)
                
            if not email:
                return JsonResponse({"message": "E-posta adresi gereklidir!"}, status=400)

            creds = authenticate()
            service = build('drive', 'v3', credentials=creds)

            temp_path = os.path.join(settings.MEDIA_ROOT, file.name)

            # Dosyayı geçici olarak kaydet
            with open(temp_path, "wb+") as dest:
                for chunk in file.chunks():
                    dest.write(chunk)

            time.sleep(1)  # Windows için güvenli bekleme

            mime_type, _ = mimetypes.guess_type(temp_path)
            media = MediaFileUpload(temp_path, mimetype=mime_type, resumable=False)
            file_drive = service.files().create(
                body={"name": file.name, "parents": [OrjinalPDF]},
                media_body=media,
                fields="id, webViewLink"
            ).execute()

            media = None

            time.sleep(1)  # Dosya serbest bırakıldığından emin ol

            # Geçici dosyayı sil
            if os.path.exists(temp_path):
                os.remove(temp_path)

            permission = {"type": "anyone", "role": "writer"}
            service.permissions().create(
                fileId=file_drive.get("id"),
                body=permission
            ).execute()

            tracking_number = generate_tracking_number()
            access_code = generate_access_code()
            
            article = UncensoredArticles.objects.create(
                article_owner=email,
                article_name=file.name,
                article_drive_id=file_drive.get("id"),
                tracking_number=tracking_number
            )
            article.save()


            log_message = f"{article.article_owner} tarafından {article.article_name} adında bir makale yüklenmiştir. Takip no : {tracking_number},Drive ID : {article.article_drive_id}"
        
            log.objects.create(
            log_type="Yazar",
            log_message=log_message
            )
        
            
            # Erişim kodunu e-posta ile gönder
            subject = "Makaleniz için Erişim Kodu"
            message = f"""
            Sayın Yazar,
            
            Makaleniz sistemimize başarıyla yüklenmiştir.
            
            Makale Başlığı: {file.name}
            Takip Kodu: {tracking_number}
            
            Makalenizin durumunu kontrol etmek için takip kodunu ve erişim kodunu kullanabilirsiniz.
            
            Saygılarımızla,
            E - Makale Servisi
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            return JsonResponse({
                "message": "Dosya başarıyla yüklendi ve veritabanına kaydedildi!",
                "file_url": file_drive.get("webViewLink"),
                "file_id": file_drive.get("id"),
                "tracking_number": tracking_number,
                "email": email
            })

        except Exception as e:
            return JsonResponse({"message": f"Hata: {str(e)}"}, status=500)

    return JsonResponse({"message": "Geçersiz istek!"}, status=400)


@csrf_exempt
def show_article(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "temp"))
        filename = fs.save(file.name, file)
        file_url = fs.url(f"temp/{filename}")
        return JsonResponse({"file_url": file_url})

    return JsonResponse({"error": "Dosya yüklenemedi!"}, status=400)


@csrf_exempt
def send_verification_code(request):
    """
    E-posta doğrulama kodu gönderme işlemi.
    Bu view, hem /send_verification_code/ hem de /author/send_verification_code/ yollarından erişilebilir.
    """
    if request.method == "POST":
        try:
            # Content-Type kontrolü
            if request.content_type and 'application/json' in request.content_type:
                # JSON formatında gelen veri
                try:
                    data = json.loads(request.body)
                    email = data.get("email")
                except json.JSONDecodeError:
                    return JsonResponse({"success": False, "message": "Geçersiz JSON formatı!"}, status=400)
            else:
                # Form formatında gelen veri
                email = request.POST.get("email")

            if not email:
                return JsonResponse({"success": False, "message": "E-posta adresi gereklidir!"}, status=400)

            verification_code = ''.join(random.choices('0123456789', k=4))

            subject = "E-posta Doğrulama Kodu"
            message = (
                f"Merhaba,\n\n"
                f"E-posta doğrulama kodunuz: {verification_code}\n"
                f"Bu kodu kimseyle paylaşmayın.\n\n"
                f"Saygılarımızla,\nE - Makale Sistemi"
            )

            # Gerçek bir mail gönderiyoruz - geliştirme aşamasında bu kısmı yorumlayabilirsiniz
            send_mail(
                 subject=subject,
                 message=message,
                 from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
             )

            # Geliştirme aşamasında doğrulama kodunu doğrudan döndür
            return JsonResponse({"success": True, "message": "Doğrulama kodu gönderildi!", "code": verification_code})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Hata: {str(e)}"}, status=500)

    return JsonResponse({"success": False, "message": "Geçersiz istek yöntemi!"}, status=405)


@csrf_exempt
def check_article_status(request):
    if request.method == "POST":
        try:
            # Content-Type kontrolü
            if request.content_type and 'application/json' in request.content_type:
                # JSON formatında gelen veri
                try:
                    data = json.loads(request.body)
                    tracking_number = data.get("tracking_number")
                    email = data.get("email")
                except json.JSONDecodeError:
                    return JsonResponse({"success": False, "message": "Geçersiz JSON formatı!"}, status=400)
            else:
                # Form formatında gelen veri
                tracking_number = request.POST.get("tracking_number")
                email = request.POST.get("email")
            
            if not tracking_number:
                return JsonResponse({"success": False, "message": "Takip numarası gereklidir!"}, status=400)
                
            if not email:
                return JsonResponse({"success": False, "message": "E-posta adresi gereklidir!"}, status=400)
                
            try:
                article = UncensoredArticles.objects.get(tracking_number=tracking_number, article_owner=email)
                
                # Hakem değerlendirmesi var mı kontrol et
                is_evaluation_sent = False
                try:
                    # BlurredPDF üzerinden RefereeEvaluation'a erişmeye çalış
                    blurred_pdf = article.blurred_pdf
                    evaluations = blurred_pdf.evaluations.filter(is_evaluation_sent=True)
                    is_evaluation_sent = evaluations.exists()
                except:
                    # Hakem değerlendirmesi bulunamadı veya BlurredPDF henüz oluşturulmamış
                    pass
                
                return JsonResponse({
                    "success": True,
                    "status": article.article_status,
                    "article_name": article.article_name,
                    "submitted_date": article.uploaded_at.strftime("%d/%m/%Y %H:%M"),
                    "is_evaluation_sent": is_evaluation_sent
                })
            except UncensoredArticles.DoesNotExist:
                return JsonResponse({"success": False, "message": "Makale bulunamadı veya e-posta eşleşmiyor!"}, status=404)
                
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Hata: {str(e)}"}, status=500)
            
    return JsonResponse({"success": False, "message": "Geçersiz istek!"}, status=400)


def download_evaluation(request, tracking_number):
    """
    Hakem değerlendirme raporunu indirme fonksiyonu
    """
    try:
        # Google Drive API ile bağlantı kur
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        
        # Önce tracking_number ile makaleyi bulmaya çalış
        try:
            article = UncensoredArticles.objects.get(tracking_number=tracking_number)
            article_name = article.article_name
        except UncensoredArticles.DoesNotExist:
            # Makale bulunamadıysa, bu bir hata olabilir ya da sadece ismi belirlemek için kullanılıyordu
            article_name = None
        
        # Belirtilen klasördeki tüm dosyaları listele
        folder_id = "1OK8NPGrUHdc9ksUpoyKCiOQqVhKKrNxY"  # Değerlendirme dosyalarının bulunduğu klasör
        
        # Eğer makale adı biliniyorsa, ona göre filtreleme yap
        query = f"'{folder_id}' in parents"
        if article_name:
            # Makale adına göre filtreleme (dosya adı makale adını içeriyorsa)
            query += f" and name contains '{article_name}'"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return JsonResponse({"success": False, "message": "Bu makale için değerlendirme dosyası bulunamadı!"}, status=404)
        
        # İlk dosyayı al (filtreleme varsa muhtemelen tek dosya olacaktır)
        file = files[0]
        file_id = file['id']
        file_name = file['name']
        
        # Dosyayı indir
        request = service.files().get_media(fileId=file_id)
        from io import BytesIO
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        # Dosyayı kullanıcıya gönder
        fh.seek(0)
        response = HttpResponse(fh.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Hata: {str(e)}"}, status=500)


def message_panel(request):
    """
    Mesaj paneli sayfasını render eden view.
    """
    return render(request, "message_panel.html")


@require_POST
@csrf_exempt
def message_to_editor(request):
    """
    Yazardan editöre mesaj gönderme işlemi.
    """
    try:
        # Content-Type kontrolü
        if request.content_type and 'application/json' in request.content_type:
            # JSON formatında gelen veri
            try:
                data = json.loads(request.body)
                email = data.get('email')
                title = data.get('title')
                text = data.get('text')
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "message": "Geçersiz JSON formatı!"}, status=400)
        else:
            # Form formatında gelen veri
            email = request.POST.get('email')
            title = request.POST.get('title')
            text = request.POST.get('text')

        if not all([email, title, text]):
            return JsonResponse({'success': False, 'error': 'Tüm alanlar doldurulmalıdır.'})

        # Yeni bir mesaj oluştur ve kaydet
        message = Messages(
            message_sender_email=email,
            message_title=title,
            message_text=text,
            message_time=timezone.now(),
            is_from_author=True,  # Yazardan gelen mesaj
            is_read=False  # Başlangıçta okunmamış
        )
        message.save()

        return JsonResponse({'success': True, 'message': 'Mesajınız başarıyla kaydedildi.'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def message_panel(request):
    """
    Mesaj paneli sayfasını render eden view.
    """
    return render(request, "author/message_panel.html")


@require_POST
@csrf_exempt
def get_user_messages(request):
    """
    Kullanıcının mesajlarını getiren view.
    """
    try:
        # Content-Type kontrolü
        if request.content_type and 'application/json' in request.content_type:
            # JSON formatında gelen veri
            try:
                data = json.loads(request.body)
                email = data.get('email')
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "message": "Geçersiz JSON formatı!"}, status=400)
        else:
            # Form formatında gelen veri
            email = request.POST.get('email')

        if not email:
            return JsonResponse({'success': False, 'message': 'E-posta adresi gereklidir!'})

        # İlgili kullanıcının aldığı mesajları getir (is_from_author=False olan mesajlar)
        # Bunlar editörden yazara giden mesajlardır
        messages = Messages.objects.filter(
            message_sender_email=email,
            is_from_author=False
        ).order_by('-message_time')

        # Mesajları JSON formatına dönüştür
        messages_list = []
        for msg in messages:
            messages_list.append({
                'id': msg.id,
                'title': msg.message_title,
                'text': msg.message_text,
                'time': msg.message_time.strftime("%d.%m.%Y %H:%M")
            })

        return JsonResponse({
            'success': True,
            'messages': messages_list
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def article_status(request):
    """
    Makale durum sorgulama sayfasını render eden view.
    """
    return render(request, "author/article_status.html")


