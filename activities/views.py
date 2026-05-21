from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.utils import timezone
from .models import Activity, Registration, Profile
from .forms import SignUpForm, LoginForm, ProfileForm, ActivityForm


def profile_complete_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                if not profile.is_completed:
                    edit_url = reverse('activities:edit_profile')
                    if request.path != edit_url: 
                        messages.warning(request, "请先完善个人资料才能使用此功能。")
                        return redirect('activities:edit_profile')
            except Profile.DoesNotExist:
                return redirect('activities:edit_profile')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def is_developer(user):
    """检查是否为开发者"""
    if user.is_superuser:
        return True
    try:
        return user.profile.is_developer()
    except Profile.DoesNotExist:
        return False


def is_teacher(user):
    """检查是否为活动老师或开发者"""
    if user.is_superuser:
        return True
    try:
        return user.profile.is_teacher()
    except Profile.DoesNotExist:
        return False


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "注册成功！请完善您的个人资料。")
            return redirect('activities:edit_profile')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def custom_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"欢迎回来，{username}！")
                
                if not user.profile.is_completed:
                    return redirect('activities:edit_profile')
                return redirect('activities:activity_list')
        else:
            messages.error(request, "用户名或密码错误。")
    
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.is_completed = True
            updated_profile.save()
            messages.success(request, "资料更新成功！")
            return redirect('activities:activity_list')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'registration/edit_profile.html', {'form': form})


def home(request):
    activities = Activity.objects.filter(status='published').order_by('-date')[:6]
    return render(request, 'activity_list.html', {'activities': activities})


@login_required
@profile_complete_required
def activity_list(request):
    activities = Activity.objects.filter(status='published').order_by('-date')
    return render(request, 'activity_list.html', {'activities': activities})


@login_required
@profile_complete_required
def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    registration = Registration.objects.filter(user=request.user, activity=activity).first()
    is_registered = registration is not None
    registered_count = activity.get_registered_count()
    is_full = activity.is_full()
    is_past = activity.date < timezone.now()
    
    # 计算用户是否可以编辑活动
    can_edit = False
    if request.user.is_authenticated:
        can_edit = activity.can_edit(request.user)
    
    context = {
        'activity': activity,
        'registration': registration,
        'is_registered': is_registered,
        'registered_count': registered_count,
        'is_full': is_full,
        'is_past': is_past,
        'can_edit': can_edit,
    }
    return render(request, 'activity_detail.html', context)


@login_required
@profile_complete_required
def register_for_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    
    if activity.date < timezone.now():
        messages.error(request, "该活动已结束，无法报名。")
        return redirect('activities:activity_detail', pk=pk)
    
    if activity.is_full():
        messages.error(request, "该活动名额已满。")
        return redirect('activities:activity_detail', pk=pk)
    
    registration, created = Registration.objects.get_or_create(user=request.user, activity=activity)
    if created:
        messages.success(request, "报名成功！")
    else:
        messages.warning(request, "您已报名。")
    return redirect('activities:activity_detail', pk=pk)


