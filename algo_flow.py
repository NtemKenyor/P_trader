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
import random
import string


#do not change this section
# Load environment variables
load_dotenv()
# Binance API keys
API_KEY = os.getenv('BINANCE_KEY_I_MADE')
EMAILER_KEY = os.getenv('MAILER_KEY')
SENDER_SCRIPT_ID = os.getenv('SCRIPT_ID_RUN')
PRIVATE_KEY_PATH = 'test-prv-key.pem'


with open(PRIVATE_KEY_PATH, 'rb') as f:
    private_key = load_pem_private_key(data=f.read(), password=None)

from decimal import Decimal, ROUND_DOWN

TRADES_API_URL = 'https://roynek.com/P_trader/'  # Replace with your actual server URL
# TRADES_API_URL = 'http://localhost/alltrenders/P_trader/'

TRADES_API_URL_IN = TRADES_API_URL+'trades_insert.php'
TRADES_API_URL_DIS = TRADES_API_URL+'trades_display.php'
TRADES_API_URL_MAIL = TRADES_API_URL+'report_tool.php'

def get_top_tokens(pair="USDT"):
    # Get the 24-hour ticker data for all symbols
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    response = requests.get(url)
    tickers = response.json()

    # Filter out only the trading pairs with volume and base pair
                                                                      
    # Filter out only the trading pairs with volume and base pair
    trading_pairs = [ticker for ticker in tickers if float(ticker['volume']) > 0 and ticker['symbol'].endswith(pair)]

    # Sort the trading pairs based on the percentage change in the last 24 hours
    sorted_pairs = sorted(trading_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)

    # Select the top 3 trading pairs for further analysis
    top_pairs = sorted_pairs[:3]

    # Check the 30-minute performance of the top pairs
    for pair in top_pairs:
        symbol = pair['symbol']
        url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=30m&limit=1'
        response = requests.get(url)
        klines = response.json()

        # Extract the close price of the last 30-minute candle
        if len(klines) > 0:
            close_price = float(klines[0][4])
            pair['close_price'] = close_price

    # Sort the top pairs based on the 30-minute performance
    sorted_top_pairs = sorted(top_pairs, key=lambda x: float(x['close_price']) / float(x['lastPrice']), reverse=True)

    # Return the best-performing token data
    if len(sorted_top_pairs) > 0:
        best_token_data = sorted_top_pairs[0]
        return best_token_data
    else:
        return None


def get_lot_size_filters(symbol):
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    exchange_info = response.json()

    # Extract the lot size filters for the specified symbol
    for symbol_info in exchange_info['symbols']:
        if symbol_info['symbol'] == symbol:
            filters = symbol_info['filters']
            return filters
    return None


def following_filter(symbol, price, initial_investment):
    filters = get_lot_size_filters(symbol)
    if not filters:
        print(f"Filters not found for symbol {symbol}")
        return False

    # Check if the initial investment is within the allowed limits
    min_notional_filter = next((filter for filter in filters if filter['filterType'] == 'NOTIONAL'), None)
    if min_notional_filter:
        min_notional = float(min_notional_filter['minNotional'])
        if initial_investment < min_notional:
            print(f"Initial investment too small. Minimum notional: {min_notional}")
            return False

    # Calculate quantity based on the price and lot size filters
    lot_size_filter = next((filter for filter in filters if filter['filterType'] == 'LOT_SIZE'), None)
    if lot_size_filter:
        min_qty = float(lot_size_filter['minQty'])
        max_qty = float(lot_size_filter['maxQty'])
        step_size = float(lot_size_filter['stepSize'])
        quantity = round(initial_investment / price, int(-math.log10(step_size)))
        quantity = max(min_qty, min(quantity, max_qty))
        return quantity

    return False

