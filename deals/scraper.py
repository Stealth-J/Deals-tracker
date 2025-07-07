from django.utils.timezone import now
import random
from .models import *
from django.utils import timezone
from .manager import *
from types import SimpleNamespace
from selectolax.parser import HTMLParser
import json


MAX_RETRIES = 3

def get_product_url(article, url):
    return 'https://jumia.com.ng' + article.css_first('.core').attributes.get('href')

def return_url(article, url):
    return url

def page_limit(tree):
    pagination_btns = tree.css('.pg')
    if pagination_btns:
        last_btn = pagination_btns[-1]
        pagination_links = tree.css('a.pg')

        if last_btn in pagination_links:
            href = last_btn.attributes.get('href')
            parsed_url = urlparse(href)
            params = parse_qs(parsed_url.query)
            return params.get('page', ['1'])[0]
        
        act = tree.css_first('._act').text(strip = True)
        return act
    
    return '1'

img_src = 'https://static.vecteezy.com/system/resources/previews/008/695/917/non_2x/no-image-available-icon-simple-two-colors-template-for-no-image-or-picture-coming-soon-and-placeholder-illustration-isolated-on-white-background-vector.jpg'

JUMIA = [{'article': 'article.prd', 'name': '.name', 'price': '.prc', 'img': '.img', 'old_price': '.old', 'product_url': get_product_url, 'price_gain': '.bdg._dsct'}, {'article': 'section.col12', 'name': 'h1.-fs20', 'price': 'span.-fs24', 'img': 'img.-fw.-fh', 'old_price': 'span.-tal.-gy5', 'product_url': return_url, 'price_gain': '.bdg._dsct'}]

IMAGE_PATH = 'https://www-konga-com-res.cloudinary.com/f_auto,fl_lossy,dpr_auto,q_auto/media/catalog/product'
BASE_URL = 'https://www.konga.com/product/'

# KONGA = [{'article': 'li.List_listItem__KlvU2', 'name': 'h3.ListingCard_productTitle__9Kzxv', 'price': 'span.7shared_price__gnso_', 'img': 'img.f5e10_VzEXF', 'old_price': 'span.f6eb3_1MyTu',  'price_gain': 'span._6977e_X5mZi', 'product_url': get_product_url_konga}, {'article': 'div._8f9c3_230YI', 'name': 'h4._24849_2Ymhg', 'price': 'div._678e4_e6nqh', 'img': 'img._72d4f_1Tx1j', 'old_price': 'div._10344_3PAla', 'product_url': return_url, 'price_gain': 'span.b3d46_3IwtW'}]
stores = ['jumia', 'konga']


def konga_scraper(tree, items):
    try:
        data = tree.css_first('#__NEXT_DATA__')
        parsed = json.loads(data.text())
        name =  parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["name"]
        image_full = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["image_full"]
        url_key = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["url_key"]
        img_src = IMAGE_PATH + image_full
        product_url = BASE_URL + url_key
        price = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["special_price"]
        if not price:
            price = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["original_price"]
            price = f'₦ {price}'
            old_price, price_gain = '', ''
        else:
            old_price = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["original_price"]
            price_gain = ((int(old_price) - int(price)) / int(old_price)) * 100        
            price_gain = f'{round(price_gain)}%'
            old_price = f'₦ {old_price}'
    
    except:
        return []
    
    items.append(SimpleNamespace(name = name, price = price, src = img_src, old_price = old_price, price_gain = price_gain, product_url = product_url, store = 'konga'))
    return items

@timeit(label = 'actual scraping')
def search_word_scraper(search, url, type, store):
    success, response = validate_and_fetch_url(url)
    items = []
    if not success:
        return (False, response, None)

    tree = HTMLParser(response)

    if store == 1:
        items = konga_scraper(tree, items)

    else:
        for article in tree.css(JUMIA[type]['article'])[:25]:
            try:
                name = article.css_first(JUMIA[type]['name']).text(strip= True) 
                price = article.css_first(JUMIA[type]['price']).text(strip= True)
                product_url = JUMIA[type]['product_url'](article, url)

                if article.css_first(JUMIA[type]['img']):
                    img_src = article.css_first(JUMIA[type]['img']).attributes.get('data-src')

                old_price, price_gain = '', ''
                if article.css_first(JUMIA[type]['old_price']):
                    old_price = article.css_first(JUMIA[type]['old_price']).text(strip= True)
                    price_gain = article.css_first(JUMIA[type]['price_gain']).text(strip = True)

            except Exception as e:
                continue

            items.append(SimpleNamespace(name = name, price = price, src = img_src, old_price = old_price, price_gain = price_gain, product_url = product_url, store = 'jumia'))

    if not items:
        search = search or url
        error_txt = f"Couldn't extract '{search}' data from the page. Please double-check the URL."

        if not tree.css('.article.prd'):
            error_txt = f" No results found for '{search}'. Try another word "
        
        return (False, error_txt, None)
    
    limit = page_limit(tree)
    
    return (True, items, limit)


