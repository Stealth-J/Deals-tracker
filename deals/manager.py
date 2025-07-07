from django.db import models
from django.db.models import *
from django.conf import settings
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
from .models import *
from urllib.parse import urlparse, parse_qs, urlunparse
import requests
import httpx, asyncio
import re
import hashlib
from .decorators import timeit


months = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
ALLOWED_DOMAINS = ['jumia.com.ng', 'www.jumia.com.ng', 'konga.com', 'www.konga.com']
HEADERS = {"User-Agent": "Mozilla/5.0"}

class AlertQueryset(models.QuerySet):
    def unread(self):
        return self.filter(seen = False)
    
    def read(self):
        return self.filter(seen = True)
    
    def alert_count(self):
        count = self.filter(seen = False).count()
        return count
    
    

def check_for_numbers(string):
    return any(x.isdigit() for x in string)



def paginate(request, alerts_filtered):
    paginator = Paginator(alerts_filtered, settings.PAGE_SIZE)
    page_num = request.GET.get('page')
    alerts_qs = paginator.get_page(page_num)
    
    return alerts_qs


def filter_for_months(request, alerts_all, months_list):
    months_indexes = []
            
    for month in months_list.split(', '):
        index_ = months.index(month)
        months_indexes.append(index_ + 1)

    alerts_filtered = alerts_all.filter(time_sent__month__in = months_indexes)
    
    return alerts_filtered


def filter_for_date(date_input, alerts_all):
    try:
        date_list = [int(x) for x in date_input.split('-')]
    except:
        raise TypeError("Date has to be just numbers")
    
    date_obj = date(*date_list)
    alerts_filtered = alerts_all.filter(time_sent__date__gte = date_obj)
    
    return alerts_filtered


def custom_filter(request, alerts_all, pagination = True):
    if request.method == 'POST':
        date_filter = request.POST.get('date_filter')
        search_word = request.POST.get('search')
    elif request.method == 'GET':
        date_filter = request.GET.get('date_filter')
        search_word = request.GET.get('search')
    
    if date_filter:
        if not check_for_numbers(date_filter):
            alerts_filtered = filter_for_months(request, alerts_all, date_filter)
        
        elif check_for_numbers(date_filter):
            if '-' in date_filter:
                alerts_filtered = filter_for_date(date_filter, alerts_all)
            else:
                alerts_filtered = alerts_all.filter(time_sent__year = int(date_filter))

    else:
        alerts_filtered = alerts_all

    if search_word:
        alerts_filtered = alerts_filtered.filter(deal__name__icontains = search_word)


    read_alerts_qs = paginate(request, alerts_filtered.read())
    unread_alerts = paginate(request, alerts_filtered.unread()) 

    if pagination == False:
        return alerts_filtered

    return read_alerts_qs, unread_alerts 


def hash_piece(html):
    return hashlib.md5(html.encode()).hexdigest()


def validate_url(url):
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return (False, 'URL is not valid.')
    
    except Exception:
        return (False, 'Malformed URL')
    
    domain = parsed.netloc.lower()
    if domain not in ALLOWED_DOMAINS:
        return (False, f"URL must be from Jumia or Konga. You provided: {domain}")

    return (True, '')

@timeit(label = "validating and fetching url")
def validate_and_fetch_url(url):
    success, text = validate_url(url)
    if not success:
        return (success, text)
    
    try:
        response = requests.get(url, timeout = 7, headers = HEADERS)
        print("Fetch time:", response.elapsed.total_seconds())

        response.raise_for_status()
        return (True, response.text)

    except Exception as e:
        return (False, f'Failed to fetch URl: {str(e)}')


async def async_validate_and_fetch_url(url, client):
    success, text = validate_url(url)
    if not success:
        return (success, text, 0)
    
    try:
        response = await client.get(url, follow_redirects = False)  # to get 302 code

        if response.status_code == 302:
            location = response.headers.get('location', 'Unknown')
            return (False, f"URL redirected (302) to '{location}'", 302)
        
        response.raise_for_status()
        return(True, response.text, response.status_code)
    
    except httpx.HTTPStatusError as e:
        return (False, f"HTTP error: {str(e)}", e.response.status_code)

    except httpx.RequestError as e:
        return (False, f"Request error: {str(e)}", -1) 

    except Exception as e:
        # Something unexpected
        return (False, f"Unexpected error while fetching url: {str(e)}", -2)


def normalize_url(url):
    parsed = urlparse(url)
    netloc = parsed.netloc
    if not parsed.netloc.startswith('www.'):
        netloc = 'www.' + netloc
        
    return urlunparse(parsed._replace(netloc = netloc))


def remove_non_numbers(text):
    text = str(text)
    return re.sub(r'[^\d.]', '', text)

def jumia_price_formatter(text):
    text = str(text).replace('₦', '').replace(' ', '').replace(',', '')

    if '-' in text:
        parts = text.split('-')
        digits = [re.sub(r'[^\d]', '', p) for p in parts if re.sub(r'[^\d]', '', p)]

        if len(digits) == 2:
            low, high = int(digits[0]), int(digits[1])
            formatted = f"₦ {low:,} - {high:,}"
            return str(low), formatted

    # No dash or only one valid number
    digits_only = re.sub(r'[^\d]', '', text)
    return digits_only, None