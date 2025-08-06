import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('restaurant_list.db')
cursor = conn.cursor()

st.title("🍽️ Miami Spice Restaurant Finder")

# -- 1. Search Functionality
st.header("🔍 Search Restaurant")
search_name = st.text_input("Search by restaurant name")

if search_name:
    query = f"""
    SELECT r.Name, r.Cuisine, r.Location, r.Link, o.Time, o.Day, o.Price
    FROM Restaurants r
    LEFT JOIN Options o ON r.RestaurantId = o.RestaurantId
    WHERE r.Name LIKE ?
    """
    df = pd.read_sql_query(query, conn, params=[f"%{search_name}%"])
    if not df.empty:
        st.success("✅ Miami Spice options found!")
        st.dataframe(df)
    else:
        st.warning("❌ No Miami Spice options found.")

# -- 2. Filter Functionality
st.header("🗂️ Filter Restaurants")

# Get unique filter options
cuisines = pd.read_sql_query("SELECT DISTINCT Cuisine FROM Restaurants", conn)['Cuisine'].dropna().tolist()
days = pd.read_sql_query("SELECT DISTINCT Day FROM Options", conn)['Day'].dropna().tolist()
times = pd.read_sql_query("SELECT DISTINCT Time FROM Options", conn)['Time'].dropna().tolist()

col1, col2, col3, col4 = st.columns(4)
with col1:
    selected_cuisine = st.selectbox("Cuisine", ["All"] + cuisines)
with col2:
    selected_day = st.selectbox("Day", ["All"] + days)
with col3:
    selected_time = st.selectbox("Time", ["All"] + times)
with col4:
    username = st.text_input("Your Name (to filter 'Never been')")

# Build dynamic query
filters = []
params = []

if selected_cuisine != "All":
    filters.append("r.Cuisine = ?")
    params.append(selected_cuisine)

if selected_day != "All":
    filters.append("o.Day = ?")
    params.append(selected_day)

if selected_time != "All":
    filters.append("o.Time = ?")
    params.append(selected_time)

# Exclude reviewed restaurants
if username:
    filters.append("""r.RestaurantId NOT IN (
        SELECT RestaurantId FROM Reviews WHERE UserName = ?
    )""")
    params.append(username)

where_clause = "WHERE " + " AND ".join(filters) if filters else ""

filter_query = f"""
SELECT DISTINCT r.RestaurantId, r.Name, r.Cuisine, r.Location, r.Link
FROM Restaurants r
LEFT JOIN Options o ON r.RestaurantId = o.RestaurantId
{where_clause}
ORDER BY r.Name
"""

filtered_df = pd.read_sql_query(filter_query, conn, params=params)
st.dataframe(filtered_df)

# -- 3. Rating Tool
st.header("🌟 Leave a Review")

with st.form("review_form"):
    review_user = st.text_input("Your Name")
    restaurant_name = st.selectbox("Select Restaurant", pd.read_sql_query("SELECT Name FROM Restaurants", conn)['Name'])
    rating = st.slider("Rating", 1, 5, 3)
    comment = st.text_area("Comment")
    submit = st.form_submit_button("Submit Review")

    if submit:
        # Get RestaurantId
        restaurant_id_query = "SELECT RestaurantId FROM Restaurants WHERE Name = ?"
        restaurant_id = pd.read_sql_query(restaurant_id_query, conn, params=[restaurant_name])['RestaurantId'][0]

        # Insert review
        cursor.execute("""
        INSERT INTO Reviews (RestaurantId, UserName, Rating, Comment, CreatedAt)
        VALUES (?, ?, ?, ?, ?)
        """, (restaurant_id, review_user, rating, comment, datetime.now()))
        conn.commit()
        st.success("✅ Review submitted!")

# Close connection when app exits
# conn.close()  # Optional if not using persistently
