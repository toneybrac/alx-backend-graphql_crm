# alx_backend_graphql/settings.py (or wherever your settings are)
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'graphene_django',
    'django_filters',
    'django_crontab',  # Add django-crontab

    # Local apps
    'crm',
    'customers',
    'orders',
]



# Django Crontab Configuration
CRONJOBS = [
    # Run heartbeat every 5 minutes
    ('*/5 * * * *', 'crm.cron.log_crm_heartbeat'),
]

# Optional: Where to store cron job logs
CRONTAB_COMMAND_SUFFIX = '2>&1'  # Redirect stderr to stdout

# Optional: Lock file settings to prevent overlapping jobs
CRONTAB_LOCK_JOBS = True

# Optional: Django project path for cron jobs
CRONTAB_DJANGO_PROJECT_DIR = str(BASE_DIR)

# Optional: Python path for cron jobs
CRONTAB_PYTHON_EXECUTABLE = sys.executable

# Optional: Logging configuration for cron jobs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/tmp/django_cron.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'crm_cron': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
