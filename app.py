import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Database connection
conn = sqlite3.connect('restaurant_list.db', check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(page_title="Miami Spice Finder", layout="wide")

st.title("Miami Spice 2025")

# Sidebar menu
menu = st.sidebar.radio("Navigate", ["🍽️ Browse Restaurants", "🌟 Reviews"])
st.sidebar.markdown("---")
st.sidebar.markdown("### Welcome!")
st.sidebar.markdown("This app helps you explore, filter, and review restaurants participating in **Miami Spice 2025**. Use the navigation menu to get started.")
st.sidebar.markdown("---")
st.sidebar.markdown("### Connect with me")
st.sidebar.markdown("Remi Kim")
st.sidebar.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/remikim213/)")
st.sidebar.markdown("[![Instagram](https://img.shields.io/badge/Instagram-Follow-purple?logo=instagram)](https://www.instagram.com/remikim213)")

# Shared data
cuisines = sorted(pd.read_sql_query("SELECT DISTINCT Cuisine FROM Restaurants", conn)['Cuisine'].dropna().tolist())
locations = sorted(pd.read_sql_query("SELECT DISTINCT Location FROM Restaurants", conn)['Location'].dropna().tolist())
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
existing_days = pd.read_sql_query("SELECT DISTINCT Day FROM Options", conn)['Day'].dropna().tolist()
days = [day for day in day_order if day in existing_days]
time_order = ["Brunch", "Lunch", "Dinner"]
existing_times = pd.read_sql_query("SELECT DISTINCT Time FROM Options", conn)['Time'].dropna().tolist()
times = [time for time in time_order if time in existing_times]
users = sorted(pd.read_sql_query("SELECT DISTINCT UserName FROM Reviews", conn)['UserName'].dropna().tolist())

# ---------------------------
# 1. Restaurants
# ---------------------------
if menu == "🍽️ Browse Restaurants":
    st.subheader("🍽️ Search and Filter Restaurants")

    with st.form("filter_search_form"):
        search_name = st.text_input("Restaurant Name (search)")
        col1, col2, col3, col4, col5 = st.columns(5)
        selected_cuisine = col1.selectbox("Cuisine", ["All"] + cuisines)
        selected_day = col2.selectbox("Day", ["All"] + days)
        selected_time = col3.selectbox("Time", ["All"] + times)
        selected_locations = col4.multiselect("Location", locations, default=[])
        selected_user = col5.text_input("User")

        submit_filter = st.form_submit_button("🔎 Search / Filter")

    if submit_filter:
        filters = []
        params = []

        if search_name:
            filters.append("r.Name LIKE ?")
            params.append(f"%{search_name}%")
        if selected_cuisine != "All":
            filters.append("r.Cuisine = ?")
            params.append(selected_cuisine)
        if selected_day != "All":
            filters.append("o.Day = ?")
            params.append(selected_day)
        if selected_time != "All":
            filters.append("o.Time = ?")
            params.append(selected_time)
        if selected_locations:
            placeholders = ','.join(['?' for _ in selected_locations])
            filters.append(f"r.Location IN ({placeholders})")
            params.extend(selected_locations)
        if selected_user:
            filters.append("rev.UserName LIKE ?")
            params.append(f"%{selected_user}%")

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        query = f"""
        SELECT DISTINCT r.RestaurantId, r.Name, r.Cuisine, r.Location, r.Link
        FROM Restaurants r
        LEFT JOIN Options o ON r.RestaurantId = o.RestaurantId
        LEFT JOIN Reviews rev ON r.RestaurantId = rev.RestaurantId
        {where_clause}
        ORDER BY r.Name
        """
        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            st.warning("🚫 No matching restaurants found. Please try different filters.")
        else:
            st.success(f"✅ {len(df)} restaurant(s) found.")

            df['Link'] = df['Link'].apply(
                lambda x: f'<a href="{x}" target="_blank">Visit Site for the Menu</a>' if pd.notna(x) else "")
            df = df.rename(columns={
                'Name': 'Restaurant',
                'Cuisine': 'Cuisine',
                'Location': 'Location',
                'Link': 'Website'
            })

            restaurant_ids = df['RestaurantId'].tolist()
            options_query = f"""
                SELECT RestaurantId, Time, Day, Price
                FROM Options
                WHERE RestaurantId IN ({','.join(['?'] * len(restaurant_ids))})
                ORDER BY Day, Time
            """
            options_df = pd.read_sql_query(options_query, conn, params=restaurant_ids)
            options_grouped = options_df.groupby('RestaurantId')

            for idx, row in df.iterrows():
                rest_id = row['RestaurantId']
                rest_name = row['Restaurant']
                rest_cuisine = row['Cuisine']
                rest_location = row['Location']
                rest_link = row['Website']

                with st.expander(f"{rest_name} ({rest_cuisine}, {rest_location})"):
                    if pd.notna(rest_link) and rest_link != "":
                        st.markdown(rest_link, unsafe_allow_html=True)

                    if rest_id in options_grouped.groups:
                        rest_options = options_grouped.get_group(rest_id)
                        rest_options['Day'] = pd.Categorical(rest_options['Day'], categories=day_order, ordered=True)
                        rest_options['Time'] = pd.Categorical(rest_options['Time'], categories=time_order, ordered=True)
                        rest_options = rest_options.sort_values(by=["Day", "Time"])
                        for _, opt_row in rest_options.iterrows():
                            st.write(f"- **{opt_row['Day']}** | {opt_row['Time']} | Price: {opt_row['Price']}")
                    else:
                        st.write("No available options.")

