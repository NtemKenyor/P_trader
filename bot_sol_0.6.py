# API_KEY = os.getenv('BINANCE_KEY_I_MADE')
# SECRET_KEY = os.getenv('BINANCE_SECRET_KEY_I_MADE')

import requests
import base64
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from dotenv import load_dotenv
import math
import hmac
import hashlib
import time
import os
import pandas as pd

# Load environment variables
load_dotenv()
# Binance API keys
API_KEY = os.getenv('BINANCE_KEY_I_MADE')
PRIVATE_KEY_PATH = 'test-prv-key.pem'


with open(PRIVATE_KEY_PATH, 'rb') as f:
    private_key = load_pem_private_key(data=f.read(), password=None)

TRADES_API_URL = 'http://roynek.com/P_trader/'  # Replace with your actual server URL
TRADES_API_URL = 'http://localhost/alltrenders/P_trader/'

TRADES_API_URL_IN = TRADES_API_URL+'trades_insert.php'
TRADES_API_URL_DIS = TRADES_API_URL+'trades_display.php'

def get_all_transactions():
    """Retrieve all transactions from the database."""
    response = requests.get(TRADES_API_URL_DIS)
    if response.status_code == 200:
        return response.json().get('row', [])
    else:
        print("Error fetching transactions:", response.status_code)
        return []


def insert_transaction(data):
    """Insert a new transaction into the database using a POST request."""
    url = TRADES_API_URL_IN

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        if response.status_code == 200:
            print("Transaction successfully inserted.")
            print(response.text)
            return response.json()
        else:
            print("Failed to insert transaction:", response.status_code)
            return None
    except requests.exceptions.RequestException as e:
        print("Error inserting transaction:", e)
        return None


def find_last_transaction(transactions, pair):
    """Find the last transaction for the given trading pair."""
    for transaction in reversed(transactions):
        if transaction['pair'] == pair:
            return transaction
    return None

# def get_account_balance(symbol="USDT"):
#     """Retrieve the account balance for a specific symbol from Binance."""
#     url = 'https://api.binance.com/api/v3/account'
#     headers = {
#         'X-MBX-APIKEY': API_KEY,
#     }
#     params = {
#         'timestamp': int(time.time() * 1000),
#         'recvWindow': 5000,
#     }
#     query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
#     signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
#     params['signature'] = signature

#     response = requests.get(url, headers=headers, params=params)
#     if response.status_code == 200:
#         balances = response.json().get('balances', [])
#         for balance in balances:
#             if balance['asset'] == symbol:
#                 return float(balance['free'])
#         return 0.0
#     else:
#         print("Error fetching account balance:", response.status_code)
#         return 0.0

# def check_last_transaction(pair):
#     """Check the last transaction for the given pair and print results."""
#     transactions = get_all_transactions()
#     last_transaction = find_last_transaction(transactions, pair)

#     if last_transaction:
#         if last_transaction['order_placed'].upper() == 'BUY':
#             print("Bought")
#         elif last_transaction['order_placed'].upper() == 'SELL':
#             usdt_balance = get_account_balance("USDT")
#             print(f"Sold - Total USDT left in account: {usdt_balance}")
#         else:
#             print(f"Last transaction was: {last_transaction['order_placed']}")
#     else:
#         print(f"No transactions found for pair: {pair}")

def get_holding_quantity(symbol):
    # Set up the request parameters
    params = {
        'timestamp': int(time.time() * 1000),  # UNIX timestamp in milliseconds
    }

    # Sign the request
    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    # Send the request
    url = f'https://api.binance.com/api/v3/account?{payload}&signature={signature.decode()}'
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for balance in data['balances']:
            if balance['asset'] == symbol:
                return float(balance['free'])
        return 0  # Token not found in balance
    else:
        print("Failed to fetch balance")
        return None

# Example usage
# symbol = 'USDT'
# usdt_quantity = get_holding_quantity(symbol)
# if usdt_quantity is not None:
#     print(f"Quantity of {symbol}: {usdt_quantity}")

# Data to be sent in the POST request
    
print(get_all_transactions())
data = {
    'pair': 'SOLUSDT',
    'price': '150.60',
    'quantity': '1.3',
    'amount': '48.60',
    'status': '1',
    'conditioned': '0',
    'addon': 'additional_info',
    'comment': 'This is a test',
    'hashed_key': '84798394893',
    'order_placed': 'BUY',
    'profit': '0'
}
insert_transaction(data)


print(get_all_transactions())
'''
if __name__ == "__main__":
    pair = "SOLUSDT"  # Replace with your trading pair
    usdt_quantity = get_holding_quantity(pair)
    if usdt_quantity is not None:
        print(f"Quantity of {symbol}: {usdt_quantity}")
    # check_last_transaction(pair)

    # # Call the function to insert the transaction
    # insert_transaction()'''
    