def buy(symbol, price, quantity):
    load_dotenv()

    API_KEY = os.getenv('BINANCE_KEY_I_MADE')
    PRIVATE_KEY_PATH = 'test-prv-key.pem'

    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key = load_pem_private_key(data=f.read(), password=None)

    # Fetch current market price
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
    response = requests.get(url)
    market_price = float(response.json()['price'])

    # Adjust price if it deviates too much from market price
    if abs(price - market_price) > market_price * 0.05:  # Adjust as needed
        print("Price too far from market price, adjusting...")
        price = market_price

    # Prepare order parameters
    params = {
        'symbol': symbol,
        'side': 'BUY',
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'price': price,
        'quantity': quantity,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    url = 'https://api.binance.com/api/v3/order'
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    # Place the order
    response = requests.post(url, headers=headers, params=params)

    if response.status_code == 200:
        # Calculate fees
        fills = response.json()['fills']
        fees = sum(float(fill['commission']) for fill in fills)
        print("Buy order successful")
        print(f"Fees: {fees}")
        return True, fees, price #understand that the price may have changed becos we made a new price check
    else:
        print("Buy order failed")
        print(response.json())
        return False, 0.0, price



def get_decimal_precision(symbol):
    url = f'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    exchange_info = response.json()

    symbol_info = next((sym for sym in exchange_info['symbols'] if sym['symbol'] == symbol), None)
    if symbol_info:
        filters = symbol_info['filters']
        price_filter = next((f for f in filters if f['filterType'] == 'PRICE_FILTER'), None)
        if price_filter:
            tick_size = float(price_filter['tickSize'])
        else:
            tick_size = 1e-8  # Default tick size if not found
    else:
        tick_size = 1e-8  # Default tick size if symbol not found

    return tick_size


def sell_token(symbol, current_price=None, sell_price=None, quantity=None):
    if current_price is None:
        # Get the current price from the exchange
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
        response = requests.get(url)
        current_price = float(response.json()['price'])

    if quantity is None:
        # If quantity is not specified, sell 100% of the holding
        quantity = get_holding_quantity(symbol)

    if sell_price is None:
        # Sell at the current market price
        price = current_price
    else:
        price = sell_price

    params = {
        'symbol': symbol,
        'type': 'LIMIT',
        'side': 'SELL',
        'timeInForce': 'GTC',  # Good Till Cancel
        'quantity': quantity,
        'price': price,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    url = f'https://api.binance.com/api/v3/order?{payload}&signature={signature.decode()}'
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }
    response = requests.post(url, headers=headers)

    return response.json()

csv_file_path = 'transactions.csv'
# Function to update the CSV file
def update_csv(symbol, initial_price, final_price, quantity, status, addon, profit, fees):
    df = pd.read_csv(csv_file_path)
    new_row = pd.DataFrame([[symbol, initial_price, final_price, quantity, status, addon, profit, fees]], columns=df.columns)
    df = pd.concat([new_row, df], ignore_index=True)
    df.to_csv(csv_file_path, index=False)


# update_csv("BTCUSDT", 7, 9, 0.23, 'Bought', 7, 5, 0.45)

def get_current_price(symbol):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
    response = requests.get(url)
    data = response.json()
    if 'price' in data:
        return float(data['price'])
    else:
        print(f"Failed to get current price for {symbol}")
        return None


def place_oco_sell_order(symbol, quantity, price, stop_price):

    params = {
        'symbol': symbol,
        'side': 'SELL',
        'quantity': quantity,
        'price': price,
        'stopPrice': stop_price,
        'stopLimitPrice': stop_price,  # This is the same as stopPrice for a simple OCO order
        'stopLimitTimeInForce': 'GTC',  # Good Till Cancel
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    url = 'https://api.binance.com/api/v3/order/oco'
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    response = requests.post(url, headers=headers, params=params)

    if response.status_code == 200:
        order_id = response.json()['orderId']
        print("OCO sell order placed successfully")
        return True, order_id
    else:
        print("Failed to place OCO sell order")
        return False, None


def cancel_order(symbol, order_id):

    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    url = 'https://api.binance.com/api/v3/order'
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    response = requests.delete(url, headers=headers, params=params)

    if response.status_code == 200:
        print("Order canceled successfully")
        return True
    else:
        print("Failed to cancel order")
        return False


def check_profit(symbol, initial_price, current_price):
    # Calculate profit percentage
    profit_percentage = ((current_price - initial_price) / initial_price) * 100

    if profit_percentage > 0:
        print(f"You are making a profit of {profit_percentage:.2f}% on {symbol}")
    elif profit_percentage < 0:
        print(f"You are in a loss of {-profit_percentage:.2f}% on {symbol}")
    else:
        print("You are breaking even")

    return profit_percentage

def cancel_all_orders(symbol):
    url = 'https://api.binance.com/api/v3/openOrders'
    params = {
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    response = requests.delete(url, headers=headers, params=params)

    if response.status_code == 200:
        print(f"All open orders for {symbol} have been canceled")
        return True
    else:
        print("Failed to cancel orders")
        return False


def get_holding_quantity(symbol):

    params = {
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    params['signature'] = signature

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

def get_holding_quantity(symbol):

    params = {
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
    }

    payload = '&'.join([f'{param}={value}' for param, value in params.items()])
    signature = base64.b64encode(private_key.sign(payload.encode('ASCII')))
    
    headers = {
        'X-MBX-APIKEY': API_KEY,
        'signature': signature.decode(),
    }

    url = 'https://api.binance.com/api/v3/account'
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        for balance in data['balances']:
            if balance['asset'] == symbol:
                return float(balance['free'])
        return 0  # Token not found in balance
    else:
        print("Failed to fetch balance")
        return None

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


# Calculate the stop price based on the loss threshold
def calculate_stop_price(initial_price, loss_percentage):
    stop_price = initial_price * (1 - loss_percentage)
    return stop_price

def truncate_to_step_size(value, step_size, max_value):
    value = Decimal(str(value))  # Convert to Decimal
    step_size = Decimal(str(step_size))  # Convert to Decimal
    max_value = Decimal(str(max_value))  # Convert to Decimal
    truncated_value = int(value / step_size) * step_size
    return min(truncated_value, max_value)

# Calculate the stop price based on the loss threshold
def calculate_stop_price(initial_price, loss_percentage):
    stop_price = initial_price * (1 - loss_percentage)
    return stop_price


def sell_filter(symbol, quantity, stop_price, stop_limit_price, current_price):
    filters = get_lot_size_filters(symbol)
    if not filters:
        print(f"Filters not found for symbol {symbol}")
        return False

    # Check if the quantity is within the allowed limits
    lot_size_filter = next((filter for filter in filters if filter['filterType'] == 'LOT_SIZE'), None)
    if lot_size_filter:
        min_qty = Decimal(lot_size_filter['minQty'])
        max_qty = Decimal(lot_size_filter['maxQty'])
        step_size = Decimal(lot_size_filter['stepSize'])
        quantity = Decimal(quantity)
        quantity = max(min_qty, min(quantity, max_qty))
        quantity = quantity.quantize(step_size, rounding=ROUND_DOWN)  # Round down to the nearest step size
        quantity = float(quantity)

        truncated_quantity = truncate_to_step_size(quantity, step_size, max_qty)
        print(truncated_quantity)


        # Adjust stopPrice and stopLimitPrice
        price_filter = next((filter for filter in filters if filter['filterType'] == 'PRICE_FILTER'), None)
        if price_filter:
            min_price = float(price_filter['minPrice'])
            max_price = float(price_filter['maxPrice'])
            tick_size = float(price_filter['tickSize'])
            stop_price = round(stop_price, int(-math.log10(tick_size)))
            stop_limit_price = round(stop_limit_price, int(-math.log10(tick_size)))
            stop_price = max(min_price, min(stop_price, max_price))
            stop_limit_price = max(min_price, min(stop_limit_price, max_price))

        # Adjust price based on current price
        price_change = current_price * 1  # Assuming 100% from current price
        adjusted_price = current_price + price_change
        adjusted_price = round(adjusted_price, int(-math.log10(tick_size)))  # Round to tick size
        adjusted_price = max(min_price, min(adjusted_price, max_price))  # Ensure price is within limits

        return truncated_quantity, quantity, adjusted_price, stop_price, stop_limit_price


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
            #print(response.text)
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


def send_data_to_php(email_key, data):
    url = TRADES_API_URL_MAIL  # Replace with the actual URL of your PHP script
    
    payload = {
        'email_key': email_key,
        'data': data
    }
    
    try:
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            return response.json()  # Return the parsed JSON response
        else:
            return {"status": False, "message": f"HTTP Error: {response.status_code}", "data": ""}
    
    except requests.exceptions.RequestException as e:
        return {"status": False, "message": f"Request Exception: {str(e)}", "data": ""}



def seller_side(sold_price, holding_quantity):
    selling_price = pair_price if (pair_price > (sold_price + THRESH_POINT)) else sold_price + THRESH_POINT
    t_quantity, f_quantity, ad_price, filtered_sp, filtered_slp = sell_filter(symbol, holding_quantity, selling_price, selling_price, pair_price)
    if f_quantity:
        # Place your OCO sell order using filtered_quantity
        print(f"Original quantity: {holding_quantity} Filtered quantity for sell order: {f_quantity} :: Truncate sell order: {t_quantity}")                                
        print(f"prices: price: {pair_price}, sp: {ad_price}, f_sp: {filtered_sp}, f_slp: {filtered_slp} ")
        # state, order_id = place_oco_sell_order(symbol, quantity=t_quantity, price=ad_price, stop_price=filtered_sp)

        
        data_from_sell = sell_token(symbol, pair_price, selling_price, t_quantity )
        return data_from_sell
    else:
        data += "Could not set the SELL FILTER... * \n "
        return None


def investment_manny():
    quantity = following_filter(symbol, pair_price, investment)
    if quantity:
        bought_status, fees, market_price = buy(symbol, pair_price, quantity)
        if bought_status:
            token_symbol = symbol.replace("USDT", "")
            time.sleep(10)

            holding_quantity = get_holding_quantity(token_symbol)
            quantity_x = holding_quantity if holding_quantity > 0 else quantity
            # amount = market_price * holding_quantity
            amount = market_price * quantity_x
            total_cost = amount + fees


            #place a sell order
            sold_price_ = total_cost + THRESH_POINT
            data_from_sell = seller_side(sold_price_, quantity_x)
            print(data_from_sell)

            #Add to db
            data_ = {
                'pair': pair,
                'price': market_price,
                # 'quantity': holding_quantity,
                'quantity': quantity_x, # it is possible that the order is placed but the item is not yet bought so it is proper for us to use the 'quantity' itself instead of 'holding_quantity'
                'amount': amount,
                'status': '1',
                'conditioned': '0',
                'addon': str(data_from_sell),
                'comment': f'Overall USDT at buy time: {usdt_quantity} and Amount+Fees: {total_cost}',
                # 'hashed_key': "".join(random.choices( list(string.digits), k=7 )),
                'hashed_key': SENDER_SCRIPT_ID,
                'order_placed': 'BUY',
                'profit': '0'
            }

            insert_transaction(data_)
            # print(get_all_transactions())

    else:
        print("could not get quantity for that amount")


#you can change this section...
THRESH_POINT = 1
stable_token = 'USDT'
pair = "SOLUSDT"
symbol = pair
tradable_mark = 140 # we would only participate in trades when the mark is lower than this
data = "Debug tooler: "
investment = 2000
tradable_usdt_mark = 2016 - investment
data_log = "Debug tooler: "

# Step 1: Get the current price of the trading pair
pair_price = get_current_price(pair)

if pair_price is not None:
    # if pair_price < tradable_mark:  # Buy condition
    transactions = get_all_transactions()
    
    if transactions:
        usdt_quantity = get_holding_quantity(stable_token)
        if usdt_quantity is not None:
            print(f"Current USDT balance: {usdt_quantity}")

            last_transaction = find_last_transaction(transactions, pair)
            data_log += f"Last transaction: {last_transaction} * \n"
            
            # Step 2: Determine if the last transaction was a 'buy'
            if "buy" in last_transaction["order_placed"].lower():
                print("Last transaction was a buy. Checking if we can sell.")
                token_symbol = pair.replace("USDT", "")
                holding_quantity = get_holding_quantity(token_symbol)
                bought_quantity = float(last_transaction["quantity"])
                bought_price = float(last_transaction["price"])
                amount_spent = float(last_transaction["amount"])
                target_price = bought_price + THRESH_POINT if (bought_price + THRESH_POINT) > pair_price else pair_price

                if holding_quantity >= bought_quantity:
                    print(f"Holding enough SOL to sell: {holding_quantity} SOL")
                    data_log += f"Attempting to sell at {target_price} * \n"

                    # Attempt to sell
                    sells_data = seller_side(target_price, holding_quantity)
                    print(sells_data)

                elif holding_quantity < bought_quantity:
                    print("Appears we already sold some tokens. Checking USDT balance.")
                    if usdt_quantity > amount_spent:
                        # Record the completed sell
                        info_ = (f"Previously held **{last_transaction['comment']}**, "
                                    f"bought {bought_quantity} of {pair}, now sold and hold {usdt_quantity} USDT.")
                        transaction_data = {
                            'pair': pair,
                            'price': bought_price + THRESH_POINT,
                            'quantity': holding_quantity,
                            'amount': bought_price * bought_quantity,
                            'status': '0',
                            'addon': info_,
                            'comment': 'Sold successfully. Quantity refers to current holdings.',
                            'hashed_key': SENDER_SCRIPT_ID,
                            'order_placed': 'SELL',
                            'profit': (bought_price + THRESH_POINT) - bought_price
                        }

                        insert_transaction(transaction_data)
                        send_data_to_php(EMAILER_KEY, str(data_log))
                    else:
                        print("Waiting for better market conditions.")
                        data_log += "Market conditions not favorable yet. * \n"

                        try:
                            # Attempt to sell
                            print("let's just try selling at the threshpoint. if no sell order exist")
                            sells_data = seller_side(target_price, holding_quantity)
                            print(sells_data)
                        except:
                            print("exception of the sell in this category...")
                else:
                    print("Order mismatch or sell order might be open. Waiting...")
                    data_log += "Order quantity mismatch. Sell order may already be open. * \n"
            else:
                # Step 3: Execute buy order if no recent buy is detected
                # tradable_usdt_mark = usdt_quantity - investment
                if pair_price < tradable_mark:  
                    #can buy now
                    print("No recent buy detected. Ready to place a buy order.")
                    data_log += "Ready to place a buy order. * \n"
                    investment_manny()
                else:
                    print(f"Current price {pair_price} exceeds tradable mark {tradable_mark}. Not buying.")
                    data_log += f"Price above tradable mark: {pair_price}. * \n"
                
        else:
            data_log += "Error retrieving USDT quantity or insufficient balance. * \n"
    else:
        data_log += "No transaction data available. * \n"
else:
    print("Error fetching the current price. Unable to proceed.")
    data_log += "Could not fetch the current price. * \n"

print(data_log)