@login_required
@profile_complete_required
def cancel_registration(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    deleted, _ = Registration.objects.filter(user=request.user, activity=activity).delete()
    if deleted > 0:
        messages.success(request, "已取消报名。")
    return redirect('activities:activity_detail', pk=pk)


@login_required
@user_passes_test(is_teacher)
def activity_create(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.creator = request.user
            activity.save()
            messages.success(request, "活动创建成功！")
            return redirect('activities:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm()
    return render(request, 'activity_form.html', {'form': form, 'title': '创建活动'})


@login_required
@user_passes_test(is_teacher)
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    
    # 检查权限：开发者可以编辑所有活动，老师只能编辑自己创建的活动
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限编辑此活动。")
        return redirect('activities:activity_detail', pk=pk)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, "活动更新成功！")
            return redirect('activities:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm(instance=activity)
    return render(request, 'activity_form.html', {'form': form, 'title': '编辑活动'})


@login_required
@user_passes_test(is_developer)
def activity_delete(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    
    # 只有开发者可以删除活动
    if not request.user.profile.is_developer():
        messages.error(request, "您没有权限删除此活动。")
        return redirect('activities:activity_detail', pk=pk)
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, "活动已删除。")
        return redirect('activities:activity_list')
    return render(request, 'activity_confirm_delete.html', {'activity': activity})


# ==================== 签到功能视图 ====================

@login_required
@profile_complete_required
@user_passes_test(is_teacher)
def generate_checkin_code(request, pk):
    """老师生成签到码"""
    activity = get_object_or_404(Activity, pk=pk)
    
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限操作此活动。")
        return redirect('activities:activity_detail', pk=pk)
    
    # 检查活动状态：只有在已发布或进行中的活动才能生成签到码
    if activity.status not in ['published', 'ongoing']:
        messages.error(request, "只有已发布的活动才能生成签到码。")
        return redirect('activities:activity_detail', pk=pk)
    
    code = activity.generate_checkin_code()
    messages.success(request, f"签到码已生成：{code}")
    return redirect('activities:activity_detail', pk=pk)


@login_required
@profile_complete_required
@user_passes_test(is_teacher)
def refresh_checkin_code(request, pk):
    """老师刷新签到码"""
    activity = get_object_or_404(Activity, pk=pk)
    
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限操作此活动。")
        return redirect('activities:activity_detail', pk=pk)
    
    # 检查活动状态
    if activity.status not in ['published', 'ongoing']:
        messages.error(request, "只有已发布的活动才能刷新签到码。")
        return redirect('activities:activity_detail', pk=pk)
    
    new_code, old_code = activity.refresh_checkin_code()
    messages.success(request, f"签到码已刷新！旧码：{old_code} → 新码：{new_code}")
    return redirect('activities:activity_detail', pk=pk)


@login_required
@profile_complete_required
def checkin(request, pk):
    """学生签到"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # 检查是否已报名
    registration = Registration.objects.filter(user=request.user, activity=activity).first()
    if not registration:
        messages.error(request, "您尚未报名此活动，无法签到。")
        return redirect('activities:activity_detail', pk=pk)
    
    # 检查是否已签到
    if registration.is_checked_in:
        messages.warning(request, "您已完成签到。")
        return redirect('activities:activity_detail', pk=pk)
    
    # 检查签到码是否存在
    if not activity.checkin_code:
        messages.error(request, "该活动暂未生成签到码，请稍后再试。")
        return redirect('activities:activity_detail', pk=pk)
    
    # 获取客户端信息
    ip_address = request.META.get('REMOTE_ADDR', '')
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
    
    if request.method == 'POST':
        input_code = request.POST.get('checkin_code', '').strip().upper()
        
        # 优化验证顺序：先检查最可能失败的
        if not input_code:
            messages.error(request, "请输入签到码。")
        elif not activity.is_checkin_available():
            # 签到时间检查放前面，因为这是最容易明确失败原因的
            messages.error(request, "签到时间未到或已结束。")
        elif input_code != activity.checkin_code:
            messages.error(request, "签到码错误，请重试。")
        else:
            registration.checkin(ip_address=ip_address, user_agent=user_agent)
            messages.success(request, "签到成功！")
            return redirect('activities:activity_detail', pk=pk)
    
    return render(request, 'checkin.html', {'activity': activity})


@login_required
@profile_complete_required
@user_passes_test(is_teacher)
def cancel_checkin(request, pk, registration_pk):
    """老师取消学生签到"""
    activity = get_object_or_404(Activity, pk=pk)
    registration = get_object_or_404(Registration, pk=registration_pk, activity=activity)
    
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限操作此签到记录。")
        return redirect('activities:checkin_list', pk=pk)
    
    ip_address = request.META.get('REMOTE_ADDR', '')
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
    
    registration.cancel_checkin(ip_address=ip_address, user_agent=user_agent)
    messages.success(request, f"已取消 {registration.user.profile.name} 的签到状态。")
    return redirect('activities:checkin_list', pk=pk)


@login_required
@profile_complete_required
@user_passes_test(is_teacher)
def export_checkin_list(request, pk):
    """导出签到名单为CSV"""
    import csv
    from django.http import HttpResponse
    
    activity = get_object_or_404(Activity, pk=pk)
    
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限导出此活动的签到记录。")
        return redirect('activities:activity_detail', pk=pk)
    
    registrations = activity.registrations.select_related('user__profile').order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="签到名单_{activity.title}_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response)
    writer.writerow(['姓名', '学号/工号', '学院', '班级/部门', '报名时间', '是否签到', '签到时间', '手机号'])
    
    for reg in registrations:
        profile = reg.user.profile
        writer.writerow([
            profile.name,
            profile.student_id,
            profile.college,
            profile.class_name or '',
            reg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '是' if reg.is_checked_in else '否',
            reg.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if reg.checked_in_at else '',
            profile.phone,
        ])
    
    return response


@login_required
@profile_complete_required
@user_passes_test(is_teacher)
def checkin_list(request, pk):
    """老师查看签到列表"""
    activity = get_object_or_404(Activity, pk=pk)
    
    if not activity.can_edit(request.user):
        messages.error(request, "您没有权限查看此活动的签到记录。")
        return redirect('activities:activity_detail', pk=pk)
    
    registrations = activity.registrations.select_related('user__profile').order_by('-created_at')
    checkin_count = registrations.filter(is_checked_in=True).count()
    total_count = registrations.count()
    
    context = {
        'activity': activity,
        'registrations': registrations,
        'checkin_count': checkin_count,
        'total_count': total_count,
        'checkin_rate': activity.get_checkin_rate(),
    }
    return render(request, 'checkin_list.html', context)