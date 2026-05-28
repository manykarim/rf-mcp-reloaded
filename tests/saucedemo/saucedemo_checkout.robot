*** Settings ***
Documentation     End-to-end checkout test for https://www.saucedemo.com
...               Tests login, adding two items to cart, and completing checkout.
...               Uses Browser Library (Playwright) for automation.
Library           Browser
Suite Teardown    Close Browser

*** Variables ***
${BASE_URL}           https://www.saucedemo.com
${USERNAME}           standard_user
${PASSWORD}           secret_sauce
${FIRST_NAME}         Test
${LAST_NAME}          User
${ZIP_CODE}           12345
${SUCCESS_HEADER}     Thank you for your order!

*** Test Cases ***
Complete Checkout Flow - Login Add Items Checkout Verify Success
    [Documentation]    Full e2e: login → add 2 items → checkout → verify success
    [Tags]             e2e    checkout    saucedemo

    # --- Step 1: Open browser and navigate to SauceDemo ---
    New Browser         chromium    headless=False
    New Context
    New Page            ${BASE_URL}
    Get Title           ==    Swag Labs

    # --- Step 2: Login with valid credentials ---
    Fill Text           \#user-name    ${USERNAME}
    Fill Text           \#password     ${PASSWORD}
    Click               \#login-button
    Get Url             contains    inventory

    # --- Step 3: Add first item (Sauce Labs Backpack) to cart ---
    Click               [data-test="add-to-cart-sauce-labs-backpack"]
    Get Text            .shopping_cart_badge    ==    1

    # --- Step 4: Add second item (Sauce Labs Bike Light) to cart ---
    Click               [data-test="add-to-cart-sauce-labs-bike-light"]
    Get Text            .shopping_cart_badge    ==    2

    # --- Step 5: Navigate to cart ---
    Click               .shopping_cart_link
    Get Url             contains    cart

    # --- Step 6: Verify cart has 2 items ---
    Get Element Count   .cart_item    ==    2

    # --- Step 7: Proceed to checkout ---
    Click               [data-test="checkout"]
    Get Url             contains    checkout-step-one

    # --- Step 8: Fill in checkout information ---
    Fill Text           [data-test="firstName"]    ${FIRST_NAME}
    Fill Text           [data-test="lastName"]     ${LAST_NAME}
    Fill Text           [data-test="postalCode"]   ${ZIP_CODE}
    Click               [data-test="continue"]
    Get Url             contains    checkout-step-two

    # --- Step 9: Verify order summary and finish ---
    Get Element Count   .cart_item    ==    2
    Click               [data-test="finish"]
    Get Url             contains    checkout-complete

    # --- Step 10: Verify success message ---
    Get Text            .complete-header    ==    ${SUCCESS_HEADER}
    Take Screenshot     checkout_complete.png
