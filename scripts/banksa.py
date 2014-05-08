#!/usr/bin/python2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import unittest, time, re
import requests
from getpass import getpass

CSV_URL = 'https://ibanking.banksa.com.au/ibank/exportTransactions.action?&newPage=1&index=2&exportFileFormat=CSV&exportDateFormat=dd/MM/yyyy&action=exporttransactionHistory&httpMethod=GET'
# 'Cookie: CompassCookie=43BB667F1CE3CB7F324FBBC8E396CF4E'
CSV_COOKIE = "CompassCookie"
#  "Express Saver",
ACCOUNTS = ["Complete Freedom", "Incentive Saver", "Maxi Saver"]

pin = ''
password = ''

class Banksa(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.base_url = "https://ibanking.banksa.com.au"
        self.verificationErrors = []
        self.accept_next_alert = True

        # Set pref so file ends up where we want it
#        fp = webdriver.FirefoxProfile()
#        fp.set_preference("browser.dowload.folderList", 2)
#        fp.set_preference("browser.download.manager.showWhenStarting",False)
#        fp.set_preference("browser.download.dir", os.getcwd())
#        fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

    def test_banksa(self):
        driver = self.driver
        driver.get(self.base_url + "/ibank/loginPage.action")
        driver.find_element_by_id("access-number").clear()
        driver.find_element_by_id("access-number").send_keys("01062173")
        driver.find_element_by_id("securityNumber").clear()
        driver.find_element_by_id("securityNumber").send_keys(pin)
        driver.find_element_by_id("internet-password").clear()
        driver.find_element_by_id("internet-password").send_keys(password)
        driver.find_element_by_id("logonButton").click()


        for account in ACCOUNTS:
            driver.find_element_by_css_selector("div.ico-home").click()
            self.driver.implicitly_wait(10)
            driver.find_element_by_link_text(account).click()
            driver.find_element_by_link_text("All").click()
            self.driver.implicitly_wait(10)

            # get the file
            cookie = driver.get_cookie(CSV_COOKIE)
            r = requests.get(CSV_URL, cookies={CSV_COOKIE: cookie['value']})
            r.raise_for_status()

            # If you download more than once a second, you're a nincompoop
            filename = "%s_%s.csv" % \
                    (account.replace(" ", "_"), time.strftime("%Y%m%d_%H%M%S"))
            with open(filename, "w") as fh:
                fh.write(r.content)

        driver.find_element_by_css_selector("a.btn.btn-logout > span").click()

    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException, e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException, e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    pin = getpass("Pin: ")
    password = getpass()
    unittest.main()
