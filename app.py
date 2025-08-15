import streamlit as st
from config import Config
from database import DatabaseManager
from ui_components import UIComponents

def main():
    """Main application function"""
    # Set page configuration
    st.set_page_config(page_title=Config.PAGE_TITLE, layout="wide")
    st.title(Config.APP_TITLE)
    
    try:
        # Initialize database connection
        db_manager = DatabaseManager()
        
        # Test connection
        connection_status = db_manager.test_connection()
        if connection_status['status'] == 'error':
            st.error(f"❌ Database connection failed: {connection_status['message']}")
            st.info("💡 Please check your secrets.toml file and MongoDB connection settings.")
            st.stop()
        
        # Render sidebar and get menu selection
        menu = UIComponents.render_sidebar()
        
        # Get filter data for dropdowns
        filter_data = db_manager.get_filter_data()
        
        # Ensure filter_data has all required keys
        if not filter_data:
            st.error("❌ Failed to load filter data from database.")
            st.stop()
        
        # Handle menu navigation
        if menu == "🍽️ Browse Restaurants":
            handle_restaurant_browsing(db_manager, filter_data)
        elif menu == "🌟 Reviews":
            handle_reviews(db_manager)
        
        # Clean up database connection
        db_manager.close()
        
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.info("💡 Try running `python test_connection.py` to debug your MongoDB connection.")
        st.stop()

def handle_restaurant_browsing(db_manager, filter_data):
    """Handle the restaurant browsing page"""
    # Render search form
    form_data = UIComponents.render_restaurant_search_form(filter_data)
    
    # Process form submission
    if form_data['submit_filter']:
        # Build filters dictionary
        filters = {
            'search_name': form_data['search_name'],
            'selected_cuisine': form_data['selected_cuisine'],
            'selected_day': form_data['selected_day'],
            'selected_time': form_data['selected_time'],
            'selected_locations': form_data['selected_locations'],
            'selected_price': form_data['selected_price'],
            'selected_user': form_data['selected_user']
        }
        
        # Search restaurants
        restaurants = db_manager.search_restaurants(filters)
        
        # Render results
        UIComponents.render_restaurant_results(restaurants, db_manager, filters)

def handle_reviews(db_manager):
    """Handle the reviews page"""
    # Submit review form
    review_form_data = UIComponents.render_review_form(db_manager)
    
    if review_form_data['submit'] and review_form_data['restaurant_name'] != "-- Select a restaurant --":
        success, message = db_manager.submit_review(
            review_form_data['restaurant_name'],
            review_form_data['review_user'],
            review_form_data['rating'],
            review_form_data['comment']
        )
        
        if success:
            st.success(f"🎉 {message}")
        else:
            st.error(message)
    
    # View reviews by restaurant form
    review_view_data = UIComponents.render_review_view_form(db_manager)
    
    if review_view_data['submit_view'] and review_view_data['restaurant_name'] != "-- Select a restaurant --":
        review_data = db_manager.get_restaurant_reviews(review_view_data['restaurant_name'])
        UIComponents.render_restaurant_reviews(review_data, review_view_data['restaurant_name'])
    
    # View user reviews form
    review_user_view = UIComponents.render_user_reviews_form()
    
    if review_user_view:
        user_reviews = db_manager.get_user_reviews(review_user_view)
        UIComponents.render_user_reviews(user_reviews)

if __name__ == "__main__":
    main()