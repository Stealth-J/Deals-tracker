from django.shortcuts import render, get_object_or_404, redirect
from .models import User, Profile, Deals, UserDeal, AlertHistory, PriceHistory
from django.http import HttpResponse, JsonResponse
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
import json
from render_block import render_block_to_string
from .manager import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .decorators import verified_email_required
import requests_cache
from .scraper import search_word_scraper, timezone
from .tasks import save_price_hash



# Create your views here.
def index(request):
    keyword = False

    if request.user.is_authenticated:
        if not request.user.emailaddress_set.filter(verified=True).exists():
            messages.warning(request, "You need to verify your email to continue.")
    else:
        messages.warning(request, 'You are not logged in')

    items = []
    page_limit = 1
    search = request.GET.get('search')
    url = request.GET.get('url')
    store = request.GET.get('store')
    page = int(request.GET.get('page') or 1)


    if store:
        if search or url:
            store = int(store)
            keyword = True
            requests_cache.install_cache('jumia_cache', expire_after = 360)
            
            if url:
                url = request.GET.get('url')
                param_index = 1

            else:
                search_formatted = search.replace(' ', '+')
                param_index = 0

                url = f'https://www.jumia.com.ng/catalog/?q={search_formatted}&page={page}'
                # url = f'https://www.konga.com/search?search={search}'

            success, items, page_limit = search_word_scraper(search, url, param_index, store)

            if not success:
                return render(request, 'error.html', {'message': items, })
            
    
    return render(request, 'index.html', {'items': items, 'keyword': keyword, 'page': page, 'page_limit': int(page_limit)})



@verified_email_required
def profile(request):
    context = {}
    return render(request, 'user_profile.html', context)


@verified_email_required
def edit_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    form = ProfileForm(instance = profile)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile_updated = form.save(commit= False)
            profile_updated.user.email = request.POST['user_mail']
            profile_updated.user.save()
            profile_updated.save()

            return render(request, 'partials/profile-card.html')
        
        return render(request, 'partials/profile-edit_form.html', {'form': form})


    context = {'form': form}
    return render(request, 'partials/profile-edit_form.html', context)


@verified_email_required
def dashboard(request):
    user_deals = UserDeal.objects.select_related('deal', 'user').filter(user = request.user)

    context = {'user_deals': user_deals}
    return render(request, 'dashboard.html', context)


def all_deals(request):
    deals = Deals.objects.all()

    if request.method == 'POST':
        sort = request.POST.get('sort') or 'Default'
        order = request.POST.get('order')
        search_word = request.POST.get('deal_search') or None

        sort_fields = {
            'Profit': ExpressionWrapper( F('old_price') - F('current_price'), output_field= DecimalField()),
            'Members tracking': Count('members_tracking'),
            'A-Z': 'name',
            'Price': 'current_price',
            'Default': 'id'
        }
        sort_expr = sort_fields.get(sort)

        if search_word:
            deals = deals.filter(name__icontains = search_word)

        if sort == 'Profit':
            deals = deals.annotate(profit = sort_expr)
            sort_key = 'profit'
        elif sort == 'Members tracking' :
            deals = deals.annotate(trackers = sort_expr)
            sort_key = 'trackers'
        elif sort_expr:
            sort_key = sort_expr
    
        if order == 'asc':
            deals = deals.order_by(sort_key)
        else:
            deals = deals.order_by(f'-{sort_key}')


        html = render_block_to_string('all_deals.html', 'dealsContainer', {'all_deals': deals}, request)
        return HttpResponse(html)


    context = {'all_deals': deals}
    return render(request, 'all_deals.html', context)


@verified_email_required
def add_deal(request):
    print(request.POST)
    name = request.POST.get('product_name')
    image = request.POST.get('image') or None
    url = request.POST.get('product_url')
    current_price = request.POST.get('current_price')
    old_price = request.POST.get('old_price') or None
    price_text = request.POST.get('price_text') or None
    threshold = request.POST.get('threshold')
    store = request.POST.get('market_store')

    url = normalize_url(url)

    if Deals.objects.filter(url = url).exists():
        msg_info = 'You are already tracking this product'
    else:
        deal_obj = Deals.objects.create(
            name = name,
            image_path = image, 
            url = url,
            current_price = current_price,
            old_price = old_price,
            last_checked = timezone.now(),
            price_text = price_text,
            store = store,
        )
        deal_obj.members_tracking.add(request.user)

        userdeal = UserDeal.objects.create(
            user = request.user,
            deal = deal_obj,
            threshold_price = threshold,
        ) 
        save_price_hash.delay(deal_obj.id)
        request.user.profile.total_deals_tracked += 1
        request.user.profile.save()

        price_history_objs = []
        price_history_objs.append(PriceHistory(deal = deal_obj, price = current_price))

        if old_price != None:
            price_history_objs.append(PriceHistory(deal = deal_obj, price = old_price))
        
        PriceHistory.objects.bulk_create(price_history_objs)

        msg_info = f'You are now tracking "{name}". Ensure to turn on notifications to receive updates.'

    messages.success(request, msg_info)

    response = HttpResponse('')
    response['HX-Trigger'] = 'message'
    return response


