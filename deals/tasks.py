from deals.models import Deals, AlertHistory, Profile, PriceHistory
from .scraper import *
from celery import shared_task
from django.core.mail import EmailMessage
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from collections import defaultdict
from django.db import close_old_connections
from django.db.models import Q


@shared_task
def send_mail(email, body):
    subject = 'Product prices dropping ⬇.'
    email = EmailMessage(subject, body, to = [email])
    email.send()



@shared_task
def tag_expired_urls():
    updated = []
    fails = ScrapeFailure.objects.filter(status_code = 302, retry_count__gt = 2)

    if fails:
        failed_deals = set(fail.deal for fail in fails)
        for deal in failed_deals:
            deal.expired = True
            updated.append(deal)
        
        Deals.objects.bulk_update(updated, ['expired'], batch_size = 30)

        fails.delete()


@shared_task
def tag_deformed_pages():
    updated = []
    fails = ScrapeFailure.objects.filter(status_code = -3, retry_count__gt = 2)

    if fails:
        failed_deals = set(fail.deal for fail in fails)
        for deal in failed_deals:
            deal.deformed = True
            updated.append(deal)
        
        Deals.objects.bulk_update(updated, ['deformed'], batch_size = 30)
        # fails.delete()

    tag_expired_urls.delay()


@shared_task
def delete_resolved_and_max_attempted_fails():
    pass 


@shared_task
def save_price_hash(obj_id):
    deal_obj = Deals.objects.filter(id = obj_id).first()

    success, response = validate_and_fetch_url(deal_obj.url)
    if success:
        tree = HTMLParser(response)
        price = scrape_price(deal_obj.store, tree, name_and_price_hash = True)
        hash = hash_piece(price)
        deal_obj.previous_price_hash = hash
        deal_obj.save()

    else:
        raise ScrapingError(response)


@shared_task
def update_price_history(instance_ids):
    price_history_list = []
    instances = Deals.objects.filter(id__in = instance_ids)

    for instance in instances:

        if instance.current_price != instance.old_price:
            price_history = PriceHistory(deal = instance, price = instance.current_price)
            price_history_list.append(price_history)
        
            price_history_qs = instance.price_history.order_by('-timestamp')

            if price_history_qs.count() > 11:
                to_delete = price_history_qs[11:]
                to_delete_ids = to_delete.values_list('id', flat = True)
                price_history_qs.filter(id__in = to_delete_ids).delete()

    PriceHistory.objects.bulk_create(price_history_list, batch_size= 30)
 

@shared_task
def update_alerts(user_id, new_alerts_ids):
    channel_layer = get_channel_layer()
    group_name = f'user_{user_id}-notifs'
    event = {'type': "update_alerts"}
    event2 = {'type': "add_new_alerts", 'ids': new_alerts_ids}

    async_to_sync(channel_layer.group_send)(
        group_name, event
    )
    async_to_sync(channel_layer.group_send)(
        group_name, event2
    )


@shared_task
def update_prices_display(updated_deals):
    channel_layer = get_channel_layer()
    group_name = 'deals_updates'
    event = {'type': 'return_updated_prices', 'updated_deals': updated_deals}

    async_to_sync(channel_layer.group_send)(
        group_name, event
    )


@shared_task
def check_and_update_prices():
    close_old_connections()     # good practice when using async
    deals = list(Deals.objects.exclude(Q(store = 'test') | Q(expired = True) | Q(deformed = True)))

    updated_deals, fails = async_to_sync(scrape_and_retry_failed)(deals)

    ScrapeFailure.objects.bulk_create(fails)
    Deals.objects.bulk_update(updated_deals, ['old_price', 'current_price', 'last_checked', 'previous_price_hash', 'price_text'])

    updated_deals_ids = [deal.id for deal in updated_deals]
    update_price_history.delay(updated_deals_ids)

    to_update_userdeals = []
    alerts_to_be_created= []
    user_ids_being_updated = []
    user_deals_map = defaultdict(list)
    update_prices_display.delay(updated_deals_ids)

    for userdeal in UserDeal.objects.select_related('deal', 'user').filter(deal__id__in = updated_deals_ids):
        if userdeal.user.email and userdeal.user.profile.notifications_enabled and userdeal.deal.current_price <= userdeal.threshold_price:
            user_deals_map[userdeal.user].append(userdeal)
    
    for user, userdeals in user_deals_map.items():
        lines = []

        for userdeal in userdeals:

            line = f'{userdeal.deal.name} is now ₦{userdeal.deal.current_price}.\nCheck it here: {userdeal.deal.url}'
            lines.append(line)

            userdeal.alert_sent = True
            to_update_userdeals.append(userdeal)

            alert = AlertHistory(user = userdeal.user, body = line, deal = userdeal.deal)
            alerts_to_be_created.append(alert)

            user_ids_being_updated.append(userdeal.user.id)

            if userdeal.user.profile.alerts_delete:
                excess_alerts = AlertHistory.objects.filter(user = userdeal.user, seen = True).order_by('-time_sent')[70:]
                excess_alerts_ids = excess_alerts.values_list('id', flat=True)
                AlertHistory.objects.filter(id__in = excess_alerts_ids).delete()

        body = '\n\n'.join(lines)
        body = '🔔 Price Drop Alert!\n\n' + body
        send_mail.delay(user.email, body)
        
            
    UserDeal.objects.bulk_update(to_update_userdeals, ['alert_sent'])
    new_alerts_list = AlertHistory.objects.bulk_create(alerts_to_be_created)
    new_alerts = AlertHistory.objects.filter(id__in = [alert.id for alert in new_alerts_list])

    for user_id in set(user_ids_being_updated):
        new_alerts_ids = [alert.id for alert in new_alerts.filter(user__id = user_id)]
        update_alerts.delay(user_id, new_alerts_ids)

        