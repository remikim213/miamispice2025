import streamlit as st
import pandas as pd
from datetime import datetime
from config import Config

class UIComponents:
    """UI components for the Miami Spice application"""
    
    @staticmethod
    def render_sidebar():
        """Render the sidebar with navigation and info"""
        menu = st.sidebar.radio("Navigate", ["🍽️ Browse Restaurants", "🌟 Reviews"])
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Welcome!")
        st.sidebar.markdown(f"This app helps you explore, filter, and review restaurants participating in **Miami Spice 2025** which is from **{Config.MIAMI_SPICE_START}** to **{Config.MIAMI_SPICE_END}**. Use the navigation menu to get started.")
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Connect with me")
        st.sidebar.markdown("Remi Kim")
        st.sidebar.markdown(f"[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)]({Config.LINKEDIN_URL})")
        st.sidebar.markdown(f"[![Instagram](https://img.shields.io/badge/Instagram-Follow-purple?logo=instagram)]({Config.INSTAGRAM_URL})")
        
        return menu
    
    @staticmethod
    def render_debug_info(db_manager):
        """Render debug information in sidebar"""
        st.sidebar.markdown("### Debug Info")
        st.sidebar.markdown(f"Restaurants ID field: {db_manager.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)}")
        st.sidebar.markdown(f"Options ID field: {db_manager.get_restaurant_id_field(Config.OPTIONS_COLLECTION)}")
        st.sidebar.markdown(f"Reviews ID field: {db_manager.get_restaurant_id_field(Config.REVIEWS_COLLECTION)}")
    
    @staticmethod
    def render_restaurant_search_form(filter_data):
        """Render the restaurant search form"""
        st.subheader("🍽️ Search and Filter Restaurants")

        with st.form("filter_search_form"):
            search_name = st.selectbox("Restaurant Name (search)", ["All"] + filter_data['restaurants'])
            col1, col2, col3, col4, col5 = st.columns(5)
            selected_cuisine = col1.selectbox("Cuisine", ["All"] + filter_data['cuisines'])
            selected_day = col2.selectbox("Day", ["All"] + filter_data['days'])
            selected_time = col3.selectbox("Time", ["All"] + filter_data['times'])
            selected_locations = col4.multiselect("Location", filter_data['locations'], default=[])
            selected_user = col5.text_input("User")

            submit_filter = st.form_submit_button("🔎 Search / Filter")
            
            return {
                'search_name': search_name,
                'selected_cuisine': selected_cuisine,
                'selected_day': selected_day,
                'selected_time': selected_time,
                'selected_locations': selected_locations,
                'selected_user': selected_user,
                'submit_filter': submit_filter
            }
    
    @staticmethod
    def render_restaurant_results(restaurants, db_manager, filters):
        """Render restaurant search results"""
        if not restaurants:
            st.warning("🚫 No matching restaurants found. Please try different filters.")
        else:
            st.success(f"✅ {len(restaurants)} restaurant(s) found.")

            for restaurant in restaurants:
                rest_name = restaurant.get('Name', 'Unknown')
                rest_cuisine = restaurant.get('Cuisine', 'Unknown')
                rest_location = restaurant.get('Location', 'Unknown')
                rest_link = restaurant.get('Link', '')

                with st.expander(f"{rest_name} ({rest_cuisine}, {rest_location})"):
                    if rest_link:
                        st.markdown(f'<a href="{rest_link}" target="_blank">Visit Site for the Menu</a>', unsafe_allow_html=True)

                    # Get options for this restaurant
                    restaurant_id_field = db_manager.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
                    restaurant_options = db_manager.get_restaurant_options(
                        restaurant[restaurant_id_field],
                        filters.get('selected_day', 'All'),
                        filters.get('selected_time', 'All')
                    )
                    
                    if restaurant_options:
                        for option in restaurant_options:
                            day = option.get('Day', 'Unknown')
                            time = option.get('Time', 'Unknown')
                            price = option.get('Price', 'Unknown')
                            st.write(f"- **{day}** | {time} | Price: {price}")
                    else:
                        st.write("No available options.")
    
    @staticmethod
    def render_review_form(db_manager):
        """Render the review submission form"""
        st.subheader("🌟 Leave a Review")

        with st.form("review_form"):
            review_user = st.text_input("Your Name")
            restaurant_list = db_manager.get_all_restaurants()
            restaurant_names = [doc['Name'] for doc in restaurant_list]
            restaurant_name = st.selectbox(
                "Select Restaurant",
                ["-- Select a restaurant --"] + restaurant_names
            )

            rating = st.slider("Rating (1 = Bad, 10 = Excellent)", 1, 10, 5)
            comment = st.text_area("Leave a comment (optional)")
            submit = st.form_submit_button("✅ Submit Review")

            return {
                'review_user': review_user,
                'restaurant_name': restaurant_name,
                'rating': rating,
                'comment': comment,
                'submit': submit
            }
    
    @staticmethod
    def render_review_view_form(db_manager):
        """Render the review viewing form"""
        st.markdown("---")
        st.subheader("🌟 View Reviews by Restaurant")

        with st.form("View Reviews By Restaurant"):
            restaurant_list = db_manager.get_all_restaurants()
            restaurant_names = [doc['Name'] for doc in restaurant_list]
            restaurant_name = st.selectbox(
                "Select Restaurant",
                ["-- Select a restaurant --"] + restaurant_names
            )
            submit_view = st.form_submit_button("View Reviews")

            return {
                'restaurant_name': restaurant_name,
                'submit_view': submit_view
            }
    
    @staticmethod
    def render_restaurant_reviews(review_data, restaurant_name):
        """Render restaurant reviews"""
        if not review_data:
            st.info(f" No reviews yet for {restaurant_name}. Be the first to leave a review!")
            return
        
        # Display summary
        st.subheader(f"📊 {restaurant_name} - Reviews Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Rating", f"{review_data['avg_rating']:.1f}/10")
        with col2:
            st.metric("Total Reviews", review_data['total_reviews'])
        
        # Display star rating visualization
        stars = "★" * int(review_data['avg_rating']) + "☆" * (10 - int(review_data['avg_rating']))
        st.write(f"Rating: {stars} ({review_data['avg_rating']:.1f}/10)")
        
        st.markdown("---")
        st.subheader("📝 All Reviews")
        
        # Display reviews
        for review in review_data['reviews']:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    created_at = review['CreatedAt'].strftime('%Y-%m-%d %H:%M') if isinstance(review['CreatedAt'], datetime) else str(review['CreatedAt'])
                    st.write(f"**{review['UserName']}** - {created_at}")
                    review_stars = "★" * review['Rating'] + "☆" * (10 - review['Rating'])
                    st.write(f"{review_stars} ({review['Rating']}/10)")
                    if review.get('Comment') and review['Comment'].strip():
                        st.write(f" {review['Comment']}")
                with col2:
                    st.write("")
                st.markdown("---")
    
    @staticmethod
    def render_user_reviews_form():
        """Render the user reviews viewing form"""
        st.markdown("---")
        st.subheader("📝 View Your Reviews")
        review_user_view = st.text_input("Enter your name to view your reviews", key="view_reviews")
        return review_user_view
    
    @staticmethod
    def render_user_reviews(user_reviews):
        """Render user reviews"""
        if user_reviews:
            # Create DataFrame for display
            user_reviews_df = pd.DataFrame(user_reviews)
            st.write(user_reviews_df)
        else:
            st.info("You have not submitted any reviews yet.") 