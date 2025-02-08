import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException

def check_internet(url='http://www.google.com', timeout=5, interval=10, max_retries=10):
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print("Internet is connected.")
                return
        except requests.ConnectionError:
            print(f"Connection failed. Retrying in {interval} seconds... ({retries + 1}/{max_retries})")
        retries += 1
        time.sleep(interval)
    raise Exception("Internet connection could not be established after multiple attempts.")

def initialize_driver(download_directory):
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": os.path.abspath(download_directory),
            "download.prompt_for_download": False,
            "directory_upgrade": True,
        })
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except WebDriverException as e:
        print("Error initializing WebDriver:", e)
        raise

def download_file(url, file_path):
    try:
        if not url:
            print("No URL provided for downloading.")
            return

        counter = 1
        base_path, ext = os.path.splitext(file_path)
        while os.path.exists(file_path):
            file_path = f"{base_path}_{counter}{ext}"
            counter += 1

        response = requests.get(url)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"File downloaded successfully: {file_path}")
        else:
            print(f"Failed to download file, status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")

def save_to_json_incremental(data, filename):
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    existing_data.append(data)
                    data = existing_data
                else:
                    print("Existing JSON is not a list. Overwriting it.")
                    data = [data]
        else:
            print(f"{filename} does not exist. A new file will be created.")
            data = [data]
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {filename}: {e}")
        data = [data]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data appended to {filename}")

def scrape_case_data(driver, download_directory, json_filename):
    try:
        rows = driver.find_elements(By.XPATH, '//*[@id="tblExport"]/tbody/tr')
        print(f"Found {len(rows)} rows to process.")

        for i in range(1, len(rows) + 1):
            try:
                case_link = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="tblExport"]/tbody/tr[{i}]/td[3]'))
                )
                driver.execute_script("arguments[0].scrollIntoView();", case_link)
                print(f"Processing row {i}: {case_link.text}")
                case_link.click()


                # Extract case details
                print("********************************")
                case_title = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[3]').text
                case_no = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[2]').text
                author_judge = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[4]').text
                judgment_date = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[5]').text
                sc_citation = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[6]').text
                court_type = "Sindh High Court"

                download_link_element = driver.find_element(By.XPATH, '//*[@id="appjudgment"]/table/tbody/tr[1]/td[8]/a')
                download_url = download_link_element.get_attribute("href")
                filename = os.path.basename(download_url)
                file_path = os.path.join(download_directory, filename)

                download_file(download_url, file_path)
                print(download_url)
                print("***************************************")

                case_details = {
                    "caseNo": case_no,
                    "caseTitle": case_title,
                    "authorJudge": author_judge,
                    "judgmentDate": judgment_date,
                    "caseCitation": sc_citation,
                    "courtType": court_type,
                    "URL": download_url,
                    "caseFile": os.path.basename(file_path),
                }

                save_to_json_incremental(case_details, json_filename)

                driver.back()
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="tblExport"]'))
                )

            except TimeoutException:
                print(f"Timeout while processing row {i}. Skipping...")
            except NoSuchElementException as e:
                print(f"Element not found in row {i}: {e}. Skipping...")
            except Exception as e:
                print(f"Error processing row {i}: {e}")

    except Exception as e:
        print(f"Error during scraping: {e}")

def main():
    check_internet()
    download_directory = "SindhHighCourt"
    os.makedirs(download_directory, exist_ok=True)
    driver = initialize_driver(download_directory)
    try:
        driver.get('https://caselaw.shc.gov.pk/caselaw/public/rpt-afr')
        time.sleep(10)
        scrape_case_data(driver, download_directory, "SindhHighCourt.json")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
