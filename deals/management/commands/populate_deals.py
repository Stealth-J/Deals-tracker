from django.core.management.base import BaseCommand
from deals.models import Deals, User
import random
from datetime import datetime


class Command(BaseCommand):
    help = "Scrape and update deal prices"

    def handle(self, *args, **kwargs):
        names = ['jeffrey', 'jeff', 'clyde']
        emails = ['nosayamejeffrey@gmail.com', 'jeffridahosa@gmail.com', 'nosayameidahosa@gmail.com']
        pw = 'jeff2006'

        for name, email in zip(names, emails):
            new_user = User.objects.create_user(username=name, email=email, password= pw)
            new_user.save()
        
        
        
        
        
        
        
        
        
        
        
        
        # fake_urls = [
        #     "https://example.com/product/1",
        #     "https://example.com/product/2",
        #     "https://example.com/product/3",
        #     "https://example.com/product/4",
        #     "https://example.com/product/5",
        #     "https://example.com/product/6",
        #     "https://example.com/product/7",
        #     "https://example.com/product/8",
        #     "https://example.com/product/9",
        #     "https://example.com/product/10",
        # ]

        # deals = []
        # for i, url in enumerate(fake_urls, 1):
        #     deal = Deals(name=f"Product {i}", url = url, current_price = random.randint(10, 100), old_price=random.randint(10, 100))
        #     deals.append(deal)

        # Deals.objects.bulk_create(deals)
        