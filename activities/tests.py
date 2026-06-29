import csv
import io
import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Activity, Profile, Registration


class ActivityTestMixin:
    def create_user(self, username, role='student'):
        user = User.objects.create_user(username=username, password='StrongPass123!')
        Profile.objects.filter(user=user).update(
            student_id=f'ID-{username}',
            name=username,
            college='计算机学院',
            phone='13800000000',
            role=role,
            is_completed=True,
        )
        user.refresh_from_db()
        return user

    def create_activity(self, creator, **overrides):
        data = {
            'title': '网络安全讲座',
            'description': '校园网络安全实践',
            'date': timezone.now() + timedelta(minutes=10),
            'location': '实验楼 A101',
            'capacity': 2,
            'status': 'published',
            'creator': creator,
        }
        data.update(overrides)
        return Activity.objects.create(**data)


class ActivityModelTests(ActivityTestMixin, TestCase):
    def setUp(self):
        self.teacher = self.create_user('teacher', role='teacher')

    def test_checkin_code_uses_six_uppercase_alphanumeric_characters(self):
        activity = self.create_activity(self.teacher)

        code = activity.generate_checkin_code()

        self.assertRegex(code, re.compile(r'^[A-Z0-9]{6}$'))

    def test_custom_checkin_window_is_respected(self):
        now = timezone.now()
        activity = self.create_activity(
            self.teacher,
            date=now,
            checkin_code='ABC123',
            checkin_start_time=now + timedelta(minutes=5),
            checkin_end_time=now + timedelta(minutes=30),
        )

        self.assertFalse(activity.is_checkin_available())

    def test_checkin_and_cancellation_append_structured_audit_log(self):
        student = self.create_user('student')
        activity = self.create_activity(self.teacher)
        registration = Registration.objects.create(user=student, activity=activity)

        registration.checkin(ip_address='127.0.0.1', user_agent='test-agent')
        registration.cancel_checkin(ip_address='127.0.0.1', user_agent='test-agent')
        registration.refresh_from_db()

        self.assertEqual([entry['action'] for entry in registration.checkin_log], ['checkin', 'cancel_checkin'])
        self.assertFalse(registration.is_checked_in)
        self.assertIsNone(registration.checked_in_at)


class RegistrationViewTests(ActivityTestMixin, TestCase):
    def setUp(self):
        self.teacher = self.create_user('teacher', role='teacher')
        self.student = self.create_user('student')
        self.activity = self.create_activity(self.teacher, capacity=1)
        self.client.force_login(self.student)

    def test_registration_requires_post(self):
        response = self.client.get(reverse('activities:register', args=[self.activity.pk]))

        self.assertEqual(response.status_code, 405)

    def test_student_can_register_only_once(self):
        url = reverse('activities:register', args=[self.activity.pk])

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(Registration.objects.filter(activity=self.activity, user=self.student).count(), 1)

    def test_registration_rejects_when_capacity_is_full(self):
        Registration.objects.create(user=self.student, activity=self.activity)
        second_student = self.create_user('student2')
        self.client.force_login(second_student)

        self.client.post(reverse('activities:register', args=[self.activity.pk]))

        self.assertFalse(Registration.objects.filter(activity=self.activity, user=second_student).exists())

    def test_teacher_cannot_register_as_student(self):
        self.client.force_login(self.teacher)

        self.client.post(reverse('activities:register', args=[self.activity.pk]))

        self.assertFalse(Registration.objects.filter(activity=self.activity, user=self.teacher).exists())

    def test_draft_activity_cannot_be_registered_by_direct_url(self):
        self.activity.status = 'draft'
        self.activity.save(update_fields=['status'])

        self.client.post(reverse('activities:register', args=[self.activity.pk]))

        self.assertFalse(Registration.objects.filter(activity=self.activity).exists())

    def test_cancel_registration_requires_post(self):
        Registration.objects.create(user=self.student, activity=self.activity)

        response = self.client.get(reverse('activities:cancel', args=[self.activity.pk]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Registration.objects.filter(activity=self.activity, user=self.student).exists())

    def test_checked_in_registration_cannot_be_deleted(self):
        registration = Registration.objects.create(
            user=self.student,
            activity=self.activity,
            is_checked_in=True,
            checked_in_at=timezone.now(),
        )

        self.client.post(reverse('activities:cancel', args=[self.activity.pk]))

        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())

    def test_student_cannot_view_draft_activity_by_direct_url(self):
        self.activity.status = 'draft'
        self.activity.save(update_fields=['status'])

        response = self.client.get(reverse('activities:activity_detail', args=[self.activity.pk]))

        self.assertEqual(response.status_code, 404)


class CheckinViewTests(ActivityTestMixin, TestCase):
    def setUp(self):
        self.teacher = self.create_user('teacher', role='teacher')
        self.student = self.create_user('student')
        self.activity = self.create_activity(self.teacher, checkin_code='ABC123')
        self.registration = Registration.objects.create(user=self.student, activity=self.activity)
        self.client.force_login(self.student)

    def test_valid_code_completes_checkin_and_records_request_metadata(self):
        response = self.client.post(
            reverse('activities:checkin', args=[self.activity.pk]),
            {'checkin_code': 'abc123'},
            HTTP_USER_AGENT='Django test client',
        )
        self.registration.refresh_from_db()

        self.assertRedirects(response, reverse('activities:activity_detail', args=[self.activity.pk]))
        self.assertTrue(self.registration.is_checked_in)
        self.assertEqual(self.registration.checkin_log[0]['user_agent'], 'Django test client')

    def test_invalid_code_does_not_complete_checkin(self):
        self.client.post(
            reverse('activities:checkin', args=[self.activity.pk]),
            {'checkin_code': 'WRONG1'},
        )
        self.registration.refresh_from_db()

        self.assertFalse(self.registration.is_checked_in)
        self.assertEqual(self.registration.checkin_log, [])


class TeacherPermissionTests(ActivityTestMixin, TestCase):
    def setUp(self):
        self.owner = self.create_user('owner', role='teacher')
        self.other_teacher = self.create_user('other', role='teacher')
        self.student = self.create_user('student')
        self.activity = self.create_activity(self.owner)
        self.registration = Registration.objects.create(user=self.student, activity=self.activity)

    def test_non_owner_teacher_cannot_view_checkin_list(self):
        self.client.force_login(self.other_teacher)

        response = self.client.get(reverse('activities:checkin_list', args=[self.activity.pk]))

        self.assertRedirects(response, reverse('activities:activity_detail', args=[self.activity.pk]))

    def test_owner_can_export_excel_compatible_csv(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('activities:export_checkin', args=[self.activity.pk]))
        content = response.content.decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(content)))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(rows[0][0:3], ['姓名', '学号/工号', '学院'])
        self.assertEqual(rows[1][0], 'student')

    def test_checkin_code_rotation_requires_post(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('activities:refresh_checkin_code', args=[self.activity.pk]))

        self.assertEqual(response.status_code, 405)
