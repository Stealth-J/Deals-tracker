from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from django.template.loader import render_to_string
from render_block import render_block_to_string
import json
from .models import *

class AlertMsgConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            self.close()
            return
        
        self.GROUP_NAME = f'user_{self.user.id}-notifs'
        async_to_sync(self.channel_layer.group_add)(
            self.GROUP_NAME, self.channel_name
        )

        self.accept()

    def disconnect(self, code):
        if self.user.is_authenticated:
            async_to_sync(self.channel_layer.group_discard)(
                self.GROUP_NAME, self.channel_name
            )

    def update_alerts(self, event):
        html = render_block_to_string('partials/navbar.html', 'bell_icon', {'user': self.user})
        self.send(text_data = html)

    def add_new_alerts(self, event):
        new_alerts_ids = event['ids']
        alerts_obj = AlertHistory.objects.filter(id__in = new_alerts_ids)
        
        html = render_to_string('partials/unread_alert_card.html', {'new_alerts': alerts_obj})
        self.send(text_data = html)


class DealsPricesUpdateConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            'deals_updates', self.channel_name
        )

        if self.scope['user'].is_authenticated:
            self.user = self.scope['user']
        else:
            self.user = None

        self.accept()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            'deals_updates', self.channel_name
        )

    def return_updated_prices(self, event):
        updated_deals_ids = event['updated_deals']
        updated_deals = Deals.objects.filter(id__in = updated_deals_ids)

        if self.user != None:
            userdeals = UserDeal.objects.filter(user = self.user, deal__id__in = updated_deals_ids)

        context = {
            'updated_deals': updated_deals,
            'userdeals': userdeals or None
        }
        
        html = render_to_string('partials/deal_cards_text.html', context)
        self.send(text_data = html)