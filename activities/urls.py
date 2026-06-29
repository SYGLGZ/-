# E:\python\activities\urls.py

from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'activities'

urlpatterns = [
    # 首页和活动列表
    path('', views.home, name='home'),
    path('list/', views.activity_list, name='activity_list'),
    
    # 活动详情和报名
    path('activity/<int:pk>/', views.activity_detail, name='activity_detail'),
    path('register/<int:pk>/', views.register_for_activity, name='register'),
    path('cancel/<int:pk>/', views.cancel_registration, name='cancel'),
    
    # 活动管理（创建/编辑）
    path('activity/create/', views.activity_create, name='activity_create'),
    path('activity/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activity/<int:pk>/delete/', views.activity_delete, name='activity_delete'),

    # 认证相关路径
    path('signup/', views.signup, name='signup'),
    path('login/', views.custom_login, name='login'),
    path('logout/', LogoutView.as_view(template_name='registration/logout.html'), name='logout'),

    # 用户资料
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # 签到功能
    path('activity/<int:pk>/generate-checkin-code/', views.generate_checkin_code, name='generate_checkin_code'),
    path('activity/<int:pk>/refresh-checkin-code/', views.refresh_checkin_code, name='refresh_checkin_code'),
    path('activity/<int:pk>/checkin/', views.checkin, name='checkin'),
    path('activity/<int:pk>/checkin-list/', views.checkin_list, name='checkin_list'),
    path('activity/<int:pk>/cancel-checkin/<int:registration_pk>/', views.cancel_checkin, name='cancel_checkin'),
    path('activity/<int:pk>/export-checkin/', views.export_checkin_list, name='export_checkin'),
]
