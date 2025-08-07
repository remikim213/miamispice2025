import os
#from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
#load_dotenv()

class Config:
    """Configuration class for the Miami Spice application"""
    
    # MongoDB Configuration
    MONGO_USER = st.secrets["mongo"]["username"]
    MONGO_PASS = st.secrets["mongo"]["password"]
    MONGO_HOST = st.secrets["mongo"]["host"]
    MONGODB_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}/?retryWrites=true&w=majority&appName=MiamiSpice"

    # Collection names
    RESTAURANTS_COLLECTION = 'Restaurants'
    OPTIONS_COLLECTION = 'Options'
    REVIEWS_COLLECTION = 'Reviews'
    
    # App Configuration
    APP_TITLE = "Miami Spice 2025"
    PAGE_TITLE = "Miami Spice Finder"
    
    # Filter options
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    TIME_ORDER = ["Brunch", "Lunch", "Dinner"]
    
    # Possible restaurant ID field names
    POSSIBLE_RESTAURANT_ID_FIELDS = ['RestaurantId', 'restaurantId', 'restaurant_id', 'Restaurant_ID']
    
    # Social links
    LINKEDIN_URL = "https://www.linkedin.com/in/remikim213/"
    INSTAGRAM_URL = "https://www.instagram.com/remikim213"
    
    # Miami Spice dates
    MIAMI_SPICE_START = "August 1st"
    MIAMI_SPICE_END = "September 30th" 