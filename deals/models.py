from django.db import models
from django.contrib.auth.models import User
from .manager import AlertQueryset, normalize_url
from django.utils.text import slugify

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank = True)
    image = models.ImageField(upload_to="avatars/", null=True, blank=True)

    notifications_enabled = models.BooleanField(default=True)
    total_deals_tracked = models.PositiveIntegerField(default=0)
    alerts_delete = models.BooleanField(default= True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    
    @property
    def avatar(self):
        if self.image:
            return self.image.url
            
        return "https://icons.veryicon.com/png/o/system/crm-android-app-icon/app-icon-person.png"
    
class Deals(models.Model):
    class StoreChoices(models.TextChoices):
        TEST = 'test',
        JUMIA = 'jumia',
        KONGA = 'konga',

    name = models.CharField(max_length=250)
    image_path = models.CharField(max_length = 150, null = True, blank = True)
    slug = models.SlugField(unique = True, blank = True, null = True)
    url = models.URLField(max_length = 500, unique = True)
    current_price = models.DecimalField(max_digits=15, decimal_places=2)
    old_price = models.DecimalField(max_digits=15, decimal_places=2, null = True, blank = True)
    last_checked = models.DateTimeField(blank=True, null=True)
    members_tracking = models.ManyToManyField(User)
    price_text = models.CharField(max_length= 50, null = True, blank = True)
    store = models.CharField(max_length = 10, choices = StoreChoices, default = StoreChoices.TEST)
    previous_price_hash = models.CharField(max_length = 32, null = True, blank = True) 
    expired = models.BooleanField(default = False)
    deformed = models.BooleanField(default = False)

    def __str__(self):
        return self.name
    
    def prices(self):
        if self.price_text:
            return self.price_text
        
        return '₦ ' + self.current_price
    

    def product_image(self):
        if self.image_path:
            return self.image_path
        
        return "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTxcYWo3fIGUqaLpD-Md1B5PzbsdYKPa23EWg&s"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def increase(self):
        if self.old_price:
            if self.current_price != self.old_price:
                return self.current_price < self.old_price
        return 'equals'
    
    @property
    def change(self):
        return self.current_price - self.old_price
    
    class Meta:
        verbose_name_plural = 'Deals'
    

class PriceHistory(models.Model):
    deal = models.ForeignKey(Deals, on_delete= models.SET_NULL, null = True, blank=True, related_name = 'price_history')
    price = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add= True)
    
    def __str__(self):
        return f'{self.deal.name} - {self.price}'

    class Meta:
        verbose_name_plural = 'Prices History'


class UserDeal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_deals")
    deal = models.ForeignKey(Deals, on_delete=models.CASCADE)
    threshold_price = models.DecimalField(max_digits=15, decimal_places=2)
    alert_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add = True)


class AlertHistory(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE, related_name="alerts")
    body = models.TextField(max_length=300)
    deal = models.ForeignKey(Deals, on_delete = models.SET_NULL, null=True, blank=True)
    time_sent = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default = False)

    objects = AlertQueryset.as_manager()

    def __str__(self):
        return f'Alert on {self.deal.name} sent to {self.user.username} at {self.time_sent.strftime("%m-%d %H:%M")}'
    
    class Meta:
        ordering = ['-time_sent']
    

class ScrapeFailure(models.Model):
    deal = models.ForeignKey(Deals, on_delete = models.SET_NULL, null=True, blank=True)
    url = models.URLField(null = True, blank = True)
    error_message = models.TextField()
    status_code = models.IntegerField(null=True, blank=True)  # optional
    attempted_at = models.DateTimeField(auto_now_add = True)
    retry_count = models.IntegerField(default = 0)  # if you track attempts
    is_resolved = models.BooleanField(default=False)  # optional cleanup logic
