from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import sqlite3
from datetime import datetime
from config import Config
import time
from performance_monitor import performance_monitor
import os

class SQLiteManager:
    def __init__(self, db_path="restaurant_list.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    @performance_monitor.monitor_query("sqlite_search_restaurants")
    def search_restaurants(self, filters):
        """Search restaurants using SQLite for better performance"""
        query = """
        SELECT DISTINCT r.* 
        FROM Restaurants r
        WHERE 1=1
        """
        params = []
        
        # Add search name filter
        if filters.get('search_name') and filters['search_name'] != "All" and filters['search_name'] is not None:
            query += " AND r.Name LIKE ?"
            params.append('%' + filters['search_name'] + '%')
        
        # Add cuisine filter
        if filters.get('selected_cuisine') and filters['selected_cuisine'] != "All" and filters['selected_cuisine'] is not None:
            query += " AND r.Cuisine = ?"
            params.append(filters['selected_cuisine'])
        
        # Add location filter
        if filters.get('selected_locations') and filters['selected_locations']:
            placeholders = ','.join(['?' for _ in filters['selected_locations']])
            query += f" AND r.Location IN ({placeholders})"
            params.extend(filters['selected_locations'])
        
        # Add day/time filter - optimized with EXISTS instead of IN
        if ((filters.get('selected_day') and filters['selected_day'] != "All") or 
            (filters.get('selected_time') and filters['selected_time'] != "All")):
            query += """
            AND EXISTS (
                SELECT 1 FROM Options o 
                WHERE o.RestaurantId = r.RestaurantId
            """
            if filters.get('selected_day') and filters['selected_day'] != "All":
                query += " AND o.Day = ?"
                params.append(filters['selected_day'])
            if filters.get('selected_time') and filters['selected_time'] != "All":
                query += " AND o.Time = ?"
                params.append(filters['selected_time'])
            query += ")"
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        # Convert to dictionary format for consistency
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in results]
    
    def get_restaurant_options(self, restaurant_id, selected_day="All", selected_time="All"):
        """Get options for a specific restaurant using SQLite"""
        if restaurant_id is None:
            return []
        
        query = "SELECT * FROM Options WHERE RestaurantId = ?"
        params = [restaurant_id]
        
        if selected_day and selected_day != "All":
            query += " AND Day = ?"
            params.append(selected_day)
        if selected_time and selected_time != "All":
            query += " AND Time = ?"
            params.append(selected_time)
        
        query += " ORDER BY Day, Time"
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        # Convert to dictionary format
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in results]
    
    def get_filter_data(self):
        """Get filter data from SQLite for better performance - optimized version"""
        # Use a single optimized query instead of multiple separate queries
        query = """
        SELECT 
            (SELECT GROUP_CONCAT(DISTINCT Name) FROM Restaurants WHERE Name IS NOT NULL) as restaurants,
            (SELECT GROUP_CONCAT(DISTINCT Cuisine) FROM Restaurants WHERE Cuisine IS NOT NULL) as cuisines,
            (SELECT GROUP_CONCAT(DISTINCT Location) FROM Restaurants WHERE Location IS NOT NULL) as locations,
            (SELECT GROUP_CONCAT(DISTINCT Day) FROM Options WHERE Day IS NOT NULL) as days,
            (SELECT GROUP_CONCAT(DISTINCT Time) FROM Options WHERE Time IS NOT NULL) as times
        """
        
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        
        if result:
            # Parse the concatenated strings back to lists
            restaurants = result[0].split(',') if result[0] else []
            cuisines = result[1].split(',') if result[1] else []
            locations = result[2].split(',') if result[2] else []
            days = result[3].split(',') if result[3] else []
            times = result[4].split(',') if result[4] else []
            
            # Filter days and times according to Config order
            days = [day for day in Config.DAY_ORDER if day in days]
            times = [time for time in Config.TIME_ORDER if time in times]
            
            return {
                'restaurants': sorted(restaurants),
                'cuisines': sorted(cuisines),
                'locations': sorted(locations),
                'days': days,
                'times': times,
                'users': []  # Users will be handled by MongoDB
            }
        
        return {
            'restaurants': [],
            'cuisines': [],
            'locations': [],
            'days': [],
            'times': [],
            'users': []
        }
    
    def get_all_restaurants(self):
        """Get all restaurants for dropdowns using SQLite"""
        self.cursor.execute("SELECT Name, RestaurantId FROM Restaurants WHERE Name IS NOT NULL ORDER BY Name")
        results = self.cursor.fetchall()
        return [{'Name': row[0], 'RestaurantId': row[1]} for row in results]
    
    def get_restaurant_by_name(self, restaurant_name):
        """Get restaurant by name from SQLite"""
        self.cursor.execute("SELECT * FROM Restaurants WHERE Name = ?", (restaurant_name,))
        result = self.cursor.fetchone()
        if result:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, result))
        return None
    
    def get_restaurant_by_id(self, restaurant_id):
        """Get restaurant by ID from SQLite"""
        self.cursor.execute("SELECT * FROM Restaurants WHERE RestaurantId = ?", (restaurant_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, result))
        return None
    
    def close(self):
        """Close SQLite connection"""
        self.conn.close()

