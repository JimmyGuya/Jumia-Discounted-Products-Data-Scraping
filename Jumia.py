from bs4 import BeautifulSoup
import requests
import pandas as pd
import pymysql
import os
from dotenv import load_dotenv

# Base URL for Jumia product listings
url = "https://www.jumia.co.ke/?page="

# Initialize a variable to track the current page number
current_page = 1

# Initialize a list to store all discounted products
discounted_products = []

# Number of pages to scrape
max_pages = 25

# Loop through pages
while current_page <= max_pages:
    # Construct the URL for the current page by appending the page number
    page_url = url + str(current_page)

    # Make the HTTP request to the current page URL
    r = requests.get(page_url)

    # Check if the request was successful
    if r.status_code != 200:
        print(f"Failed to retrieve page {current_page}")
        break

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find all product containers (adjust the selector based on the actual HTML structure)
    products = soup.find_all("article", {"class": "prd"})

    # Check if no products are found, meaning we've likely reached the last page
    if not products:
        print("No more products found, stopping pagination.")
        break

    # Iterate over the products to extract the relevant information
    for product in products:
        # Extract product name
        product_name = product.find("div", class_="name").text.strip()

        # Extract current price (price after discount)
        current_price = product.find("div", class_="prc").text.strip()

        # Extract old price (price before discount) from the 'data-oprc' attribute
        old_price = product.find("div", class_="prc").get("data-oprc", "No old price").strip()

        # Extract discount if available
        product_discount = product.find("div", class_="bdg _dsct")

        # If the product has a discount, include it in the data
        if product_discount:
            discount_text = product_discount.text.strip()
            discounted_products.append({
                "Product Name": product_name,
                "Price Before Discount": old_price,
                "Current Price After Discount": current_price,
                "Discount": discount_text
            })

    # Print progress
    print(f"Scraped page {current_page}")

    # Move to the next page
    current_page += 1

# Create a DataFrame from the collected discounted products
df = pd.DataFrame(discounted_products)

# Print the total number of discounted products found
print(f"Total discounted products found: {len(df)}")

# Show the first few rows of the DataFrame
print(df.head())

# Save to CSV
df.to_csv("discounts.csv", index=False)


# Load environment variables from .env file
load_dotenv()

# MySQL connection using environment variables with pymysql
connection = pymysql.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)

try:
    # Create a cursor object
    with connection.cursor() as cursor:
        # Create the table if it doesn't exist (adjust columns as necessary)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS discounted_products (
            `Product Name` VARCHAR(255),
            `Price Before Discount` VARCHAR(255),
            `Current Price After Discount` VARCHAR(255),
            `Discount` VARCHAR(255)
        )
        """
        cursor.execute(create_table_query)

        # Read the CSV file
        dfs = pd.read_csv('discounts.csv')

        # Insert data into the table
        for _, row in dfs.iterrows():
            insert_query = """
            INSERT INTO discounted_products (`Product Name`, `Price Before Discount`, `Current Price After Discount`, `Discount`)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (row['Product Name'], row['Price Before Discount'], row['Current Price After Discount'], row['Discount']))

        # Commit the transaction
        connection.commit()

        # Print a successful message
        print(f'The table discounted products has been updated successfully!')

finally:
    # Close the connection
    connection.close()