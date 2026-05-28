*** Settings ***
Library    Browser

*** Test Cases ***
Saucedemo Locked Out Login
    New Browser    chromium    headless=True
    Set Browser Timeout    60s
    New Context
    New Page
    Go To    https://www.saucedemo.com    wait_until=domcontentloaded
    Fill Text    id=user-name    locked_out_user
    Fill Text    id=password    secret_sauce
    Click    id=login-button
    Get Text    [data-test="error"]    *=    locked out
    Get Url    ==    https://www.saucedemo.com/
    Close Browser
