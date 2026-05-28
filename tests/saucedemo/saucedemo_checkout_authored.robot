*** Settings ***
Library    Browser

*** Test Cases ***
Saucedemo Checkout
    New Browser    chromium    headless=True
    Set Browser Timeout    60s
    New Context
    New Page
    Go To    https://www.saucedemo.com    wait_until=domcontentloaded
    Get Title    ==    Swag Labs
    Fill Text    id=user-name    standard_user
    Fill Text    id=password    secret_sauce
    Click    id=login-button
    Get Url    *=    inventory.html
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]
    Get Text    .shopping_cart_badge    ==    2
    Click    .shopping_cart_link
    Get Url    *=    cart.html
    Get Element Count    .cart_item    ==    2
    Click    [data-test="checkout"]
    Fill Text    [data-test="firstName"]    Many
    Fill Text    [data-test="lastName"]    Tester
    Fill Text    [data-test="postalCode"]    12345
    Click    [data-test="continue"]
    Get Url    *=    checkout-step-two.html
    Click    [data-test="finish"]
    Get Url    *=    checkout-complete.html
    Get Text    .complete-header    ==    Thank you for your order!
    Close Browser
