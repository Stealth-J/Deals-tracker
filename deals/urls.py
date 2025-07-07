from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name="index"),
    path('profile', profile, name = "profile"),
    path('edit-profile', edit_profile, name = "edit_profile"),
    path('dashboard', dashboard, name="dashboard"),
    path('all-deals', all_deals, name="deals"),
    path('add-deal', add_deal, name="add_deal"),
    path('cancel-deal-tracker/<int:pk>', cancel_deal_tracker, name="cancel_deal_tracker"),
    path('add-user-deal/<int:pk>', add_user_deal, name="add_user_deal"),
    path('message', message, name="message"),

    path('edit-user-deal/<int:pk>', edit_user_deal, name="edit_user_deal"),
    path('delete-user-deal/<int:pk>', delete_user_deal, name="delete_user_deal"),

    path('alerts', alerts, name="alerts"),
    path('load-more-alerts/<str:viewed>', load_more_alerts, name="load-more-alerts"),

    path('load_read_alert/<int:pk>', load_read_alert, name="load_read_alert"),
    path('reload-unread-alerts', reload_unread_alerts, name="reload-unread-alerts"),

    path('delete_alert/<str:pk>', delete_alert, name="delete_alert"),

    path('product-detail/<str:slug>', product_detail, name="product-detail")
]