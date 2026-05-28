*** Settings ***
Library    Browser
Suite Teardown    Close Browser

*** Test Cases ***
Step 1 - Setup Open Browser And Navigate
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Get Title    ==    Swag Labs
