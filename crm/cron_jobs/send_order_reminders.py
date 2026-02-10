#!/usr/bin/env python3
"""
send_order_reminders.py
Python script that queries GraphQL for pending orders and logs reminders.
Runs daily at 8:00 AM via cron job.
"""

import os
import sys
import datetime
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Try to import gql and related libraries
try:
    from gql import gql, Client
    from gql.transport.requests import RequestsHTTPTransport
except ImportError:
    print("Error: gql library not installed. Install it with: pip install gql[requests]")
    sys.exit(1)

# Configuration
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"

def setup_logging():
    """Setup logging to both console and file"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def get_graphql_client():
    """Create and return a GraphQL client"""
    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=3
        )
        
        client = Client(
            transport=transport,
            fetch_schema_from_transport=True
        )
        
        return client
    except Exception as e:
        raise Exception(f"Failed to create GraphQL client: {str(e)}")

def get_recent_pending_orders(client) -> List[Dict[str, Any]]:
    """
    Query GraphQL for orders with order_date within the last 7 days
    """
    # Calculate date 7 days ago
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # GraphQL query
    query = gql("""
    query GetRecentPendingOrders($sinceDate: String!) {
        pendingOrders(sinceDate: $sinceDate) {
            id
            orderNumber
            orderDate
            status
            totalAmount
            customer {
                id
                email
                firstName
                lastName
            }
            items {
                product {
                    name
                    sku
                }
                quantity
                price
            }
        }
    }
    """)
    
    # Execute query with parameters
    try:
        result = client.execute(query, variable_values={"sinceDate": seven_days_ago})
        return result.get('pendingOrders', [])
    except Exception as e:
        raise Exception(f"GraphQL query failed: {str(e)}")

def get_recent_pending_orders_alternative(client) -> List[Dict[str, Any]]:
    """
    Alternative GraphQL query in case the schema is different
    """
    # Calculate date 7 days ago
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # More flexible query that might work with different schemas
    query = gql("""
    query GetOrders($startDate: String!, $status: String) {
        orders(
            filter: {
                orderDate_gte: $startDate,
                status: $status
            }
            orderBy: orderDate_DESC
        ) {
            edges {
                node {
                    id
                    orderNumber
                    orderDate
                    status
                    totalAmount
                    customer {
                        email
                        firstName
                        lastName
                    }
                }
            }
        }
    }
    """)
    
    try:
        result = client.execute(query, variable_values={
            "startDate": seven_days_ago,
            "status": "PENDING"
        })
        
        # Extract nodes from edges
        orders = []
        if 'orders' in result and 'edges' in result['orders']:
            for edge in result['orders']['edges']:
                orders.append(edge['node'])
        
        return orders
    except Exception as e:
        # Try another query pattern
        return get_recent_pending_orders_simple(client, seven_days_ago)

def get_recent_pending_orders_simple(client, seven_days_ago: str) -> List[Dict[str, Any]]:
    """
    Simple GraphQL query as a fallback
    """
    query = gql("""
    query {
        allOrders {
            id
            orderNumber
            orderDate
            status
            customerEmail
            customer {
                email
            }
        }
    }
    """)
    
    try:
        result = client.execute(query)
        all_orders = result.get('allOrders', [])
        
        # Filter locally in Python
        filtered_orders = []
        for order in all_orders:
            try:
                order_date = datetime.strptime(order['orderDate'], '%Y-%m-%d')
                cutoff_date = datetime.strptime(seven_days_ago, '%Y-%m-%d')
                
                if order_date >= cutoff_date and order.get('status') in ['PENDING', 'pending']:
                    filtered_orders.append(order)
            except (ValueError, KeyError):
                continue
        
        return filtered_orders
    except Exception as e:
        raise Exception(f"Simple GraphQL query also failed: {str(e)}")

def log_order_reminders(logger, orders: List[Dict[str, Any]]):
    """Log order reminders to file"""
    if not orders:
        logger.info("No pending orders found from the last 7 days.")
        return
    
    logger.info(f"Found {len(orders)} pending orders from the last 7 days:")
    
    for order in orders:
        try:
            order_id = order.get('id', 'N/A')
            order_number = order.get('orderNumber', order_id)
            
            # Extract customer email from various possible locations
            customer_email = "Unknown"
            if order.get('customer'):
                if isinstance(order['customer'], dict):
                    customer_email = order['customer'].get('email', 'Unknown')
                elif isinstance(order['customer'], str):
                    customer_email = order['customer']
            elif order.get('customerEmail'):
                customer_email = order['customerEmail']
            
            order_date = order.get('orderDate', 'Unknown')
            status = order.get('status', 'Unknown')
            total_amount = order.get('totalAmount', 0)
            
            logger.info(
                f"Order #{order_number} - "
                f"Date: {order_date}, "
                f"Status: {status}, "
                f"Amount: ${total_amount}, "
                f"Customer: {customer_email}"
            )
            
            # Also log to a structured format for potential processing
            logger.debug(f"Order details: {json.dumps(order, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error processing order: {str(e)}")

def main():
    """Main execution function"""
    logger = setup_logging()
    
    logger.info("Starting order reminder processing...")
    
    try:
        # Create GraphQL client
        client = get_graphql_client()
        logger.info(f"Connected to GraphQL endpoint: {GRAPHQL_ENDPOINT}")
        
        # Get recent pending orders
        logger.info("Querying for pending orders from the last 7 days...")
        
        # Try multiple query approaches
        orders = []
        try:
            orders = get_recent_pending_orders(client)
        except Exception as e1:
            logger.warning(f"First query approach failed: {str(e1)}")
            try:
                orders = get_recent_pending_orders_alternative(client)
            except Exception as e2:
                logger.error(f"All GraphQL query approaches failed: {str(e2)}")
                orders = []
        
        # Log the reminders
        log_order_reminders(logger, orders)
        
        # Success message
        success_msg = "Order reminders processed!"
        logger.info(success_msg)
        
        # Print to console (as required)
        print(success_msg)
        
        return 0
        
    except Exception as e:
        error_msg = f"Critical error in order reminder script: {str(e)}"
        logger.error(error_msg)
        print(f"Error: {error_msg}")
        return 1

if __name__ == "__main__":
    # Exit with appropriate code
    sys.exit(main())
