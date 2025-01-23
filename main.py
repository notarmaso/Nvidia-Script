from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import webbrowser
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
import winsound
import threading

def play_alert_sound(alarm_length):
    frequency = 800
    duration = alarm_length  # milliseconds
    winsound.Beep(frequency, duration)

def loading_is_inactive(driver):
    """
    Returns True if the loading bar is not active.
    """
    indicator_html = driver.execute_script(
        "return document.querySelector('css-loading-indicator')?.innerHTML?.trim()"
    )
    return indicator_html == '\x3C!---->'

def create_optimized_driver(timeout):
    chrome_options = Options()
    
    # Performance optimizations
    chrome_options.add_experimental_option(
        "prefs", {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.images": 2,
            "profile.default_content_settings.javascript": 1,  # Keep JavaScript enabled for your case
            "profile.managed_default_content_settings.cookies": 1,
            "profile.default_content_settings.plugins": 2,
        }
    )
    
    # Additional performance options
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    
    # Set page load strategy
    chrome_options.page_load_strategy = 'eager'
    
    # Create service and driver
    service = Service('chromedriver-win64/chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(timeout)
    
    return driver

def open_product_link_single(url, search_text, initial_timeout, alarm_length, max_retries=99999):
    attempt = 0
    while attempt < max_retries:
        timeout = initial_timeout
        driver = create_optimized_driver(timeout)
        
        try:
            print(f"\nWindow {threading.current_thread().name} - Attempt {attempt + 1} of {max_retries}")
            print(f"Using timeout of {timeout} seconds")
            
            driver.get(url)
            
            wait = WebDriverWait(driver, 30)
            wait.until(loading_is_inactive)
            print("Loading bar is no longer active.")
            
            product_titles = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h2.nv-productTitle'))
            )

            product_found = False
            data_found = False
            
            for title_elem in product_titles:
                title_text = title_elem.get_attribute('title')
                
                if search_text in title_text:
                    pid_code = title_elem.get_attribute('data-pid-code')
                    
                    if not pid_code:
                        print(f"Product ID not found for title: {title_text}")
                        continue
                    
                    try:
                        hidden_div = driver.find_element(By.ID, pid_code)
                        product_data = json.loads(hidden_div.get_attribute('textContent').strip())
                        data_found = True
                        
                        direct_purchase_link = product_data[0].get('directPurchaseLink')
                        if direct_purchase_link:
                            print(f"Success in window {threading.current_thread().name}! Opening link: {direct_purchase_link}")
                            webbrowser.open(direct_purchase_link)
                            play_alert_sound(alarm_length)
                            driver.quit()
                            return True
                        else:
                            print(f"Window {threading.current_thread().name} - Product found but no direct purchase link available.")
                            product_found = True
                            
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON for product ID {pid_code}: {e}")
            
            if data_found and not product_found:
                print(f"Window {threading.current_thread().name} - Product data found but no matching products. Retrying...")
            else:
                print(f"Window {threading.current_thread().name} - No product data found. Retrying...")
                
            attempt += 1
            
            if attempt < max_retries:
                delay = 1
                print(f"Window {threading.current_thread().name} - Waiting {delay} seconds before next attempt...")
                time.sleep(delay)
                
        except TimeoutException:
            print(f"Window {threading.current_thread().name} - Page load timed out. Retrying...")
            attempt += 1
            
        except WebDriverException as e:
            print(f"Window {threading.current_thread().name} - Browser error: {e}")
            attempt += 1
            
        except Exception as e:
            print(f"Window {threading.current_thread().name} - Unexpected error: {e}")
            attempt += 1
            
        finally:
            driver.quit()
            
    print(f"\nWindow {threading.current_thread().name} - Max retries ({max_retries}) reached. Script terminated.")
    return False

def run_concurrent_searches(url, search_text, num_windows=1, timeout=60, delay=10, alarm_length=5000):
    print(f"Starting {num_windows} concurrent search windows...")
    
    futures = []
    with ThreadPoolExecutor(max_workers=num_windows) as executor:
        for i in range(num_windows):
            if i > 0:
                print(f"Waiting 10 seconds before starting window {i+1}...")
                time.sleep(delay)
            
            futures.append(executor.submit(open_product_link_single, url, search_text, timeout, alarm_length))
        
        results = [future.result() for future in futures]

    successful_searches = sum(1 for result in results if result)
    print(f"\nSearch completed. {successful_searches} out of {num_windows} product found.")
    return any(results)

def get_url_input():
    while True:
        print("\nURL Selection:")
        print("1. Use default NVIDIA marketplace URL (Recommended for 50XX series Founder Edition)")
        print("2. Enter custom marketplace URL")
        choice = input("Enter your choice (1 or 2): ")
        
        if choice == "1":
            return "https://marketplace.nvidia.com/da-dk/consumer/graphics-cards/?locale=da-dk&page=1&limit=12&sorting=fp&manufacturer=NVIDIA&manufacturer_filter=NVIDIA~3,ASUS~12,GAINWARD~1,GIGABYTE~20,INNO3D~13,MSI~11,PALIT~7,PNY~4,ZOTAC~10"
        elif choice == "2":
            return input("Enter your custom URL: ").strip()
        else:
            print("Invalid choice. Please enter 1 or 2.")

def get_integer_input(prompt, min_value=1):
    while True:
        try:
            value = int(input(prompt))
            if value >= min_value:
                return value
            print(f"Please enter a number greater than or equal to {min_value}")
        except ValueError:
            print("Please enter a valid number")

def main():
    # Get URL
    url = get_url_input()
    
    search_text = input("\nEnter the search text (e.g., 5080): ").strip()
    
    windows = get_integer_input("\nEnter the number of windows to run (recommended: 6): ")
    
    timeout = get_integer_input("\nEnter the timeout value in seconds (recommended: 60): ")
    
    delay = get_integer_input("\nEnter the delay between each window in seconds (recommended: 10): ")
    
    alarm_length = get_integer_input("\nEnter the lengths of the alarm in ms (recommended: 5000): ")

    success = run_concurrent_searches(url, search_text, windows, timeout, delay, alarm_length)
    
    if not success:
        print("Failed to find and open product link in all windows.")

if __name__ == "__main__":
    main()