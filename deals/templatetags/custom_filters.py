from django import template
from deals.models import User, Deals, UserDeal
import re

register = template.Library()

@register.filter
def return_none(search_word):
    if search_word == None:
        return ''
    return search_word

@register.filter
def shorten_notifications(number_of_notifs):
    if int(number_of_notifs) > 99:
        return '99+'
    
    return number_of_notifs

@register.filter
def remove_naira(value):
    value = str(value).replace('₦', '').replace(' ', '')
    
    if '-' in value:
        parts = value.split('-')
        formatted_parts = [f"{int(re.sub(r'[^\d]', '', p)):,}" for p in parts if re.sub(r'[^\d]', '', p)]
        return f"₦ {' - '.join(formatted_parts)}" if formatted_parts else ''
    digits = re.sub(r'[^\d]', '', value)
    return f"₦ {int(digits):,}" if digits else ''

@register.filter
def return_lowest_price(string):
    string = str(string)
    value = string.replace('₦', '').replace(' ', '').replace(',', '')
    if '-' in string:
        prices = value.split('-')
        prices = [int(price) for price in prices]

        value = min(prices)

    return value

@register.filter
def to_list(length):
    list_ = [ i+1 for i in range(length)]
    return list_

@register.filter
def minus_one(num):
    if num == 1:
        return 1
    num = int(num)
    return num - 1

@register.filter
def lte(value, arg):
    return value <= arg