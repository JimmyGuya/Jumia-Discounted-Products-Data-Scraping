
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import pymysql

# Load environment variables outside the functions to avoid reloading every time
load_dotenv()

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 9, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# Define the DAG
dag = DAG(
    'jumia_scrape_dag',
    default_args=default_args,
    description='Scraping discounted products on Jumia and storing them in MySQL',
    schedule_interval='@daily',
    catchup=False
)

# Scrape discounted products from Jumia website
def scrape_jumia_products(**context):
    url = "https://www.jumia.co.ke/?page="
    current_page = 1
    max_pages = 25  # Define the number of pages to scrape
    discounted_products = []

    while current_page <= max_pages:
        page_url = url + str(current_page)
        logging.info(f'Scraping page: {current_page}')
        try:
            r = requests.get(page_url)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching page {current_page}: {e}")
            break

        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all("article", {"class": "prd"})

        if not products:
            logging.info("No products found on page, stopping scraping.")
            break

        for product in products:
            try:
                product_name = product.find("div", class_="name").text.strip()
                current_price = product.find("div", class_="prc").text.strip()
                old_price = product.find("div", class_="prc").get("data-oprc", "No old price").strip()
                product_discount = product.find("div", class_="bdg _dsct")

                if product_discount:
                    discount_text = product_discount.text.strip()
                    discounted_products.append({
                        "Product Name": product_name,
                        "Price Before Discount": old_price,
                        "Current Price After Discount": current_price,
                        "Discount": discount_text
                    })
            except Exception as e:
                logging.error(f"Error processing product: {e}")

        logging.info(f"Scraped page {current_page} successfully")
        current_page += 1

    df = pd.DataFrame(discounted_products)
    logging.info(f"Total discounted products found: {len(df)}")
    df.to_csv("discounts.csv", index=False)
    return len(df)

# Load scraped data to MySQL
def load_to_mysql(**context):
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
            # Create the table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS discountedproducts (
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
                INSERT INTO discountedproducts (`Product Name`, `Price Before Discount`, `Current Price After Discount`, `Discount`)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    row['Product Name'], 
                    row['Price Before Discount'], 
                    row['Current Price After Discount'], 
                    row['Discount']
                ))

            # Commit the transaction after inserting all rows
            connection.commit()

            logging.info(f"The table discountedproducts has been updated successfully with {len(dfs)} records!")

    except Exception as e:
        logging.error(f"Failed to insert data into MySQL: {e}")
        raise

    finally:
        # Close the connection
        connection.close()

# Define the Python tasks
scrape_task = PythonOperator(
    task_id='scrape_jumia_products',
    python_callable=scrape_jumia_products,
    provide_context=True,
    dag=dag
)

upload_task = PythonOperator(
    task_id='load_to_mysql',
    python_callable=load_to_mysql,
    provide_context=True,
    dag=dag
)

# Set task dependencies
scrape_task >> upload_task