@verified_email_required
def add_user_deal(request, pk):
    deal = Deals.objects.get(pk = pk)
    userdeal = UserDeal.objects.filter(user = request.user, deal = deal)
    context = {'deal': deal}
    
    if request.method == 'POST' and not userdeal.exists():
        threshold = float(request.POST.get('threshold'))
        userdeal = UserDeal.objects.create(user = request.user, deal = deal, threshold_price = threshold)
        deal.members_tracking.add(request.user)
        request.user.profile.total_deals_tracked += 1
        request.user.profile.save()
        messages.success(request, f'You are now tracking {deal.name}. Head to Track Deals for more')

        response = render(request, 'partials/deals_cards.html', context)
        response['HX-Trigger'] = 'message'
        return response

    return render(request, 'partials/add_deal.html', context)


@verified_email_required
def edit_user_deal(request, pk):
    deal = Deals.objects.get(id = pk)
    userdeal = UserDeal.objects.filter(user = request.user, deal = deal)
    context = {'deal': deal, 'userdeal': userdeal[0]}

    import time
    time.sleep(2)

    if request.method == 'POST' and userdeal.exists():
        userdeal = userdeal[0]
        threshold = float(request.POST.get('threshold'))
        edit_type = request.POST.get('edit_type') or 'all'
        userdeal.threshold_price = threshold
        userdeal.save()

        messages.success(request, f'You have successfully updated {deal.name} threshold price')

        if edit_type == "dashboard":
            return render(request, 'partials/tracked_deal-cards.html', {'user_deal': userdeal})
        
        response = render(request, 'partials/deals_cards.html', context)
        response['HX-Trigger'] = 'message'
        return response


    return render(request, 'partials/edit_deal.html', context)


@verified_email_required
def delete_user_deal(request, pk):
    userdeal = UserDeal.objects.filter(id = pk)
    if userdeal:
        userdeal[0].deal.members_tracking.remove(request.user)
        userdeal[0].delete()
        request.user.profile.total_deals_tracked
        request.user.profile.save()
        messages.info(request, f'{userdeal[0].deal.name} is not being tracked anymore')

        response = HttpResponse("")
        response['HX-Trigger'] = 'message'
        return response
    
    return HttpResponse('An error occurred')


@verified_email_required
def cancel_deal_tracker(request, pk):
    deal = Deals.objects.get(pk = pk)

    return render(request, 'partials/deals_cards.html', {'deal': deal})


@verified_email_required
def alerts(request):
    alerts_all = AlertHistory.objects.select_related('user', 'deal').filter(user = request.user)
    unread_alerts = alerts_all.unread()
    read_alerts = alerts_all.read()

    read_alerts_qs = paginate(request, read_alerts)
    unread_alerts = paginate(request, unread_alerts)
    
    context = {'unread_alerts': unread_alerts, 'read_alerts': read_alerts_qs, 'months': months, }

    if request.method == 'POST':
        read_alerts_qs, unread_alerts = custom_filter(request, alerts_all)
        tab = int(request.POST.get('tab')) or 1

        context = {
            'read_alerts': read_alerts_qs, 
            'unread_alerts': unread_alerts,
            'search_word': request.POST.get('search')
        }

        html = render_block_to_string('alerts.html', f'tab{tab}', context, request)
        response =  HttpResponse(html)
        response['HX-Trigger'] = "filtered_results"
        response['HX-Retarget'] = f'#tab-content{tab}'
        return response
    

    return render(request, 'alerts.html', context)


