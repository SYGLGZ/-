from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
import secrets
import string

def generate_checkin_code():
    """生成6位随机签到码（数字+大写字母）"""
    alphabet = string.digits + string.ascii_uppercase
    return ''.join(secrets.choice(alphabet) for _ in range(6))

# --- 1. 用户详细资料模型 (Profile) ---
class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', '学生'),
        ('teacher', '活动老师'),
        ('developer', '开发者'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # 用户注册时由信号先创建空 Profile；NULL 可避免多个未完善资料的账号触发唯一键冲突。
    student_id = models.CharField("学号/工号", max_length=20, unique=True, blank=True, null=True)
    name = models.CharField("姓名", max_length=50)
    college = models.CharField("学院", max_length=100)
    class_name = models.CharField("班级/部门", max_length=50, blank=True, null=True)
    phone = models.CharField("手机号", max_length=15)
    role = models.CharField("用户角色", max_length=20, choices=ROLE_CHOICES, default='student')
    is_completed = models.BooleanField("资料是否完善", default=False)

    def __str__(self):
        return f"{self.name} ({self.student_id}) - {self.get_role_display()}"
    
    def is_developer(self):
        return self.role == 'developer' or self.user.is_superuser
    
    def is_teacher(self):
        return self.role == 'teacher' or self.is_developer()
    
    def is_student(self):
        return self.role == 'student'

# 注意：信号代码已移至 signals.py，此处不再需要

# --- 2. 活动模型 (Activity) ---
class Activity(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('ongoing', '进行中'),
        ('ended', '已结束'),
    ]
    
    title = models.CharField("活动标题", max_length=200)
    description = models.TextField("活动描述")
    date = models.DateTimeField("活动时间")
    location = models.CharField("地点", max_length=200)
    image = models.ImageField("活动图片", upload_to='activities/', blank=True, null=True)
    capacity = models.PositiveIntegerField("人数限制", default=100)
    status = models.CharField("活动状态", max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_activities', verbose_name="创建者")
    
    # 签到功能字段
    checkin_code = models.CharField("签到码", max_length=6, blank=True, null=True, help_text="6位签到码")
    checkin_start_time = models.DateTimeField("签到开始时间", blank=True, null=True)
    checkin_end_time = models.DateTimeField("签到结束时间", blank=True, null=True)

    def __str__(self):
        return self.title
    
    def get_registered_count(self):
        return self.registrations.count()
    
    def is_full(self):
        return self.get_registered_count() >= self.capacity
    
    def can_edit(self, user):
        """判断用户是否有权限编辑此活动"""
        if user.is_superuser:
            return True
        try:
            profile = user.profile
            if profile.is_developer():
                return True
            if profile.is_teacher() and self.creator == user:
                return True
        except Profile.DoesNotExist:
            pass
        return False
    
    def generate_checkin_code(self):
        """生成新的签到码"""
        self.checkin_code = generate_checkin_code()
        self.save(update_fields=['checkin_code'])
        return self.checkin_code
    
    def refresh_checkin_code(self):
        """刷新签到码（重新生成）"""
        old_code = self.checkin_code
        self.checkin_code = generate_checkin_code()
        self.save(update_fields=['checkin_code'])
        return self.checkin_code, old_code
    
    def is_checkin_available(self):
        """判断当前是否可以签到"""
        if self.checkin_code is None or self.checkin_code == '':
            return False
        now = timezone.now()
        start_time = self.checkin_start_time or self.date - timezone.timedelta(minutes=30)
        end_time = self.checkin_end_time or self.date + timezone.timedelta(hours=2)
        return start_time <= now <= end_time
    
    def get_checkin_count(self):
        """获取已签到人数"""
        return self.registrations.filter(is_checked_in=True).count()
    
    def get_checkin_rate(self):
        """获取签到率"""
        total = self.get_registered_count()
        if total == 0:
            return 0
        return (self.get_checkin_count() / total) * 100

# --- 3. 报名记录模型 (Registration) ---
class Registration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='registrations', verbose_name="活动")
    created_at = models.DateTimeField("报名时间", auto_now_add=True)
    
    # 签到状态
    is_checked_in = models.BooleanField("是否已签到", default=False, db_index=True)
    checked_in_at = models.DateTimeField("签到时间", blank=True, null=True)
    
    # 签到日志
    checkin_log = models.JSONField("签到日志", default=list, blank=True, help_text="记录签到操作的详细信息")

    class Meta:
        unique_together = ('user', 'activity')
        verbose_name = "报名记录"
        verbose_name_plural = "报名记录"

    def __str__(self):
        status = "已签到" if self.is_checked_in else "未签到"
        return f"{self.user.username} 报名了 {self.activity.title} ({status})"
    
    def checkin(self, ip_address=None, user_agent=None):
        """完成签到"""
        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "action": "checkin",
            "user_id": self.user.id,
            "user_name": self.user.username,
            "activity_id": self.activity.id,
            "activity_title": self.activity.title,
            "ip_address": ip_address or "unknown",
            "user_agent": user_agent or "unknown",
        }
        self.is_checked_in = True
        self.checked_in_at = timezone.now()
        
        # 记录日志
        existing_log = list(self.checkin_log or [])
        existing_log.append(log_entry)
        self.checkin_log = existing_log
        
        self.save()
    
    def cancel_checkin(self, ip_address=None, user_agent=None):
        """取消签到"""
        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "action": "cancel_checkin",
            "user_id": self.user.id,
            "user_name": self.user.username,
            "activity_id": self.activity.id,
            "activity_title": self.activity.title,
            "previous_checkin_time": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "ip_address": ip_address or "unknown",
            "user_agent": user_agent or "unknown",
        }
        self.is_checked_in = False
        self.checked_in_at = None
        
        # 记录日志
        existing_log = list(self.checkin_log or [])
        existing_log.append(log_entry)
        self.checkin_log = existing_log
        
        self.save()
