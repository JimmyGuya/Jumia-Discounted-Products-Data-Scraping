from bs4 import BeautifulSoup
import requests
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime



# define the default arguments
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024,9,1),
    "retries": 1
}

# define the dag
dag = DAG(
    "jumia_scrape_dag",
    default_args=default_args,
    description='scraping discounted products on jumia and storing them in mysql database.',
    schedule= '@daily'
)

# scrape discounted products from jumia website
def scrape_jumia_products():
    # Base URL for Jumia product listings 
    url = "https://www.jumia.co.ke/?page="

    # Initialize a variable to track the current page number
    current_page = 1

    # Initialize a list to store all discounted products
    discounted_products = []

    # Number of pages to scrape 
    max_pages = 2

    # Loop through pages
    while current_page <= max_pages:
        # Construct the URL for the current page by appending the page number
        page_url = url + str(current_page)
    
        # Make the HTTP request to the current page URL
        r = requests.get(page_url)
    
        # Check if the request was successful
        if r.status_code != 200:
            break
    
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
    
        # Find all product containers (adjust the selector based on the actual HTML structure)
        products = soup.find_all("article", {"class": "prd"})
    
        # Check if no products are found, meaning we've likely reached the last page
        if not products:
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

    df.to_csv("discounts.csv", index=False)

def load_to_mysql():
    # Load environment variables from .env file
    load_dotenv()

    # MySQL connection using environment variables
    # SQLAlchemy connection string
    conn_string = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"

    # create the engine connection
    db = create_engine(conn_string)
    conn = db.connect()

    # Trace the filepath
    file_path = 'C:/Users/VINCE/Desktop/Data Engineering Projects/Data Scraping/discounts.csv'
    dfs = pd.read_csv('discounts.csv') # Read the csv file

    # Load the dataframe to mysql
    table_name = "discountedproducts"
    dfs.to_sql(table_name, con=conn, if_exists='replace', index=False)

    # we close the connection
    conn.close()

    # print a successful message
    print(f'The table {table_name} has been uploaded successfully!')

# define the python tasks
scrape_task = PythonOperator(
    task_id='scrape_jumia_products',
    python_callable=scrape_jumia_products,
    dag=dag
)

upload_task = PythonOperator(
    task_id='load_to_mysql',
    python_callable=load_to_mysql,
    dag=dag
)

# set task dependencies
scrape_task >> upload_task