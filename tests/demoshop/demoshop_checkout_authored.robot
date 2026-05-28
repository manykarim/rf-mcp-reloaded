*** Settings ***
Library    Browser

*** Test Cases ***
Flowline Supply — Add Two Items And Checkout
    New Browser    chromium    headless=True
    Set Browser Timeout    60s
    New Context
    New Page
    Go To    https://demoshop.makrocode.de/    wait_until=domcontentloaded

    # Add first item: Cascade Water Bottle (featured non-compact card)
    Click    article:not(.product-card--compact)[data-product-id="12"] button[data-test="add-to-cart-btn"]
    Get Text    [data-cart-count]    ==    1

    # Add second item: Echo Conference Speaker (unique in featured section)
    Click    [aria-label="Add Echo Conference Speaker to cart"]
    Get Text    [data-cart-count]    ==    2

    # Checkout
    Go To    https://demoshop.makrocode.de/checkout    wait_until=domcontentloaded
    Fill Text    \#checkout-email    test@example.com
    Fill Text    \#checkout-name    Test User
    Fill Text    \#checkout-address    123 Flow Street, San Francisco, CA
    Click    .checkout-form button[type="submit"]

    # Assert checkout success
    Get Element Count    .checkout-alert--success    ==    1
