*** Settings ***
Library    Browser
Suite Setup     Open Login And Add Items
Suite Teardown    Close Browser

*** Keywords ***
Open Login And Add Items
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \#user-name    standard_user
    Fill Text    \#password    secret_sauce
    Click    \#login-button
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]

*** Test Cases ***
Step 4 - Navigate To Cart And Verify Items
    Open Login And Add Items
    Click    .shopping_cart_link
    Get Url    contains    cart
    Get Element Count    .cart_item    ==    2
    Take Screenshot    step4_cart.png
