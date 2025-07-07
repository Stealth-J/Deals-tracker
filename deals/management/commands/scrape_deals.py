from django.core.management.base import BaseCommand
from deals.models import Deals
from deals.scraper import scrape_price, DealScraper
from deals.tasks import check_and_update_tasks


class Command(BaseCommand):
    help = "Scrape and update deal prices"

    def handle(self, *args, **kwargs):
        all_deals = Deals.objects.all()
        updated_two = []

        for deal in all_deals:
            scraper = DealScraper(deal)
            changed = scraper.update_price
            updated_two.append(changed)

        Deals.objects.bulk_update(updated_two, ['current_price', 'old_price'], batch_size = 30)

