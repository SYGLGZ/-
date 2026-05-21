from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from activities import views as activities_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 自定义登录视图
    path('accounts/login/', activities_views.custom_login, name='login'),
    path('accounts/', include('django.contrib.auth.urls')),

    # 核心应用路由（放在首页前面）
    path('activities/', include(('activities.urls', 'activities'), namespace='activities')),
    path('captcha/', include('captcha.urls')),
    
    # 首页路由放在最后
    path('', activities_views.home, name='home'), 
]

# 开发环境下的媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)