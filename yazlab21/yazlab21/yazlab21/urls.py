from django.contrib import admin
from django.urls import path, include
from administration.views import index as main_page
from author.views import *
from django.conf.urls.static import static
from author.views import message_to_editor  # Mesaj gönderme view'ı


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", main_page, name="main-page"),
    path('author/', include("author.urls")),
    path('editor/', include("editor.urls")),
    path("upload-file/", upload_file, name="upload_file"),
    path("show-article/", show_article, name="show_article"),
    path("send-verification-code/", send_verification_code, name="send-verification-code"),
    path("message-to-editor/", message_to_editor, name="message_to_editor"),  # Mesaj gönderme URL
    path('referee/',include("referee.urls"))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)