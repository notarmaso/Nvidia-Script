from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import webbrowser
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
import winsound  # Added for sound alert

def play_alert_sound():
    # Play a 1000Hz sound for 2 seconds
    frequency = 800
    duration = 1000  # milliseconds
    winsound.Beep(frequency, duration)

def loading_is_inactive(driver):
    """
    Returns True if the loading bar is not active.
    """
    indicator_html = driver.execute_script(
        "return document.querySelector('css-loading-indicator')?.innerHTML?.trim()"
    )
    # The loading bar is considered inactive if indicator_html equals '\x3C!---->'
    return indicator_html == '\x3C!---->'

def open_product_link_single(url, search_text, initial_timeout=10, max_retries=500, ):
    attempt = 0
    while attempt < max_retries:
        timeout = initial_timeout
        
        service = Service('chromedriver-win64/chromedriver.exe')
        driver = webdriver.Chrome(service=service)
        driver.set_page_load_timeout(timeout)
        
        try:
            print(f"\nWindow {threading.current_thread().name} - Attempt {attempt + 1} of {max_retries}")
            print(f"Using timeout of {timeout} seconds")
            
            driver.get(url)
            
        
            wait = WebDriverWait(driver, 30)  # or some smaller period
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
                            play_alert_sound()  # Play sound when product is found
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
 
def run_concurrent_searches(url, search_text, num_windows=1, timeout=60):
    print(f"Starting {num_windows} concurrent search windows...")
    
    futures = []
    with ThreadPoolExecutor(max_workers=num_windows) as executor:
        for i in range(num_windows):
            # Stagger each new window by 10 seconds
            if i > 0:
                print(f"Waiting 10 seconds before starting window {i+1}...")
                time.sleep(10)
            
            # Submit the task to ThreadPoolExecutor
            futures.append(executor.submit(open_product_link_single, url, search_text, timeout))
        
        # Once all tasks are submitted, wait for them to complete
        results = [future.result() for future in futures]

    successful_searches = sum(1 for result in results if result)
    print(f"\nSearch completed. {successful_searches} out of {num_windows} windows found products.")
    return any(results)

if __name__ == "__main__":
    import threading  # Added import for thread naming
    
    url = "https://marketplace.nvidia.com/da-dk/consumer/graphics-cards/?locale=da-dk&page=1&limit=12&sorting=fp&manufacturer=GAINWARD&manufacturer_filter=NVIDIA~3,ASUS~12,GAINWARD~2,GIGABYTE~18,INNO3D~14,MSI~12,PALIT~6,PNY~5,ZOTAC~11"
    search_text = "4060"
    success = run_concurrent_searches(url, search_text, 1)
    
    if not success:
        print("Failed to find and open product link in all windows.")