"""
crm/cron.py
Cron jobs for the CRM application using django-crontab
"""

import os
import sys
import json
import logging
from datetime import datetime
import requests

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

# Try to import GraphQL client for optional health check
try:
    from gql import gql, Client
    from gql.transport.requests import RequestsHTTPTransport
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False
    print("Warning: gql library not available. GraphQL health check will be skipped.")

# Configuration
HEARTBEAT_LOG_FILE = "/tmp/crm_heartbeat_log.txt"
LOW_STOCK_LOG_FILE = "/tmp/low_stock_updates_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"

# ============ LOGGING HELPER FUNCTIONS ============

def log_to_file(message: str, log_file: str):
    """
    Log a message to a file with timestamp
    
    Args:
        message (str): The message to log
        log_file (str): Path to log file
    """
    try:
        # Ensure the directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Write message to log file (append mode)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Also log to console for immediate feedback
        print(log_entry.strip())
        
    except PermissionError:
        print(f"ERROR: Permission denied writing to {log_file}")
    except Exception as e:
        print(f"ERROR: Failed to log message: {str(e)}")

# ============ HEARTBEAT FUNCTIONS (EXISTING) ============

def log_heartbeat_message(message: str):
    """
    Log a message to the heartbeat log file
    
    Args:
        message (str): The message to log
    """
    log_to_file(message, HEARTBEAT_LOG_FILE)

def check_graphql_health() -> bool:
    """
    Check if the GraphQL endpoint is responsive
    
    Returns:
        bool: True if GraphQL endpoint is responsive, False otherwise
    """
    if not GRAPHQL_AVAILABLE:
        return False
    
    try:
        # Create GraphQL client
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=1,
            timeout=5
        )
        
        client = Client(
            transport=transport,
            fetch_schema_from_transport=False  # Don't fetch schema for simple health check
        )
        
        # Simple GraphQL query to check health
        query = gql("""
        query {
            hello
        }
        """)
        
        # Execute query
        result = client.execute(query)
        
        # Check if we got a response
        if 'hello' in result:
            return True
        else:
            return False
            
    except Exception as e:
        # Log the error but don't raise it - this is just a health check
        logging.debug(f"GraphQL health check failed: {str(e)}")
        return False

def log_crm_heartbeat():
    """
    Django-crontab job function that logs a heartbeat message every 5 minutes
    
    This function:
    1. Creates a timestamp in DD/MM/YYYY-HH:MM:SS format
    2. Logs "CRM is alive" message to /tmp/crm_heartbeat_log.txt
    3. Optionally checks GraphQL endpoint health
    4. Appends to the log file (does not overwrite)
    """
    # Get current timestamp in required format
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    
    # Check GraphQL health (optional)
    graphql_status = "Unknown"
    try:
        if GRAPHQL_AVAILABLE:
            is_healthy = check_graphql_health()
            graphql_status = "Healthy" if is_healthy else "Unhealthy"
        else:
            graphql_status = "Not checked (gql not available)"
    except Exception:
        graphql_status = "Check failed"
    
    # Create log message
    base_message = f"{timestamp} CRM is alive"
    
    # Optional: Add GraphQL status to message
    enhanced_message = f"{base_message} | GraphQL: {graphql_status}"
    
    # Log the message
    log_heartbeat_message(enhanced_message)
    
    # Also log to console for immediate feedback (optional)
    print(f"Heartbeat logged: {enhanced_message}")
    
    return f"Heartbeat logged at {timestamp}"

def log_crm_heartbeat_simple():
    """
    Simplified version without GraphQL check
    """
    # Get current timestamp in required format
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    
    # Create log message
    message = f"{timestamp} CRM is alive"
    
    # Log the message
    log_heartbeat_message(message)
    
    # Also log to console for immediate feedback
    print(f"Heartbeat logged: {message}")
    
    return f"Heartbeat logged at {timestamp}"

# ============ LOW-STOCK UPDATE FUNCTIONS (NEW) ============