class DatabaseManager:
    """Manages hybrid database operations (SQLite for restaurants/options, MongoDB for reviews)"""
    
    def __init__(self):
        # MongoDB for reviews only
        self.client = MongoClient(Config.MONGODB_URI, server_api=ServerApi('1'))
        self.db = self.client['MiamiSpice']
        self.reviews_collection = self.db[Config.REVIEWS_COLLECTION]
        
        # SQLite for restaurants and options
        self.sqlite_manager = SQLiteManager()
        
        # Enhanced caching for better performance
        self._filter_data_cache = None
        self._filter_data_cache_timestamp = 0
        self._cache_duration = 300  # 5 minutes cache
        
        # Create indexes for MongoDB reviews
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create database indexes for optimal query performance"""
        try:
            # Reviews collection indexes
            self.reviews_collection.create_index([("RestaurantId", 1)])
            self.reviews_collection.create_index([("UserName", 1)])
            self.reviews_collection.create_index([("CreatedAt", -1)])
            self.reviews_collection.create_index([("UserName", 1), ("RestaurantId", 1)])  # Compound index
            
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
    
    @performance_monitor.monitor_query("get_filter_data")
    def get_filter_data(self):
        """Get all filter data using SQLite for restaurants/options and MongoDB for users with caching"""
        current_time = time.time()
        
        # Return cached data if still valid
        if (self._filter_data_cache and 
            current_time - self._filter_data_cache_timestamp < self._cache_duration):
            return self._filter_data_cache
        
        # Use SQLite for most filter data
        sqlite_filter_data = self.sqlite_manager.get_filter_data()
        
        # Get users from MongoDB (since reviews are in MongoDB)
        users_pipeline = [{'$group': {'_id': '$UserName'}}]
        users = sorted([doc['_id'] for doc in self.reviews_collection.aggregate(users_pipeline) 
                       if doc['_id'] and isinstance(doc['_id'], str)])
        
        # Combine SQLite and MongoDB data
        sqlite_filter_data['users'] = users
        
        # Cache the result
        self._filter_data_cache = sqlite_filter_data
        self._filter_data_cache_timestamp = current_time
        
        return sqlite_filter_data
    
    @performance_monitor.monitor_query("search_restaurants")
    def search_restaurants(self, filters):
        """Search restaurants using SQLite for better performance"""
        # Use SQLite for basic search and filtering
        sqlite_results = self.sqlite_manager.search_restaurants(filters)
        
        # If user filter is applied, we need to filter by MongoDB reviews
        if filters.get('selected_user') and filters['selected_user'].strip():
            # Get restaurant IDs that have reviews from the specified user - optimized with projection
            reviews_filter = {
                'UserName': {'$regex': filters['selected_user'], '$options': 'i'}
            }
            
            # Use projection to only get RestaurantId field, reducing data transfer
            reviewed_restaurant_ids = set(
                doc['RestaurantId'] 
                for doc in self.reviews_collection.find(reviews_filter, {'RestaurantId': 1, '_id': 0})
            )
            
            # Filter SQLite results by reviewed restaurant IDs
            sqlite_results = [restaurant for restaurant in sqlite_results 
                            if restaurant.get('RestaurantId') in reviewed_restaurant_ids]
        
        return sqlite_results
    
    def get_restaurant_options(self, restaurant_id, selected_day="All", selected_time="All"):
        """Get options for a specific restaurant using SQLite"""
        return self.sqlite_manager.get_restaurant_options(restaurant_id, selected_day, selected_time)
    
    def submit_review(self, restaurant_name, user_name, rating, comment):
        """Submit a new review using MongoDB"""
        # Get restaurant ID from SQLite
        restaurant = self.sqlite_manager.get_restaurant_by_name(restaurant_name)
        if not restaurant:
            return False, "Restaurant not found."
        
        restaurant_id = restaurant.get('RestaurantId')
        if restaurant_id is None:
            return False, "Restaurant ID not found."
        
        # Insert review into MongoDB
        review_data = {
            'RestaurantId': restaurant_id,
            'UserName': (user_name or '').strip(),
            'Rating': rating,
            'Comment': (comment or '').strip(),
            'CreatedAt': datetime.now()
        }
        self.reviews_collection.insert_one(review_data)
        
        # Invalidate cache since we added new data
        self._filter_data_cache = None
        
        return True, "Review submitted successfully!"
    
    @performance_monitor.monitor_query("get_restaurant_reviews")
    def get_restaurant_reviews(self, restaurant_name):
        """Get all reviews for a specific restaurant using MongoDB"""
        # Get restaurant ID from SQLite
        restaurant = self.sqlite_manager.get_restaurant_by_name(restaurant_name)
        if not restaurant:
            return None
        
        restaurant_id = restaurant.get('RestaurantId')
        if restaurant_id is None:
            return None
        
        # Use aggregation to get reviews and calculate stats in one query
        pipeline = [
            {'$match': {'RestaurantId': restaurant_id}},
            {
                '$group': {
                    '_id': None,
                    'reviews': {'$push': '$$ROOT'},
                    'avg_rating': {'$avg': '$Rating'},
                    'total_reviews': {'$sum': 1}
                }
            }
        ]
        
        result = list(self.reviews_collection.aggregate(pipeline))
        
        if result:
            data = result[0]
            # Sort reviews by creation date
            reviews = sorted(data['reviews'], key=lambda x: x.get('CreatedAt', datetime.min), reverse=True)
            
            return {
                'reviews': reviews,
                'avg_rating': data['avg_rating'],
                'total_reviews': data['total_reviews']
            }
        
        return None
    
    @performance_monitor.monitor_query("get_user_reviews")
    def get_user_reviews(self, user_name):
        """Get all reviews by a specific user using MongoDB"""
        # Since we can't do a lookup from MongoDB to SQLite, we'll get the reviews first
        # and then enrich them with restaurant names from SQLite
        reviews = list(self.reviews_collection.find(
            {'UserName': {'$regex': (user_name or '').strip(), '$options': 'i'}}
        ).sort('CreatedAt', -1))
        
        enriched_reviews = []
        for review in reviews:
            # Get restaurant name from SQLite
            restaurant = self.sqlite_manager.get_restaurant_by_id(review.get('RestaurantId'))
            restaurant_name = restaurant.get('Name') if restaurant else 'Unknown'
            
            created_at = review['CreatedAt'].strftime('%Y-%m-%d %H:%M') if isinstance(review['CreatedAt'], datetime) else str(review['CreatedAt'])
            
            enriched_reviews.append({
                'Restaurant': restaurant_name,
                'Rating': review['Rating'],
                'Comment': review.get('Comment') or '',
                'CreatedAt': created_at
            })
        
        return enriched_reviews
    
    def get_all_restaurants(self):
        """Get all restaurants for dropdowns using SQLite"""
        return self.sqlite_manager.get_all_restaurants()
    
    def get_restaurant_id_field(self, collection_name):
        """Get the restaurant ID field name for a given collection"""
        # For SQLite collections, the field is always 'RestaurantId'
        if collection_name in [Config.RESTAURANTS_COLLECTION, Config.OPTIONS_COLLECTION]:
            return 'RestaurantId'
        # For MongoDB collections (reviews), the field is also 'RestaurantId'
        elif collection_name == Config.REVIEWS_COLLECTION:
            return 'RestaurantId'
        else:
            # Default fallback
            return 'RestaurantId'
    
    def test_connection(self):
        """Test the database connection and return status"""
        try:
            # Test MongoDB connection
            self.client.admin.command('ping')
            
            # Test SQLite connection
            self.sqlite_manager.cursor.execute("SELECT 1")
            
            # Test database access
            collections = self.db.list_collection_names()
            
            return {
                'status': 'success',
                'message': f'Connected to MiamiSpice database (SQLite + MongoDB)',
                'collections': collections
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'collections': []
            }
    
    def close(self):
        """Close the database connections"""
        self.client.close()
        self.sqlite_manager.close() 