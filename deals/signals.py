from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from .models import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=User)
def user_postsave(sender, instance, created, **kwargs):
    user = instance

    if created:
        Profile.objects.create(user = user)

# deleting every other duplicate file
@receiver(pre_save, sender=Profile)
def profile_image_clean(sender, instance, **kwargs):
    if not instance.pk:
        return
    
    if instance.image:
        try:
            old_profile = Profile.objects.get(pk = instance.pk)
        except Profile.DoesNotExist:
            return
        
        old_image = old_profile.image
        new_image = instance.image

        if old_image and old_image != new_image:
            if not Profile.objects.filter(image = old_image).exclude(pk = instance.pk).exists():
                old_image.delete(save=False)


# @receiver(post_save, sender = Deals)
# def update_price_history(sender, instance, created, **kwargs):

#     if not created and instance.current_price != instance.old_price:
#         PriceHistory.objects.create(deal = instance, price = instance.old_price)
    
#         price_history_qs = instance.price_history.order_by('-timestamp')

#         if price_history_qs.count() > 10:
#             to_delete = price_history_qs[10:]
#             to_delete_ids = to_delete.values_list('id', flat = True)
#             price_history_qs.filter(id__in = to_delete_ids).delete()




@receiver(pre_save, sender=User)
def user_presave(sender, instance, **kwargs):
    if instance.username:
        instance.username = instance.username.lower()