def execute_low_stock_mutation():
    """
    Execute the UpdateLowStockProducts GraphQL mutation
    
    Returns:
        dict: Response from GraphQL API
    """
    # GraphQL mutation query with variables
    mutation = """
    mutation UpdateLowStockProducts($incrementBy: Int, $threshold: Int) {
        updateLowStockProducts(incrementBy: $incrementBy, threshold: $threshold) {
            success
            message
            totalUpdated
            updatedProducts {
                name
                oldStock
                newStock
            }
        }
    }
    """
    
    # Prepare the request
    headers = {
        'Content-Type': 'application/json',
    }
    
    payload = {
        'query': mutation,
        'variables': {
            'incrementBy': 10,  # Increment stock by 10
            'threshold': 10     # Products with stock < 10
        }
    }
    
    try:
        response = requests.post(
            GRAPHQL_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30  # 30 second timeout
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        return response.json()
        
    except requests.exceptions.ConnectionError:
        error_msg = f"Failed to connect to GraphQL endpoint: {GRAPHQL_ENDPOINT}"
        log_to_file(f"ERROR: {error_msg}", LOW_STOCK_LOG_FILE)
        raise Exception(error_msg)
    except requests.exceptions.Timeout:
        error_msg = "Request timed out"
        log_to_file(f"ERROR: {error_msg}", LOW_STOCK_LOG_FILE)
        raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP request failed: {str(e)}"
        log_to_file(f"ERROR: {error_msg}", LOW_STOCK_LOG_FILE)
        raise Exception(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response: {str(e)}"
        log_to_file(f"ERROR: {error_msg}", LOW_STOCK_LOG_FILE)
        raise Exception(error_msg)

def update_low_stock():
    """
    Cron job function to update low-stock products every 12 hours
    
    This function:
    1. Executes the GraphQL mutation to update low-stock products
    2. Logs updated product names and new stock levels
    3. Includes timestamps for each update
    4. Logs to /tmp/low_stock_updates_log.txt
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Log start of update
    log_to_file("=" * 50, LOW_STOCK_LOG_FILE)
    log_to_file(f"Starting low-stock product update at {timestamp}", LOW_STOCK_LOG_FILE)
    log_to_file("=" * 50, LOW_STOCK_LOG_FILE)
    log_to_file(f"Parameters: increment_by=10, threshold=10", LOW_STOCK_LOG_FILE)
    
    try:
        # Execute GraphQL mutation
        log_to_file("Executing GraphQL mutation: UpdateLowStockProducts", LOW_STOCK_LOG_FILE)
        result = execute_low_stock_mutation()
        
        # Check for GraphQL errors
        if 'errors' in result:
            errors = json.dumps(result['errors'], indent=2)
            log_to_file(f"GraphQL Errors: {errors}", LOW_STOCK_LOG_FILE)
            return False, "GraphQL errors occurred"
        
        # Extract mutation result
        data = result.get('data', {})
        mutation_result = data.get('updateLowStockProducts', {})
        
        success = mutation_result.get('success', False)
        message = mutation_result.get('message', 'No message returned')
        total_updated = mutation_result.get('totalUpdated', 0)
        updated_products = mutation_result.get('updatedProducts', [])
        
        # Log the results
        log_to_file(f"Mutation Result: {message}", LOW_STOCK_LOG_FILE)
        log_to_file(f"Success: {success}", LOW_STOCK_LOG_FILE)
        log_to_file(f"Total Products Updated: {total_updated}", LOW_STOCK_LOG_FILE)
        
        # Log details of each updated product
        if updated_products:
            log_to_file("Updated Products:", LOW_STOCK_LOG_FILE)
            for product in updated_products:
                product_name = product.get('name', 'Unknown Product')
                old_stock = product.get('oldStock', 'N/A')
                new_stock = product.get('newStock', 'N/A')
                
                log_entry = f"  - {product_name}: Stock {old_stock} → {new_stock}"
                log_to_file(log_entry, LOW_STOCK_LOG_FILE)
        else:
            log_to_file("No products were updated (either none found or all had sufficient stock)", LOW_STOCK_LOG_FILE)
        
        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Log completion
        log_to_file("-" * 50, LOW_STOCK_LOG_FILE)
        log_to_file(f"Update completed in {execution_time:.2f} seconds", LOW_STOCK_LOG_FILE)
        log_to_file("=" * 50, LOW_STOCK_LOG_FILE)
        
        return success, message
        
    except Exception as e:
        error_msg = f"Failed to update low-stock products: {str(e)}"
        log_to_file(f"ERROR: {error_msg}", LOW_STOCK_LOG_FILE)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_to_file("-" * 50, LOW_STOCK_LOG_FILE)
        log_to_file(f"Update failed after {execution_time:.2f} seconds", LOW_STOCK_LOG_FILE)
        log_to_file("=" * 50, LOW_STOCK_LOG_FILE)
        
        return False, error_msg

# ============ OPTIONAL CLEANUP FUNCTION ============

def cleanup_old_logs():
    """
    Optional cron job to clean up old log files
    Runs daily at midnight
    """
    import glob
    from datetime import datetime, timedelta
    
    log_files = [
        "/tmp/crm_heartbeat_log.txt",
        "/tmp/low_stock_updates_log.txt",
        "/tmp/customer_cleanup_log.txt",
        "/tmp/order_reminders_log.txt"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            if file_time < thirty_days_ago:
                # Archive old log file
                archive_name = f"{log_file}.{file_time.strftime('%Y%m%d')}.bak"
                os.rename(log_file, archive_name)
                log_to_file(f"Archived old log file: {log_file} → {archive_name}", HEARTBEAT_LOG_FILE)
    
    return "Log cleanup completed"

# ============ TEST FUNCTIONS ============

def test_low_stock_update():
    """Test function to manually run the low-stock update"""
    print("Testing low-stock product update...")
    success, message = update_low_stock()
    
    print(f"\nTest completed:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    
    # Show last few lines of log
    if os.path.exists(LOW_STOCK_LOG_FILE):
        print(f"\nLast 10 lines of log file ({LOW_STOCK_LOG_FILE}):")
        with open(LOW_STOCK_LOG_FILE, 'r') as f:
            lines = f.readlines()[-10:]
            for line in lines:
                print(line.rstrip())
    
    return success, message

def test_heartbeat():
    """Test function to verify cron job works"""
    print("Testing CRM heartbeat cron job...")
    result = log_crm_heartbeat()
    print(f"Result: {result}")
    
    # Verify the log was created
    if os.path.exists(HEARTBEAT_LOG_FILE):
        with open(HEARTBEAT_LOG_FILE, 'r') as f:
            last_line = f.readlines()[-1] if f.readlines() else "Empty"
        print(f"Last log entry: {last_line.strip()}")
    else:
        print("Log file not created. Check permissions.")

# ============ MAIN EXECUTION ============

if __name__ == "__main__":
    # Run both tests if script is executed directly
    print("=" * 50)
    print("CRM Cron Jobs Test Suite")
    print("=" * 50)
    
    print("\n1. Testing Heartbeat Function:")
    print("-" * 30)
    test_heartbeat()
    
    print("\n2. Testing Low-Stock Update Function:")
    print("-" * 30)
    test_low_stock_update()
    
    print("\n" + "=" * 50)
    print("All tests completed")
    print("=" * 50)
