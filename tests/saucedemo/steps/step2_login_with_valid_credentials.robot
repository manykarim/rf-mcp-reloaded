*** Settings ***
Library    Browser
Suite Setup     Open Browser Session
Suite Teardown    Close Browser

*** Keywords ***
Open Browser Session
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \#user-name    standard_user
    Fill Text    \#password    secret_sauce
    Click    \#login-button

*** Test Cases ***
Step 2 - Login With Valid Credentials
    Open Browser Session
    Get Url    contains    inventory
    Take Screenshot    step2_login.png