@verified_email_required
def load_more_alerts(request, viewed):
    if viewed == "read":
        read_alerts = AlertHistory.objects.select_related('user', 'deal').filter(user = request.user, seen = True)

        read_alerts_qs, _ = custom_filter(request, read_alerts)
        context = {'read_alerts': read_alerts_qs}

        html = render_block_to_string('partials/alerts_loop.html', 'read_alerts_loop', context, request)
        return HttpResponse(html)
    
    elif viewed == 'unread':
        unread_alerts = AlertHistory.objects.select_related('user', 'deal').filter(user = request.user, seen = False)
        
        _, unread_alerts_qs = custom_filter(request, unread_alerts)
        context = {'unread_alerts': unread_alerts_qs}

        html = render_block_to_string('partials/unread_alerts.html', 'unread_alerts_loop', context, request)
        return HttpResponse(html)



@verified_email_required
def load_read_alert(request, pk):
    all_alerts_main = AlertHistory.objects.select_related('user', 'deal').filter(user=request.user)
    all_alerts = custom_filter(request, all_alerts_main, pagination = False)

    if pk == 0:
        print('stretham')
        read_alerts = all_alerts.filter(seen = False)
        for i in read_alerts:
            i.seen = True
        
        AlertHistory.objects.bulk_update(read_alerts, ['seen'], batch_size = 50)
        return redirect('alerts')
    else:
        read_alerts = all_alerts.filter(id = pk)

        for read_alert in read_alerts:
            read_alert.seen = True
            read_alert.save()


    response = render(request, 'partials/alerts_loop.html', {'read_alerts': read_alerts})
    response['HX-Trigger'] = json.dumps({'update_bell_number' : {'unreadCount': all_alerts_main.alert_count()}})
    
    if all_alerts_main.alert_count() == 0:
        response['HX-Trigger'] = json.dumps({'check_for_new_alerts': {'remove_number_on_bell': True}})

    elif all_alerts.alert_count() == 0:
        response['HX-Trigger'] = json.dumps({'check_for_new_alerts': {'remove_number_on_bell': False}, 'update_bell_number' : {'unreadCount': all_alerts_main.alert_count()}})


    return response


@verified_email_required
def reload_unread_alerts(request):
    all_alerts = AlertHistory.objects.select_related('user', 'deal').filter(user = request.user)
    all_alerts = custom_filter(request, all_alerts, pagination = False)
    unread_alerts = all_alerts.unread()

    return render(request, 'partials/unread_alerts.html', {'unread_alerts': unread_alerts})


@verified_email_required
def delete_alert(request, pk):
    all_alerts = AlertHistory.objects.select_related('user', 'deal').filter(user = request.user)

    if not pk.isdigit():
        alert_ids = request.POST.getlist('alert_ids')

        delete_obj = all_alerts.filter(id__in = [int(i) for i in alert_ids])
        message_ = f'Successfully deleted {len(alert_ids)} alerts'
        count_ = all_alerts.alert_count()
        

    else:
        pk = int(pk)

        if pk == 0:
            delete_obj = all_alerts
            message_ = 'Successfully deleted every alert. You have no alerts '
            count_ = 0
        else:
            delete_obj = all_alerts.filter(id = pk)
            if not delete_obj.first().seen:
                count_ = all_alerts.alert_count() - 1
            else:
                count_ = None
            message_ = "Successfully deleted alert"

    for i in delete_obj:
        i.delete()
    
    messages.info(request, message_)
    response = HttpResponse("")
    
    if count_ == 0:
        response['HX-Trigger'] = json.dumps({'check_for_new_alerts': {'remove_number_on_bell': True}, 'message': message_})

    elif count_ == None:
        response['HX-Trigger'] = 'message'

    else:
        response['HX-Trigger'] = json.dumps({'check_for_new_alerts': {'remove_number_on_bell': False}, 'update_bell_number' : {'unreadCount': count_}, 'message': message_, })

    return response


def product_detail(request, slug):
    user = request.user
    threshold_price = None
    deal = Deals.objects.prefetch_related('price_history', 'members_tracking').filter(slug = slug).first()

    history_qs = deal.price_history.all().order_by('timestamp')
    data_ = list(history_qs.values_list('price', flat = True))
    dates_ = list(history_qs.values_list('timestamp', flat = True))

    data = [float(d) for d in data_] 
    dates = [d.strftime("%b %d, %H:%M") for d in dates_] 

    if user.is_authenticated and user in deal.members_tracking.all():
        user_deal = UserDeal.objects.filter(user = request.user, deal = deal).first()
        threshold_price = user_deal.threshold_price 

    context = {
        'deal': deal,
        'earliest': history_qs.first(),
        'latest': history_qs.last(),
        'data': data,
        'dates': dates,
        'threshold': threshold_price
    }
    return render(request, 'product_detail.html', context)


@verified_email_required
def message(request):
    return render(request, 'partials/messages.html')

