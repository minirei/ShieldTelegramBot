import requests
import time
from bs4 import BeautifulSoup
from pprint import pprint

# 'TEST': [URL, key_id_name, key_id_temperature]
id_dict = {
    'HQ': ['', '', '],
    'VES': ['', '', ''],
    'Section 1': ['', '', ''],
    'Section 2': ['', '', ''],
    'Section 3': ['', '', ''],
    'Section 4': ['', '', ''],
    'TEST': ['https://docs.google.com/forms/d/e/1FAIpQLSfhYcN-tZc4U4PQ2lxJYqhKl9WKq_WvMW2a8bihrDbIvl4VLA/formResponse', 'entry.651194876', 'entry.547671152']
}


def get_name_options(url):
    html_content = requests.get(url).text #read

    soup = BeautifulSoup(html_content, "lxml") #parse

    dropdown = soup.find("div", attrs={"class": "quantumWizMenuPaperselectOptionList"}) #get everything in the dropdown box
    dropdown_data = dropdown.find_all("div", attrs={"role": "option"}) #get the options (comes with one placeholder option; index 0)

    options = []
    i = 1
    while(i < len(dropdown_data)):
        foo = []
        foo.append(dropdown_data[i].span.text) #each option string is stored as a "span" under each div class (thankfully i don't need to format the string)
        i += 1
        try:
            foo.append(dropdown_data[i].span.text)
            i += 1
        except Exception:
            pass
        options.append(foo)

    return options

def send_temperature(url, data_dict):
    try:
        requests.post(url, data=data_dict)
        print("Form submitted")
        time.sleep(2)
    except:
        print("Error Occured")