# ---------------------------
# 2. Reviews
# ---------------------------
elif menu == "🌟 Reviews":
    st.subheader("🌟 Leave a Review")

    with st.form("review_form"):
        review_user = st.text_input("Your Name")
        restaurant_list = pd.read_sql_query("SELECT Name, RestaurantId FROM Restaurants ORDER BY Name", conn)
        restaurant_name = st.selectbox(
            "Select Restaurant",
            ["-- Select a restaurant --"] + restaurant_list['Name'].tolist()
        )

        rating = st.slider("Rating (1 = Bad, 10 = Excellent)", 1, 10, 5)
        comment = st.text_area("Leave a comment (optional)")
        submit = st.form_submit_button("✅ Submit Review")

    if submit:
        selected_row = restaurant_list[restaurant_list['Name'] == restaurant_name]
        if not selected_row.empty:
            restaurant_id = int(selected_row['RestaurantId'].values[0])
            cursor.execute("""
                INSERT INTO Reviews (RestaurantId, UserName, Rating, Comment, CreatedAt)
                VALUES (?, ?, ?, ?, ?)
            """, (restaurant_id, review_user.strip(), rating, comment.strip(), datetime.now()))
            conn.commit()
            st.success("🎉 Review submitted successfully!")
        else:
            st.error("Restaurant not found.")

    st.markdown("---")
    
    st.subheader("🌟 View Reviews")

    with st.form("View Reviews By Restaurant"):
        restaurant_list = pd.read_sql_query("SELECT Name, RestaurantId FROM Restaurants ORDER BY Name", conn)
        restaurant_name = st.selectbox(
            "Select Restaurant",
            ["-- Select a restaurant --"] + restaurant_list['Name'].tolist()
        )
        submit_view = st.form_submit_button("View Reviews")

    # Display restaurant reviews and average rating when submitted
    if submit_view and restaurant_name != "-- Select a restaurant --":
        # Get restaurant ID
        selected_row = restaurant_list[restaurant_list['Name'] == restaurant_name]
        if not selected_row.empty:
            restaurant_id = int(selected_row['RestaurantId'].values[0])
            
            # Get average rating
            avg_rating_query = """
            SELECT AVG(Rating) as AverageRating, COUNT(*) as TotalReviews
            FROM Reviews 
            WHERE RestaurantId = ?
            """
            avg_result = pd.read_sql_query(avg_rating_query, conn, params=[restaurant_id])
            
            # Get all reviews with comments
            reviews_query = """
            SELECT UserName, Rating, Comment, CreatedAt
            FROM Reviews 
            WHERE RestaurantId = ?
            ORDER BY CreatedAt DESC
            """
            reviews_df = pd.read_sql_query(reviews_query, conn, params=[restaurant_id])
            
            if not reviews_df.empty:
                # Display average rating
                avg_rating = avg_result['AverageRating'].iloc[0]
                total_reviews = avg_result['TotalReviews'].iloc[0]
                
                st.subheader(f"📊 {restaurant_name} - Reviews Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Average Rating", f"{avg_rating:.1f}/10")
                with col2:
                    st.metric("Total Reviews", total_reviews)
                
                # Display star rating visualization
                stars = "★" * int(avg_rating) + "☆" * (10 - int(avg_rating))
                st.write(f"Rating: {stars} ({avg_rating:.1f}/10)")
                
                st.markdown("---")
                st.subheader("📝 All Reviews")
                
                # Format and display reviews
                reviews_df['CreatedAt'] = pd.to_datetime(reviews_df['CreatedAt']).dt.strftime('%Y-%m-%d %H:%M')
                reviews_df['Stars'] = reviews_df['Rating'].apply(lambda x: "★" * x + "☆" * (10 - x))
                
                for idx, review in reviews_df.iterrows():
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{review['UserName']}** - {review['CreatedAt']}")
                            st.write(f"{review['Stars']} ({review['Rating']}/10)")
                            if pd.notna(review['Comment']) and review['Comment'].strip():
                                st.write(f" {review['Comment']}")
                        with col2:
                            st.write("")
                        st.markdown("---")
            else:
                st.info(f" No reviews yet for {restaurant_name}. Be the first to leave a review!")

    st.markdown("---")
    st.subheader("📝 View Your Reviews")
    review_user_view = st.text_input("Enter your name to view your reviews", key="view_reviews")

    if review_user_view:
        query = """
        SELECT r.Name as Restaurant, rev.Rating, rev.Comment, rev.CreatedAt
        FROM Reviews rev
        JOIN Restaurants r ON rev.RestaurantId = r.RestaurantId
        WHERE rev.UserName = ?
        ORDER BY rev.CreatedAt DESC
        """
        user_reviews = pd.read_sql_query(query, conn, params=[review_user_view.strip()])

        if not user_reviews.empty:
            user_reviews['CreatedAt'] = pd.to_datetime(user_reviews['CreatedAt']).dt.strftime('%Y-%m-%d %H:%M')
            st.write(user_reviews)
        else:
            st.info("You have not submitted any reviews yet.")