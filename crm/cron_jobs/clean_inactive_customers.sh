#!/bin/bash

# clean_inactive_customers.sh
# This script deletes customers with no orders since a year ago
# Run via cron job every Sunday at 2:00 AM

# Set the Django project path (adjust this based on your project structure)
DJANGO_PROJECT_PATH="/path/to/your/alx-backend-graphql_crm"
LOG_FILE="/tmp/customer_cleanup_log.txt"

# Change to Django project directory
cd "$DJANGO_PROJECT_PATH" || {
    echo "Error: Cannot change to directory $DJANGO_PROJECT_PATH" >> "$LOG_FILE"
    exit 1
}

# Activate virtual environment if needed (uncomment if using virtualenv)
# source venv/bin/activate

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Run Django shell command to delete inactive customers
# This assumes you have Customer and Order models
PYTHON_COMMAND="
import datetime
from django.utils import timezone
from your_app.models import Customer, Order

# Calculate date one year ago
one_year_ago = timezone.now() - datetime.timedelta(days=365)

# Find customers with no orders in the last year
customers_to_delete = []
for customer in Customer.objects.all():
    # Check if customer has any orders in the last year
    has_recent_order = Order.objects.filter(
        customer=customer, 
        created_at__gte=one_year_ago
    ).exists()
    
    if not has_recent_order:
        customers_to_delete.append(customer.id)

# Delete the customers
deleted_count = Customer.objects.filter(id__in=customers_to_delete).delete()[0]

print(f'Deleted {deleted_count} inactive customers')
"

# Execute the Python command and capture output
OUTPUT=$(python manage.py shell -c "$PYTHON_COMMAND")

# Log the results
echo "[$TIMESTAMP] $OUTPUT" >> "$LOG_FILE"

# Optional: Log success/failure
if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] Cleanup script executed successfully" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] Error executing cleanup script" >> "$LOG_FILE"
fi
