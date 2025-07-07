import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deals_project.settings')

celery_app = Celery('deals_project')

# celery looks for settings beginning with CELERY 
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

celery_app.autodiscover_tasks()
