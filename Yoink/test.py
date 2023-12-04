import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class WebAppTest(unittest.TestCase):
    def setUp(self):
        # Set up the WebDriver (you may need to adjust the path based on your system)
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)  # Set implicit wait time to handle dynamic elements
        self.driver.get('http://127.0.0.1:5000')  # Update with the actual URL of your web application

    def tearDown(self):
        # Close the browser window after each test
        self.driver.quit()

    def test_user_creates_new_post(self):
        # Navigate to the login page from the home page
        self.go_to_login_page()

        # Log in (replace 'username' and 'password' with actual credentials)
        self.log_in('admin@mail.com', '123')

        # After successful login, navigate back to the home page
        self.go_to_home_page()

        # Type 'Hello World' in the create new Yoink input field
        self.type_new_yoink('Hello World')

        # Press the post yoink button
        self.post_yoink()

        # Wait for the post to be visible on the page
        time.sleep(2)  # Adjust the wait time based on your application's loading time

        # Check if the post is visible on the page
        post_text = 'Hello World'
        self.assertTrue(self.is_post_visible(post_text))

    def go_to_login_page(self):
        # Navigate to the login page from the home page
        login_link = self.driver.find_element(By.XPATH, '//a[@href="/login"]')  # Update with your actual login link locator
        login_link.click()

    def go_to_home_page(self):
        # Navigate back to the home page
        home_link = self.driver.find_element(By.XPATH, '//a[@href="/"]')  # Update with your actual home link locator
        home_link.click()

    def log_in(self, username, password):
        # Implement the login logic based on your web application's structure
        # Example (replace with your actual login page elements):
        email_input = self.driver.find_element(By.NAME, 'email')
        password_input = self.driver.find_element(By.NAME, 'password')
        login_button = self.driver.find_element(By.CLASS_NAME, 'sign-up-button')  # Update with your actual login button locator

        email_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

    def type_new_yoink(self, yoink_text):
        # Find the create new Yoink input field and type the given text
        yoink_input = self.driver.find_element(By.NAME, 'content')
        yoink_input.send_keys(yoink_text)

    def post_yoink(self):
        # Find and click the post yoink button
        post_button = self.driver.find_element(By.NAME, 'submit')
        post_button.click()

    def is_post_visible(self, post_text):
        # Check if the post with the given text is visible on the page
        yoink_list = self.driver.find_element(By.CLASS_NAME, 'yoink-list')
        posts = yoink_list.find_elements(By.CLASS_NAME, 'yoink-item')

        for post in posts:
            if post_text in post.text:
                return True

        return False

if __name__ == '__main__':
    unittest.main()
