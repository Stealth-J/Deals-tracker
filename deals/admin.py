from django.contrib import admin
from .models import Deals, Profile, UserDeal, AlertHistory,PriceHistory, ScrapeFailure

# Register your models here.
admin.site.register(Deals)
admin.site.register(Profile)
admin.site.register(UserDeal)
admin.site.register(AlertHistory)
admin.site.register(PriceHistory)
admin.site.register(ScrapeFailure)