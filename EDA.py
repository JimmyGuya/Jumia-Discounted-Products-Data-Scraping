import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Load environment variables
load_dotenv()

# Connect to MySQL database using mysql.connector
conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)

# Create a cursor object
cursor = conn.cursor()

# Query the data to select all
query = "SELECT * FROM discounted_products"
cursor.execute(query)

# Fetch all the rows from the query
rows = cursor.fetchall()

# Get column names from the cursor
column_names = [i[0] for i in cursor.description]

# Convert the rows into a Pandas DataFrame
df = pd.DataFrame(rows, columns=column_names)

# Close the cursor and the connection
cursor.close()
conn.close()

# Print the first few rows of the dataframe
print(df.head())

# Convert the 'Discount' column to numeric (removing any '%' signs and converting to float)
df['Discount'] = df['Discount'].str.replace('%', '').astype(float)

# EDA: General overview of the data
print(df.info())
print(df.describe())

# Check for missing values
print(df.isnull().sum())

# Distribution of discounts
plt.figure(figsize=(10, 6))
sns.histplot(df['Discount'], bins=20, kde=True)
plt.title("Distribution of Discounts")
plt.show()

# Top 10 products with the highest discount
top_discounted_products = df.nlargest(10, 'Discount')
print(top_discounted_products[['Product Name', 'Discount']])

# Boxplot of price before and after discount
plt.figure(figsize=(12, 6))
sns.boxplot(data=df[['Price Before Discount', 'Current Price After Discount']])
plt.title("Price Distribution Before and After Discount")
plt.show()