class ScrapingError(Exception):
    def __init__(self, message, deal = None, status_code = None):
        super().__init__(message)
        self.deal = deal
        self.status_code = status_code



def scrape_price(store, tree, name_and_price_hash = False):
    if store == 'jumia':
        for article in tree.css(JUMIA[1]['article']):
            price = article.css_first(JUMIA[1]['price'])

        if name_and_price_hash:
            return price.html

    elif store == 'konga':
        data = tree.css_first('#__NEXT_DATA__')
        parsed = json.loads(data.text())

        name =  parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["name"]
        price = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["special_price"]
        if not price:
            price = parsed["props"]["initialProps"]["pageProps"]["data"]["product"]["original_price"]
        
        if name_and_price_hash:
            return str(name) + str(price)

    return price


class DealScraper:
    def __init__(self, deal):
        self.deal = deal

    async def fetch(self, client):
        success, response, status_code = await async_validate_and_fetch_url(self.deal.url, client)

        if not success:
            raise ScrapingError(response, self.deal, status_code)
        
        self.html = response
        self.status_code = status_code
        return self

    def get_current_price(self):
        store = self.deal.store
        if not self.html:
            raise ValueError('You are yet to fetch the url')
        
        tree = HTMLParser(self.html)

        try:
            if store == 'jumia':
                price = scrape_price('jumia', tree).text(strip = True)
                price, price_text = jumia_price_formatter(price)
                self.price_text = price_text
            elif store == 'konga':
                price = scrape_price('konga', tree)
                price = remove_non_numbers(price)
            else:
                fake_price = int(random.triangular(100, 300, 150))
                price = fake_price
                
        except Exception as e:
            raise ScrapingError('Price couldnt be scraped from this url', self.deal, -3)

        self.new_price = price    
        self.tree = tree
        return price

    def update_price(self):
        if not self.new_price:
            raise ValueError('You havent gotten current price yet')
        
        self.deal.old_price = self.deal.current_price
        self.deal.current_price = self.new_price
        self.deal.last_checked = timezone.now()
        if self.price_text:
            self.deal.price_text = self.price_text

        price = scrape_price(self.deal.store, self.tree, name_and_price_hash = True)
        self.deal.previous_price_hash = hash_piece(price)
        
        return self.deal


def log_error_obj(scraper, deal = None):
    if isinstance(scraper, ScrapingError):
        deal = scraper.deal
        fail_data = {'deal': deal, 'url': deal.url, 'error_message': str(scraper), 'status_code': scraper.status_code}
    else:
        fail_data = {'deal': deal, 'url': deal.url, 'error_message': str(scraper), 'status_code': -4}
            
    return fail_data


async def periodic_scraper(deals, return_success = False):
    updated_deals = []
    fails_data = []
    successful_scrapes = []
    

    async with httpx.AsyncClient(timeout = 10, headers = HEADERS) as client:
        tasks = [ DealScraper(deal).fetch(client) for deal in deals ]
        scrapers = await asyncio.gather(*tasks, return_exceptions = True)

        for scraper in scrapers:
            if isinstance(scraper, Exception):
                fail_data = log_error_obj(scraper)
                    
                fails_data.append(fail_data)
                continue

            try:
                new_price = scraper.get_current_price()
                if int(scraper.deal.current_price) != int(new_price):
                    print(f'price changed from {scraper.deal.current_price} to {new_price}')
                    updated_deal = scraper.update_price()
                    updated_deals.append(updated_deal)
                
                successful_scrapes.append(scraper.deal)

            except Exception as e:
                fail_data = log_error_obj(e, deal = scraper.deal)
                    
                fails_data.append(fail_data)
                continue

    if return_success:
        return updated_deals, fails_data, successful_scrapes
    return updated_deals, fails_data
    

async def retry_failed_scrapes(fails):
    updated_deals_all = []
    resolved_fails = []
    final_fails = []

    for attempt in range(1, MAX_RETRIES + 1):
        failed_deals = [ fail.deal for fail in fails ]
        updated_deals, fails_data, successful = await periodic_scraper(failed_deals, return_success = True)

        updated_deals_all.extend(updated_deals)

        new_fails = []

        for fail in fails:
            if fail.deal in successful:
                fail.is_resolved = True
                fail.retry_count = attempt
                resolved_fails.append(fail)
            else:
                fail.retry_count = attempt
                new_fails.append(fail)  

        fails = new_fails
        for f in fails:
            print(f"Retry {attempt} — still failing. Error code: {f.status_code} Message: {f.error_message}, {f.deal.name}")

        if not fails:     #  All resolved
            break
        if attempt == MAX_RETRIES:
            final_fails.extend(fails)
            break

        await asyncio.sleep(2 * attempt)

    failed_scrapes = resolved_fails + final_fails
    return updated_deals_all, failed_scrapes


async def scrape_and_retry_failed(deals):
    updated_deals, fails_data = await periodic_scraper(deals)
    fails = [ ScrapeFailure(**fail_data) for fail_data in fails_data ]

    if fails_data:
        updated, failed_scrapes = await retry_failed_scrapes(fails)
        updated_deals.extend(updated)

    return updated_deals, fails