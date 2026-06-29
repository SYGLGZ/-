from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from captcha.fields import CaptchaField
from .models import Profile, Activity

# 1. 带验证码的注册表单
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    captcha = CaptchaField(label='验证码') # 添加验证码字段

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'captcha')

# 2. 带验证码的登录表单
class LoginForm(AuthenticationForm):
    captcha = CaptchaField(label='验证码')

# 3. 完善资料表单
class ProfileForm(forms.ModelForm):
    student_id = forms.CharField(label='学号/工号', max_length=20, required=True)

    class Meta:
        model = Profile
        fields = ['name', 'student_id', 'college', 'class_name', 'phone']
        labels = {'class_name': '班级/部门'}

# 4. 活动表单
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'date', 'location', 'image', 'capacity', 'status']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
