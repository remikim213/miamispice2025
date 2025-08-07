from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from config import Config
import time
from performance_monitor import performance_monitor

class DatabaseManager:
    """Manages MongoDB connections and operations with optimized time complexity"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI, server_api=ServerApi('1'))
        self.db = self.client['MiamiSpice']
        self.restaurants_collection = self.db[Config.RESTAURANTS_COLLECTION]
        self.options_collection = self.db[Config.OPTIONS_COLLECTION]
        self.reviews_collection = self.db[Config.REVIEWS_COLLECTION]
        
        # Enhanced caching for better performance
        self._restaurant_id_fields = {}
        self._filter_data_cache = None
        self._filter_data_cache_timestamp = 0
        self._cache_duration = 300  # 5 minutes cache
        
        # Create indexes for better query performance
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create database indexes for optimal query performance"""
        try:
            # Restaurant collection indexes
            self.restaurants_collection.create_index([("Name", 1)])
            self.restaurants_collection.create_index([("Cuisine", 1)])
            self.restaurants_collection.create_index([("Location", 1)])
            
            # Options collection indexes
            self.options_collection.create_index([("RestaurantId", 1), ("Day", 1), ("Time", 1)])
            self.options_collection.create_index([("Day", 1)])
            self.options_collection.create_index([("Time", 1)])
            
            # Reviews collection indexes
            self.reviews_collection.create_index([("RestaurantId", 1)])
            self.reviews_collection.create_index([("UserName", 1)])
            self.reviews_collection.create_index([("CreatedAt", -1)])
            
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
    
    def get_restaurant_id_field(self, collection_name):
        """Determine the correct field name for restaurant ID in each collection with caching"""
        if collection_name in self._restaurant_id_fields:
            return self._restaurant_id_fields[collection_name]
            
        sample_doc = self.db[collection_name].find_one()
        if sample_doc:
            # Check common field names for restaurant ID
            for field in Config.POSSIBLE_RESTAURANT_ID_FIELDS:
                if field in sample_doc and sample_doc[field] is not None:
                    self._restaurant_id_fields[collection_name] = field
                    return field
            # If no common field found, return the first field that looks like an ID
            for key in sample_doc.keys():
                if 'id' in key.lower() and key != '_id' and sample_doc[key] is not None:
                    self._restaurant_id_fields[collection_name] = key
                    return key
        return 'RestaurantId'  # default fallback
    
    @performance_monitor.monitor_query("get_filter_data")
    def get_filter_data(self):
        """Get all filter data with caching and optimized queries"""
        current_time = time.time()
        
        # Return cached data if still valid
        if (self._filter_data_cache and 
            current_time - self._filter_data_cache_timestamp < self._cache_duration):
            return self._filter_data_cache
        
        # Use aggregation pipeline for efficient data retrieval
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'restaurants': {'$addToSet': '$Name'},
                    'cuisines': {'$addToSet': '$Cuisine'},
                    'locations': {'$addToSet': '$Location'}
                }
            }
        ]
        
        restaurant_data = list(self.restaurants_collection.aggregate(pipeline))
        
        if restaurant_data:
            data = restaurant_data[0]
            restaurants = sorted([name for name in data.get('restaurants', []) if name and isinstance(name, str)])
            cuisines = sorted([cuisine for cuisine in data.get('cuisines', []) if cuisine and isinstance(cuisine, str)])
            locations = sorted([location for location in data.get('locations', []) if location and isinstance(location, str)])
        else:
            restaurants, cuisines, locations = [], [], []
        
        # Get days and times from options collection with aggregation
        days_pipeline = [{'$group': {'_id': '$Day'}}]
        times_pipeline = [{'$group': {'_id': '$Time'}}]
        
        existing_days = [doc['_id'] for doc in self.options_collection.aggregate(days_pipeline) if doc['_id'] and isinstance(doc['_id'], str)]
        days = [day for day in Config.DAY_ORDER if day in existing_days]
        
        existing_times = [doc['_id'] for doc in self.options_collection.aggregate(times_pipeline) if doc['_id'] and isinstance(doc['_id'], str)]
        times = [time for time in Config.TIME_ORDER if time in existing_times]
        
        # Get users from reviews collection with aggregation
        users_pipeline = [{'$group': {'_id': '$UserName'}}]
        users = sorted([doc['_id'] for doc in self.reviews_collection.aggregate(users_pipeline) if doc['_id'] and isinstance(doc['_id'], str)])
        
        filter_data = {
            'restaurants': restaurants,
            'cuisines': cuisines,
            'locations': locations,
            'days': days,
            'times': times,
            'users': users
        }
        
        # Cache the results
        self._filter_data_cache = filter_data
        self._filter_data_cache_timestamp = current_time
        
        return filter_data
    
    @performance_monitor.monitor_query("search_restaurants")
    def search_restaurants(self, filters):
        """Search restaurants based on filters with optimized queries"""
        # Build base filter query
        filter_query = {}
        
        if filters.get('search_name') and filters['search_name'] != "All" and filters['search_name'] is not None:
            filter_query['Name'] = {'$regex': filters['search_name'], '$options': 'i'}
        if filters.get('selected_cuisine') and filters['selected_cuisine'] != "All" and filters['selected_cuisine'] is not None:
            filter_query['Cuisine'] = filters['selected_cuisine']
        if filters.get('selected_locations') and filters['selected_locations']:
            filter_query['Location'] = {'$in': filters['selected_locations']}

        # Get restaurants matching the filter
        matching_restaurants = list(self.restaurants_collection.find(filter_query))
        
        if not matching_restaurants:
            return []
        
        # Get restaurant IDs for efficient filtering
        restaurant_id_field = self.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
        restaurant_ids = [restaurant[restaurant_id_field] for restaurant in matching_restaurants if restaurant.get(restaurant_id_field) is not None]
        
        # Use aggregation to efficiently filter by day/time and user reviews
        final_restaurant_ids = set(restaurant_ids)
        
        # Filter by day/time if specified
        if (filters.get('selected_day') and filters.get('selected_day') != "All") or (filters.get('selected_time') and filters.get('selected_time') != "All"):
            options_restaurant_id_field = self.get_restaurant_id_field(Config.OPTIONS_COLLECTION)
            options_filter = {options_restaurant_id_field: {'$in': restaurant_ids}}
            
            if filters.get('selected_day') and filters.get('selected_day') != "All":
                options_filter['Day'] = filters['selected_day']
            if filters.get('selected_time') and filters.get('selected_time') != "All":
                options_filter['Time'] = filters['selected_time']
            
            # Get restaurant IDs that have matching options
            available_restaurant_ids = set(
                doc[options_restaurant_id_field] 
                for doc in self.options_collection.find(options_filter, {options_restaurant_id_field: 1})
            )
            final_restaurant_ids &= available_restaurant_ids
        
        # Filter by user if specified
        if filters.get('selected_user') and filters['selected_user'].strip():
            reviews_restaurant_id_field = self.get_restaurant_id_field(Config.REVIEWS_COLLECTION)
            reviews_filter = {
                reviews_restaurant_id_field: {'$in': list(final_restaurant_ids)},
                'UserName': {'$regex': filters['selected_user'], '$options': 'i'}
            }
            
            # Get restaurant IDs that have reviews from the specified user
            reviewed_restaurant_ids = set(
                doc[reviews_restaurant_id_field] 
                for doc in self.reviews_collection.find(reviews_filter, {reviews_restaurant_id_field: 1})
            )
            final_restaurant_ids &= reviewed_restaurant_ids
        
        # Return only the restaurants that passed all filters
        return [restaurant for restaurant in matching_restaurants 
                if restaurant[restaurant_id_field] in final_restaurant_ids]
    
    def get_restaurant_options(self, restaurant_id, selected_day="All", selected_time="All"):
        """Get options for a specific restaurant with optimized query"""
        if restaurant_id is None:
            return []
            
        options_restaurant_id_field = self.get_restaurant_id_field(Config.OPTIONS_COLLECTION)
        options_filter = {options_restaurant_id_field: restaurant_id}
        
        if selected_day and selected_day != "All":
            options_filter['Day'] = selected_day
        if selected_time and selected_time != "All":
            options_filter['Time'] = selected_time
        
        # Use sort in the query instead of Python sorting
        restaurant_options = list(self.options_collection.find(options_filter).sort([
            ('Day', 1), ('Time', 1)
        ]))
        
        # Sort by day and time order using config
        restaurant_options.sort(key=lambda x: (
            Config.DAY_ORDER.index(x.get('Day') or ''), 
            Config.TIME_ORDER.index(x.get('Time') or '')
        ))
        
        return restaurant_options
    
    def submit_review(self, restaurant_name, user_name, rating, comment):
        """Submit a new review with optimized query"""
        restaurant_id_field = self.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
        reviews_restaurant_id_field = self.get_restaurant_id_field(Config.REVIEWS_COLLECTION)
        
        # Find the restaurant ID with index
        restaurant_doc = self.restaurants_collection.find_one({'Name': restaurant_name})
        if not restaurant_doc:
            return False, "Restaurant not found."
        
        restaurant_id = restaurant_doc.get(restaurant_id_field)
        if restaurant_id is None:
            return False, "Restaurant ID not found."
        
        # Insert review
        review_data = {
            reviews_restaurant_id_field: restaurant_id,
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
        """Get all reviews for a specific restaurant with optimized aggregation"""
        restaurant_id_field = self.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
        reviews_restaurant_id_field = self.get_restaurant_id_field(Config.REVIEWS_COLLECTION)
        
        # Get restaurant ID
        restaurant_doc = self.restaurants_collection.find_one({'Name': restaurant_name})
        if not restaurant_doc:
            return None
        
        restaurant_id = restaurant_doc.get(restaurant_id_field)
        if restaurant_id is None:
            return None
        
        # Use aggregation to get reviews and calculate stats in one query
        pipeline = [
            {'$match': {reviews_restaurant_id_field: restaurant_id}},
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
        """Get all reviews by a specific user with optimized aggregation"""
        restaurant_id_field = self.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
        reviews_restaurant_id_field = self.get_restaurant_id_field(Config.REVIEWS_COLLECTION)
        
        # Use aggregation to join reviews with restaurant data in one query
        pipeline = [
            {'$match': {'UserName': {'$regex': (user_name or '').strip(), '$options': 'i'}}},
            {'$sort': {'CreatedAt': -1}},
            {
                '$lookup': {
                    'from': Config.RESTAURANTS_COLLECTION,
                    'localField': reviews_restaurant_id_field,
                    'foreignField': restaurant_id_field,
                    'as': 'restaurant_info'
                }
            },
            {'$unwind': '$restaurant_info'},
            {
                '$project': {
                    'Restaurant': '$restaurant_info.Name',
                    'Rating': 1,
                    'Comment': 1,
                    'CreatedAt': 1
                }
            }
        ]
        
        enriched_reviews = []
        for review in self.reviews_collection.aggregate(pipeline):
            created_at = review['CreatedAt'].strftime('%Y-%m-%d %H:%M') if isinstance(review['CreatedAt'], datetime) else str(review['CreatedAt'])
            
            enriched_reviews.append({
                'Restaurant': review.get('Restaurant') or 'Unknown',
                'Rating': review['Rating'],
                'Comment': review.get('Comment') or '',
                'CreatedAt': created_at
            })
        
        return enriched_reviews
    
    def get_all_restaurants(self):
        """Get all restaurants for dropdowns with optimized query"""
        restaurant_id_field = self.get_restaurant_id_field(Config.RESTAURANTS_COLLECTION)
        restaurants = list(self.restaurants_collection.find(
            {}, 
            {'Name': 1, restaurant_id_field: 1}
        ).sort('Name', 1))
        
        # Filter out restaurants with None names
        return [restaurant for restaurant in restaurants if restaurant.get('Name') is not None]
    
    def test_connection(self):
        """Test the database connection and return status"""
        try:
            # Test basic connection
            self.client.admin.command('ping')
            
            # Test database access
            collections = self.db.list_collection_names()
            
            return {
                'status': 'success',
                'message': f'Connected to MiamiSpice database',
                'collections': collections
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'collections': []
            }
    
    def close(self):
        """Close the database connection"""
        self.client.close() 