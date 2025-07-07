from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
import time
from functools import wraps

def verified_email_required(func):

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')
        
        if not request.user.emailaddress_set.filter(verified = True).exists():
            messages.warning(request, 'You need to verify your email to continue.')
            return redirect("account_email_verification_sent")
        
        return func(request, *args, **kwargs)
    
    return wrapper


def timeit(label = None):    # so we can put arguments in teh decorator
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            tag = label or func.__name__
            print(f"[{tag}] took {duration:.2f} seconds")

            return result
        return wrapper
    return decorator

