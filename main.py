import datetime
import glob
import json
import logging
import os
import time
import requests
import yfinance as yf
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logging.getLogger("seleniumwire").setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SYMBOLS_DIR = os.path.join(SCRIPT_DIR, 'symbols')
DIST_DIR = os.path.join(SCRIPT_DIR, 'dist')

def get_latest_user_agent(operating_system='windows', browser='chrome'):
    url = f'https://jnrbsn.github.io/user-agents/user-agents.json'
    r = requests.get(url)
    r.raise_for_status()
    user_agents = r.json()
    
    for user_agent in user_agents:
        if operating_system.lower() in user_agent.lower() and browser.lower() in user_agent.lower():
            return user_agent
    return None

def get_issa_etf_price(symbol, type='etf', max_attempts=3):
    """
    Retrieves price from Maya TASE website with enhanced validation.
    """
    for attempt in range(max_attempts):
        logging.info(f"Attempt {attempt + 1} for symbol {symbol}")
        driver = None
        
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            
            driver = webdriver.Chrome(options=options)
            
            if type == 'etf':
                url = f"https://maya.tase.co.il/foreignetf/{symbol}"
            else:
                url = f"https://maya.tase.co.il/fund/{symbol}"
                
            logging.info(f"Accessing URL: {url}")
            driver.get(url)
            
            # Wait for the page to load
            wait = WebDriverWait(driver, 20)
            
            # Wait for specific elements that indicate the page is fully loaded
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "securities-details")))
            
            # Let's log the full page source for debugging
            logging.debug(f"Page source before price extraction: {driver.page_source}")
            
            # Try to get price from multiple sources
            price = None
            
            # Method 1: Try getting from the main price display
            try:
                price_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".securityHeaderPrice"))
                )
                price_text = price_element.text.strip()
                logging.info(f"Found price text (method 1): {price_text}")
                if price_text:
                    cleaned_price = price_text.replace('₪', '').replace(',', '').strip()
                    price = float(cleaned_price)
            except Exception as e:
                logging.error(f"Method 1 failed: {str(e)}")
            
            # Method 2: Try getting from the trade data
            if not price:
                try:
                    price_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".lastPrice"))
                    )
                    price_text = price_element.text.strip()
                    logging.info(f"Found price text (method 2): {price_text}")
                    if price_text:
                        cleaned_price = price_text.replace('₪', '').replace(',', '').strip()
                        price = float(cleaned_price)
                except Exception as e:
                    logging.error(f"Method 2 failed: {str(e)}")
            
            # Validate the price
            if price is not None:
                if price <= 0 or price > 1000000:  # Adjust these bounds as needed
                    raise Exception(f"Price {price} seems invalid")
                
                logging.info(f"Successfully extracted price: {price}")
                
                # Save screenshot for verification
                screenshot_path = f"price_screenshot_{symbol}.png"
                driver.save_screenshot(screenshot_path)
                logging.info(f"Verification screenshot saved to {screenshot_path}")
                
                price_date = datetime.datetime.now().strftime('%Y-%m-%d')
                driver.quit()
                return price, price_date
            else:
                raise Exception("Could not extract price using any method")
            
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if driver:
                try:
                    screenshot_path = f"error_screenshot_{symbol}_{attempt}.png"
                    driver.save_screenshot(screenshot_path)
                    logging.info(f"Error screenshot saved to {screenshot_path}")
                    logging.debug(f"Page source on error: {driver.page_source}")
                except:
                    pass
                driver.quit()
            
            if attempt == max_attempts - 1:
                raise Exception(f"Failed to get price after {max_attempts} attempts")
            
            time.sleep((attempt + 1) * 5)
            continue

def main():
    logging.info(f"Reading symbols *.json files in {SYMBOLS_DIR} ...")
    for symbol_track_file_path in glob.glob(os.path.join(SYMBOLS_DIR, '*.json'), recursive=True):
        logging.info(f"Processing {symbol_track_file_path} ...")

        try:
            with open(symbol_track_file_path) as f:
                symbol_track_info = json.load(f)

            symbol_price = 0
            symbol_price_date = ''

            symbol_id = symbol_track_info['id']
            symbol = symbol_track_info['symbol']
            currency = symbol_track_info['currency']
            user_agent_header = get_latest_user_agent(operating_system='windows', browser='chrome')

            if symbol_track_info['source'] == 'justetf':
                url = f'https://www.justetf.com/api/etfs/{symbol}/quote?locale=en&currency={currency}&isin={symbol}'
                r = requests.get(url, headers={'User-Agent': user_agent_header, 'Accept': 'application/json'})
                r.raise_for_status()
                symbol_info = r.json()
                symbol_price = symbol_info['latestQuote']['raw']
                symbol_price_date = symbol_info['latestQuoteDate']

            elif symbol_track_info['source'] == 'yahoo_finance':
                ticker_yahoo = yf.Ticker(symbol)
                symbol_info = ticker_yahoo.history()
                symbol_price = symbol_info['Close'].iloc[-1]
                symbol_price_date = symbol_info['Close'].index[-1]
                symbol_price_date = datetime.datetime.strftime(symbol_price_date, '%Y-%m-%d')

            elif symbol_track_info['source'] == 'issa':
                symbol_price, symbol_price_date = get_issa_etf_price(
                    symbol, 
                    type=symbol_track_info.get('type', 'etf')
                )

            if not symbol_price:
                raise Exception(f'Failed to get price for {symbol}')

            # Create the distribution directory and save files
            symbol_dist_dir = os.path.join(DIST_DIR, symbol_id)
            os.makedirs(symbol_dist_dir, exist_ok=True)
            
            symbol_track_info['price'] = symbol_price
            symbol_track_info['price_date'] = symbol_price_date

            # Save individual files
            with open(os.path.join(symbol_dist_dir, 'price'), 'w+') as f:
                f.write(str(symbol_price))

            with open(os.path.join(symbol_dist_dir, 'currency'), 'w+') as f:
                f.write(currency)

            with open(os.path.join(symbol_dist_dir, 'date'), 'w+') as f:
                f.write(symbol_price_date)

            with open(os.path.join(symbol_dist_dir, 'info.json'), 'w+') as f:
                json.dump(symbol_track_info, f, indent=2)

            logging.info(f'Symbol "{symbol_id}" update completed. Price: {symbol_price} {currency} Date: {symbol_price_date}')

        except Exception as e:
            logging.exception(f'Failed to process {symbol_track_file_path}')
            raise

if __name__ == '__main__':
    main()
