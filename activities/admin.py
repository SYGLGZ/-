from django.contrib import admin
from django.utils.html import format_html
from .models import Activity, Registration, Profile

# 自定义 Activity 的显示方式
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'capacity', 'status', 'created_at', 'image_preview')
    list_filter = ('status', 'date')
    search_fields = ('title', 'location')
    list_editable = ('status',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 60px; height: 60px; object-fit: cover;" />', obj.image.url)
        return "无图片"
    image_preview.short_description = "图片预览"

# 自定义 Registration 的显示方式
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'created_at')
    search_fields = ('user__username', 'activity__title')
    list_filter = ('created_at',)

# 自定义 Profile 的显示方式
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'student_id', 'college', 'class_name', 'phone', 'role', 'is_completed')
    search_fields = ('name', 'student_id', 'college')
    list_filter = ('college', 'role', 'is_completed')

admin.site.register(Activity, ActivityAdmin)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(Profile, ProfileAdmin)