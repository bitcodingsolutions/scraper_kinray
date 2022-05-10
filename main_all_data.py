from concurrent import futures
import requests
import csv
import os
from dotenv import load_dotenv
import json
import time

### Selenium

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


load_dotenv()


email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')
input_file_name = os.getenv('INPUT_FILE_NAME')
all_kinray_sku_list_file_name = os.getenv('ALL_KINRAY_SKU_LIST_FILE_NAME')

sender_address = os.getenv('SENDER_ADDRESS')
sender_pass = os.getenv('SENDER_PASS')
receiver_address = os.getenv('RECEIVER_ADDRESS')

result_file_name = all_kinray_sku_list_file_name + ".csv"

thread_pool = 100
all_data = []

driver = None
session = requests.session()
account_num = ""


is_header = True
def write_output(data):
    """
    This Funcation Write The Data In Csv File
    """
    global is_header

    header = ["SKU","category"]


    with open(result_file_name, mode='a', encoding="utf-8", newline='') as output_file:
        writer = csv.writer(output_file, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_ALL)
        # Header
        if is_header == True:
            is_header = False
            writer.writerow(header)

        for i in data:
            writer.writerow(i)


def chrome_driver():
    """
    initialize chrome driver with headless
    :return: driver
    """

    print("chrome_driver() -> initialization started")
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument(
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36')

    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}

    return uc.Chrome(options=chrome_options, desired_capabilities=caps)



def login_session():
    global account_num
    global driver

    try:
        response = session.get("https://api.cardinalhealth.com/pharmcon/kinray-exp/user/detail")
        json_data = response.json()
        account_num = json_data["accounts"][0]["accountNum"]
        print("account_num : ", account_num)
    except:
        driver = chrome_driver()

        driver.get("https://kinrayweblink.cardinalhealth.com/login")
        current_handle = driver.current_window_handle
        for handle in driver.window_handles:
            if handle != current_handle:
                driver.switch_to.window(handle)
                driver.close()

        driver.switch_to.window(current_handle)

        input_username = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.ID, "okta-signin-username"))
        )
        print("login() -> loginName found ")
        input_password = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.ID, "okta-signin-password"))
        )
        print("login() -> password found ")

        input_username.send_keys(email)
        input_password.send_keys(password, Keys.ENTER)

        while True:
            if driver.current_url == "https://kinrayweblink.cardinalhealth.com/home":
                break
            else:
                time.sleep(1)


        browser_log = driver.get_log('performance')
        access_token = ''
        x_api_key = ''
        for entry in browser_log:
            try:
                json_request = json.loads(entry["message"])
                access_token = json_request['message']['params']['headers']['access-token']
                x_api_key = json_request['message']['params']['headers']['x-api-key']
                if access_token and x_api_key:
                    break
            except:
                pass

        driver.quit()

        print("access_token : ",access_token)
        print("x_api_key : ",x_api_key)
        # access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJTYW5kYWRpckBhb2wuY29tIiwibG9naW4iOiJTYW5kYWRpckBhb2wuY29tIiwiZW1haWxJZCI6IlNhbmRhZGlyQGFvbC5jb20iLCJleHBpcmVkQXQiOjE2NTE5NDgzNDQzNDYsIm9rdGFJZCI6IjAwdWo3bWN0Y2tOcENtZWV4MXQ3IiwiZXhwIjoxNjUxOTQ4MzQ0MzQ2LCJidUlkIjozLCJ1c2VyVHlwZSI6ODAzLCJ1c2VyRGV0YWlsTnVtIjo0NjQ1OH0.C63nJ6LV1fwD1lv9ZDYSD6JSvrfZUIvKSyQ1zN7wiKg'
        # x_api_key = 'Ggcj9yiWoNY2AWzWAZUNqcJ0miMbGkey'

        session.headers.update({'Accept': 'application/json'})
        session.headers.update({'Content-Type': 'application/json'})
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36'})
        session.headers.update({'access-token': access_token})
        session.headers.update({'x-api-key': x_api_key})

    response = session.get("https://api.cardinalhealth.com/pharmcon/kinray-exp/user/detail")
    json_data = response.json()
    account_num = json_data["accounts"][0]["accountNum"]
    print("account_num : ",account_num)


def get_all_categories():
    global session

    url = "https://api.cardinalhealth.com/pharmcon/kinray-exp/kinray/search/v1/fine-dept"
    response = session.get(url)

    try:
        return response.json()
    except:
        return None


def get_data_from_category(args):
    global session
    global account_num

    category_obj = args[0]

    page_no = 0
    page_size = 100

    url = "https://api.cardinalhealth.com/pharmcon/kinray-exp/kinray/search/v1/products"

    list_sku = []
    while True:
        payload = json.dumps({
            "searchKeyword": "",
            "pageSize": page_size,
            "pageNo": page_no,
            "allDeals": False,
            "allNew": False,
            "allPharmacySupplies": False,
            "sortParam": None,
            "sortOrder": None,
            "showIneligibleItem": True,
            "accountNum": account_num,
            "searchResult": None,
            "cheapestFlag": None,
            "fine_department_code": category_obj["fineDeptCode"],
            "fine_department_desc": category_obj["fineDeptDesc"],
            "facets": {
                "finest_department_desc": [],
                "manufacturer": [],
                "strength": []
            },
            "searchFilters": {
                "deals": False,
                "pharmacySupplies": False,
                "specials": False,
                "instantRebates": False,
                "prebook": False,
                "leader": False,
                "newFilter": False
            },
            "rbcFlag": False
        })

        response = session.post(url, data=payload)
        json_data = response.json()

        # print("json_data : ", json_data)
        current_page = json_data["pageVo"]["current"]
        total_pages = json_data["pageVo"]["total_pages"]

        # print("current_page : ", current_page)
        # print("total_pages : ", total_pages)

        for item in json_data["itemList"]:
            list_sku.append([item["itemId"],category_obj["fineDeptDesc"]])
            # list_sku.extend(json_data["itemList"])

        if current_page >= total_pages-1:
            break
        page_no += 1

    print(category_obj["fineDeptDesc"]," : ", len(list_sku))

    write_output(data=list_sku)


def start():
    global all_data

    try:
        os.remove(result_file_name)
    except:
        pass

    login_session()

    categories = get_all_categories()
    print("categories : ", categories)

    with futures.ThreadPoolExecutor(thread_pool) as executor:
        for category in categories:
            executor.submit(get_data_from_category,[category])


if __name__ == '__main__':
    start()