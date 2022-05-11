from concurrent import futures
import requests
import pandas as pd
import csv
import os
from dotenv import load_dotenv
import json
import datetime
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
output_file_name = os.getenv('OUTPUT_FILE_NAME')

sender_address = os.getenv('SENDER_ADDRESS')
sender_pass = os.getenv('SENDER_PASS')
receiver_address = os.getenv('RECEIVER_ADDRESS')

result_file_name = output_file_name + "_" + str(datetime.datetime.now().timestamp()).split(".")[0] + ".csv"


thread_pool = 100
max_retry = 10


driver = None
session = requests.session()
account_num = ""

is_header = True
def write_output(data):
    """
    This Funcation Write The Data In Csv File
    """
    global is_header

    header = ["Qty","Size","Item#","Description","MFG","WAC/Source","NDC/UPC","Retail Price","Invoice","Est. Net","Deal Details","AWP"]

    with open(result_file_name, mode='a', encoding="utf-8", newline='') as output_file:
        writer = csv.writer(output_file, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_ALL)
        # Header
        if is_header == True:
            is_header = False
            writer.writerow(header)

        for i in data:
            writer.writerow(i)



#### MAIL

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

def send_mail(send_from, send_to, subject, text, sending_file, server ='smtp.gmail.com', port=587, isTls=True):
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime = True)
    msg['Subject'] = subject
    msg.attach(MIMEText(text))

    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(f"{sending_file}", "rb").read())
    encoders.encode_base64(part)
    sending_file = sending_file.split('/')[-1]
    part.add_header('Content-Disposition', f'attachment; filename="{sending_file}"')
    msg.attach(part)

    smtp = smtplib.SMTP(server, port)
    if isTls:
        smtp.starttls()
    smtp.login(sender_address,sender_pass)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.quit()


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
        response = session.get("https://api.cardinalhealth.com/pharmcon/kinray-exp/user/detail", timeout=10)
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
        # access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJTYW5kYWRpckBhb2wuY29tIiwibG9naW4iOiJTYW5kYWRpckBhb2wuY29tIiwiZW1haWxJZCI6IlNhbmRhZGlyQGFvbC5jb20iLCJleHBpcmVkQXQiOjE2NTIyMjcyNDYyNTQsIm9rdGFJZCI6IjAwdWo3bWN0Y2tOcENtZWV4MXQ3IiwiZXhwIjoxNjUyMjI3MjQ2MjU0LCJidUlkIjozLCJ1c2VyVHlwZSI6ODAzLCJ1c2VyRGV0YWlsTnVtIjo0NjQ1OH0.VcN7PlnjRQb0pH2bNzQXdMCEh6wl2eLo1ZFaOMw5oXU'
        # x_api_key = 'Ggcj9yiWoNY2AWzWAZUNqcJ0miMbGkey'

        session.headers.update({'Accept': 'application/json'})
        session.headers.update({'Content-Type': 'application/json'})
        session.headers.update({'Pragma': 'no-cache'})
        session.headers.update({'Origin': 'https://kinrayweblink.cardinalhealth.com'})
        session.headers.update({'Referer': 'https://kinrayweblink.cardinalhealth.com/'})
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36'})
        session.headers.update({'access-token': access_token})
        session.headers.update({'x-api-key': x_api_key})

    response = session.get("https://api.cardinalhealth.com/pharmcon/kinray-exp/user/detail", timeout=10)
    json_data = response.json()
    account_num = json_data["accounts"][0]["accountNum"]
    print("account_num : ",account_num)


index = 1
def get_data_from_sku(args):
    global session
    global account_num
    global index

    search_sku = args[0]

    list_sku = []

    url = "https://api.cardinalhealth.com/pharmcon/kinray-exp/kinray/search/v1/products"

    payload = json.dumps({
        "searchKeyword": search_sku,
        "pageSize": 10,
        "pageNo": 0,
        "allDeals": False,
        "allNew": False,
        "allPharmacySupplies": False,
        "sortParam": None,
        "sortOrder": None,
        "showIneligibleItem": True,
        "accountNum": account_num,
        "searchResult": None,
        "cheapestFlag": None,
        "fine_department_code": None,
        "fine_department_desc": "ALL",
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

    retry = 0

    while True:
        try:
            response = session.post(url, data=payload, timeout=20)
            json_data = response.json()

            if "itemList" in json_data:
                item = json_data["itemList"][0]

                print(index," -- item : ",item.get("itemId",""))
                index += 1
                list_sku.append([item.get("packQuantity",""),item.get("size",""),item.get("itemId",""),item.get("description",""),item.get("manufacturer",""),item.get("acquisitionPrice",""),
                                 f"'{item.get('upc','')}'",item.get("retailPrice",""),item.get("invoicePrice",""),item.get("estimatedNetPrice",""),"",item.get("medispanAWP","")])
                break
            else:

                print(index, " --- ",retry," -- Exception    ------ : ",search_sku, " ----- ", json_data )
                try:
                    error_code = json_data["faultInfos"][0]["faultCode"]
                except:
                    error_code = ""

                if retry < max_retry and error_code != "PRD123":
                    time.sleep(1)
                    retry += 1
                else:
                    index += 1
                    list_sku.append(["","",search_sku,"","","","","","","","",""])
                    break

        except Exception as e:
            print(index, " --- ",retry," -- Exception ------- : ",search_sku, " ------- ", e)
            if retry < max_retry:
                time.sleep(1)
                retry += 1
            else:
                print(index," -- item : ",search_sku)
                index += 1
                list_sku.append(["","",search_sku,"","","","","","","","",""])
                break

    write_output(data=list_sku)




def start():
    global is_header

    while True:
        is_header = True
        login_session()

        df = pd.read_csv(input_file_name)

        print("len : ", len(df['SKU']))
        i = 1
        with futures.ThreadPoolExecutor(thread_pool) as executor:
            for id in df['SKU']:
                executor.submit(get_data_from_sku, [id])
                i += 1
                # break

        send_mail(sender_address, receiver_address, 'Data Scrapped for the SKUs ', 'The scrapped data is in the attached Excel file.', result_file_name)

        print("Waiting for 3 Hours to start Scrapping again")
        time.sleep(10800)

if __name__ == '__main__':
    start()