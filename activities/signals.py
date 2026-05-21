from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    当 User 被保存时触发：
    如果是新创建的用户 (created=True)，则创建对应的 Profile。
    """
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    当 User 被保存时，自动保存对应的 Profile。
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()