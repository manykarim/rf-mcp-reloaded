*** Settings ***
Library    Browser
Suite Setup     Open Login Add Items And Go To Cart
Suite Teardown    Close Browser

*** Keywords ***
Open Login Add Items And Go To Cart
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \#user-name    standard_user
    Fill Text    \#password    secret_sauce
    Click    \#login-button
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]
    Click    .shopping_cart_link

*** Test Cases ***
Step 5 - Checkout Flow And Verify Success
    Open Login Add Items And Go To Cart
    Click    [data-test="checkout"]
    Get Url    contains    checkout-step-one
    Fill Text    [data-test="firstName"]    Test
    Fill Text    [data-test="lastName"]     User
    Fill Text    [data-test="postalCode"]   12345
    Click    [data-test="continue"]
    Get Url    contains    checkout-step-two
    Get Element Count    .cart_item    ==    2
    Click    [data-test="finish"]
    Get Url    contains    checkout-complete
    Get Text    .complete-header    ==    Thank you for your order!
    Take Screenshot    step5_checkout_complete.png
