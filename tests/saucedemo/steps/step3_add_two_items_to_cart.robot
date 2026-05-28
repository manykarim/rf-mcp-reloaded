*** Settings ***
Library    Browser
Suite Setup     Open And Login
Suite Teardown    Close Browser

*** Keywords ***
Open And Login
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \#user-name    standard_user
    Fill Text    \#password    secret_sauce
    Click    \#login-button

*** Test Cases ***
Step 3 - Add Two Items To Cart
    Open And Login
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Get Text    .shopping_cart_badge    ==    1
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]
    Get Text    .shopping_cart_badge    ==    2
    Take Screenshot    step3_items_added.png
