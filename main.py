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

logging.getLogger("seleniumwire").setLevel(logging.DEBUG)
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
    Retrieves price from Maya TASE website with enhanced anti-detection measures.
    Args:
        symbol (str): The symbol to look up
        type (str): Either 'etf' or 'fund'
        max_attempts (int): Number of retry attempts
    """
    if type not in ['etf', 'fund']:
        raise ValueError(f"Invalid type '{type}'. Must be either 'etf' or 'fund'")
        
    for attempt in range(max_attempts):
        logging.info(f"Attempt {attempt + 1} for symbol {symbol} (type: {type})")
        driver = None
        
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument(f"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            
            driver = webdriver.Chrome(options=options)
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'})
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Construct URL based on type
            if type == 'etf':
                url = f"https://maya.tase.co.il/etf/{symbol}"  # Changed from foreignetf to etf
            else:
                url = f"https://maya.tase.co.il/fund/{symbol}"
                
            logging.info(f"Accessing URL: {url}")
            
            driver.set_page_load_timeout(30)
            driver.get(url)
            
            # Wait for page load
            driver.execute_script("return document.readyState") == "complete"
            time.sleep(2)  # Add small delay to ensure dynamic content loads
            
            wait = WebDriverWait(driver, 20)
            
            # Updated selectors for both ETFs and funds
            selectors = [
                ".lastGateValue",
                ".buyPriceValue",
                "[data-test='currPrice']",
                ".security-price",
                ".price-value",
                ".fundDetailsLastPrice",  # Added fund-specific selector
                ".etfDetailsLastPrice",   # Added ETF-specific selector
                "//span[contains(@class, 'price')]",
                "//div[contains(@class, 'lastGateValue')]",
                "//div[contains(text(), '₪')]",
                "//span[contains(@class, 'fundPrice')]",  # Added fund-specific xpath
                "//span[contains(@class, 'etfPrice')]"    # Added ETF-specific xpath
            ]
            
            price_element = None
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        price_element = wait.until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                    else:
                        price_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    if price_element:
                        break
                except:
                    continue
            
            if not price_element:
                raise Exception(f"Could not find price element with any selector for {type} {symbol}")
            
            # Get the raw text and log it
            raw_text = price_element.text.strip()
            logging.info(f"Raw price text: {raw_text}")
            
            if not raw_text:
                raise ValueError(f"Price element was found but contains no text for {type} {symbol}")
            
            # Check if we're dealing with agorot
            is_agorot = 'אג' in raw_text
            
            # Enhanced text cleaning
            price_text = raw_text
            
            # Remove everything except digits, dots, and commas
            price_text = ''.join(c for c in price_text if c.isdigit() or c in '.,')
            logging.debug(f"After initial cleaning: {price_text}")
            
            if not price_text:
                # Try to extract just numbers if initial cleaning failed
                price_text = ''.join(c for c in raw_text if c.isdigit())
                logging.debug(f"After number-only extraction: {price_text}")
                
                if not price_text:
                    raise ValueError(f"Could not extract numeric value from '{raw_text}'")
            

            # Remove all dots first
            price_text = price_text.replace('.', '')
                
            # Remove all commas
            price_text = price_text.replace(',', '')

            # Split by the last period (decimal point) if it exists
            parts = price_text.rsplit('.', 1)
            
            # Remove all commas and periods from the first part
            parts[0] = parts[0].replace(',', '').replace('.', '')
            
            # Join back with decimal point if it existed
            price_text = '.'.join(parts) if len(parts) > 1 else parts[0]
            
            logging.debug(f"Final cleaned price text: {price_text}")
            
            try:
                logging.debug(f"Attempting to convert to float: {price_text}")
                if is_agorot:
                    price = float(price_text) / 100
                else:
                    price = float(price_text)
                    
                logging.info(f"Successfully parsed price: {price}")
                
                if price <= 0:
                    raise ValueError(f"Invalid price value: {price}")
                    
            except ValueError as e:
                logging.error(f"Failed to parse price text: '{price_text}' (raw text: '{raw_text}')")
                screenshot_path = f"price_parse_error_{symbol}_{attempt}.png"
                driver.save_screenshot(screenshot_path)
                logging.info(f"Price parse error screenshot saved to {screenshot_path}")
                raise
            
            price_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            driver.quit()
            return price, price_date
            
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if driver:
                try:
                    screenshot_path = f"error_screenshot_{symbol}_{attempt}.png"
                    driver.save_screenshot(screenshot_path)
                    logging.info(f"Screenshot saved to {screenshot_path}")
                    page_source = driver.page_source
                    with open(f"page_source_{symbol}_{attempt}.html", 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logging.info(f"Page source saved to page_source_{symbol}_{attempt}.html")
                except:
                    pass
                driver.quit()
            
            if attempt == max_attempts - 1:
                raise Exception(f"Failed to get price after {max_attempts} attempts: {str(e)}")
            
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
