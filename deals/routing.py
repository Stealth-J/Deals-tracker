from django.urls import re_path
from .consumers import AlertMsgConsumer, DealsPricesUpdateConsumer

websocket_urlpatterns = [
    re_path('ws/test/', AlertMsgConsumer.as_asgi()),
    re_path('ws/deals/updates', DealsPricesUpdateConsumer.as_asgi()),
]
