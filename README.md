# Miami Spice 2025

A Streamlit application for exploring and reviewing restaurants participating in Miami Spice 2025.

## 🏗️ Architecture

The application has been refactored with a modular architecture:

### Core Modules

- **`app.py`** - Main application entry point
- **`config.py`** - Configuration management and environment variables
- **`database.py`** - MongoDB database operations and connection management
- **`ui_components.py`** - Streamlit UI components and interface logic

### Security

- All secrets are managed through environment variables
- Database credentials are stored in `.env` file (not committed to version control) or `secrets.toml`
- Configuration is centralized in `config.py`

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `secrets.toml` file in the root directory with your MongoDB credentials:

```secrets.toml
[mongo]
host = "miamispice.xxxxxxxx.mongodb.net"
username = "xxx"
password = "xxx"
```

### 3. Run the Application

```bash
streamlit run app.py
```

## 📁 Project Structure

```
miamispice2025/
├── app.py                 # Main application
├── config.py             # Configuration management
├── database.py           # Database operations
├── ui_components.py      # UI components
├── performance_monitor.py # Performance monitoring
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🔧 Features

- **Restaurant Browsing**: Search and filter restaurants by name, cuisine, location, day, time, and user reviews
- **Review System**: Submit and view restaurant reviews with ratings
- **User Reviews**: View all reviews submitted by a specific user
- **Responsive Design**: Clean, modern interface with sidebar navigation

## 🛡️ Security Improvements

- ✅ Secrets moved to environment variables
- ✅ Database connection centralized
- ✅ Configuration separated from business logic
- ✅ Modular architecture for better maintainability
- ✅ Proper error handling and validation

## 🔄 Refactoring Benefits

1. **Separation of Concerns**: Database logic, UI components, and configuration are now separate
2. **Maintainability**: Code is more modular and easier to maintain
3. **Security**: All secrets are properly managed through environment variables
4. **Reusability**: UI components can be reused across different pages
5. **Testability**: Each module can be tested independently

## ⚡ Performance Optimizations

### Time Complexity Improvements

The database operations have been optimized for better performance:

- **Aggregation Pipelines**: Reduced multiple queries to single aggregation operations
- **Strategic Indexing**: Created indexes on frequently queried fields
- **Intelligent Caching**: Implemented 5-minute cache for filter data
- **Set-Based Filtering**: Eliminated N+1 query problems using batch operations
- **Performance Monitoring**: Added query execution time tracking

### Key Optimizations

1. **Filter Data Retrieval**: O(5n) → O(n) - 5x faster
2. **Restaurant Search**: O(n*m) → O(n + m) - Linear vs Quadratic complexity
3. **User Reviews**: O(n*m) → O(n) - Eliminated N+1 queries
4. **Cached Operations**: O(n) → O(1) - Constant time for repeated requests

## 📝 Usage

1. **Browse Restaurants**: Use the search form to filter restaurants by various criteria
2. **Submit Reviews**: Leave reviews for restaurants you've visited
3. **View Reviews**: See all reviews for a specific restaurant or your own reviews
