
from flask import Flask, render_template, request
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# MySQL connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
    return conn

# Function to extract the numerical part of the discount and return it as an integer
def extract_discount(discount_str):
    match = re.search(r'(\d+)', discount_str)
    return int(match.group(1)) if match else 0

@app.route('/')
def index():
    # Get current page number, search query, and items per page from query parameters
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    items_per_page = 5  # Number of products per page

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query with search filter, ensuring no duplicates by `Product Name`
    base_query = f"""
        SELECT DISTINCT `Product Name`, `Price Before Discount`, `Current Price After Discount`, `Discount`
        FROM discounted_products
        WHERE `Product Name` LIKE %s
    """

    # Get the total number of products with the search filter applied (for pagination)
    cursor.execute(f"""
        SELECT COUNT(DISTINCT `Product Name`)
        FROM discounted_products
        WHERE `Product Name` LIKE %s
    """, (f"%{search_query}%",))
    total_products = cursor.fetchone()[0]

    # Pagination offset
    offset = (page - 1) * items_per_page

    # Get the product data sorted by the highest discount (convert string to number using SQL logic)
    cursor.execute(f"""
        {base_query}
        ORDER BY CAST(SUBSTRING_INDEX(`Discount`, '%', 1) AS UNSIGNED) DESC
        LIMIT %s OFFSET %s;
    """, (f"%{search_query}%", items_per_page, offset))
    
    rows = cursor.fetchall()

    # Fetch column names
    column_names = [i[0] for i in cursor.description]

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Calculate the total number of pages
    total_pages = (total_products + items_per_page - 1) // items_per_page

    # Determine the range of pages to display (show a maximum of 6 pages)
    max_visible_pages = 10
    start_page = max(1, page - max_visible_pages // 2)
    end_page = min(total_pages, start_page + max_visible_pages - 1)
    if end_page - start_page + 1 < max_visible_pages:
        start_page = max(1, end_page - max_visible_pages + 1)

    # Render the data in the HTML template
    return render_template(
        'index.html',
        rows=rows,
        columns=column_names,
        current_page=page,
        total_pages=total_pages,
        total_products=total_products,
        search_query=search_query,
        start_page=start_page,
        end_page=end_page
    )

if __name__ == '__main__':
    app.run(debug=True)
