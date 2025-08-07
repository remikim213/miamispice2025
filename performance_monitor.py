import time
import functools
from typing import Dict, List, Any
import logging

class PerformanceMonitor:
    """Monitor and track database query performance"""
    
    def __init__(self):
        self.query_times = {}
        self.total_queries = 0
        self.slow_queries = []  # Queries taking > 100ms
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def monitor_query(self, query_name: str):
        """Decorator to monitor query execution time"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Track performance
                    self._record_query_time(query_name, execution_time)
                    
                    # Log slow queries
                    if execution_time > 0.1:  # 100ms threshold
                        self.slow_queries.append({
                            'query': query_name,
                            'time': execution_time,
                            'timestamp': time.time()
                        })
                        self.logger.warning(f"Slow query detected: {query_name} took {execution_time:.3f}s")
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._record_query_time(query_name, execution_time, error=True)
                    self.logger.error(f"Query {query_name} failed after {execution_time:.3f}s: {str(e)}")
                    raise
            return wrapper
        return decorator
    
    def _record_query_time(self, query_name: str, execution_time: float, error: bool = False):
        """Record query execution time"""
        if query_name not in self.query_times:
            self.query_times[query_name] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'errors': 0
            }
        
        stats = self.query_times[query_name]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], execution_time)
        stats['max_time'] = max(stats['max_time'], execution_time)
        
        if error:
            stats['errors'] += 1
        
        self.total_queries += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of query performance"""
        if not self.query_times:
            return {"message": "No queries recorded yet"}
        
        summary = {
            'total_queries': self.total_queries,
            'slow_queries_count': len(self.slow_queries),
            'query_stats': {}
        }
        
        for query_name, stats in self.query_times.items():
            summary['query_stats'][query_name] = {
                'count': stats['count'],
                'avg_time_ms': round(stats['avg_time'] * 1000, 2),
                'min_time_ms': round(stats['min_time'] * 1000, 2),
                'max_time_ms': round(stats['max_time'] * 1000, 2),
                'total_time_ms': round(stats['total_time'] * 1000, 2),
                'error_rate': round(stats['errors'] / stats['count'] * 100, 2) if stats['count'] > 0 else 0
            }
        
        return summary
    
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get list of slow queries"""
        return self.slow_queries.copy()
    
    def reset_stats(self):
        """Reset all performance statistics"""
        self.query_times = {}
        self.total_queries = 0
        self.slow_queries = []
    
    def print_summary(self):
        """Print a formatted performance summary"""
        summary = self.get_performance_summary()
        
        if "message" in summary:
            print(summary["message"])
            return
        
        print("\n" + "="*60)
        print("DATABASE PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Queries: {summary['total_queries']}")
        print(f"Slow Queries (>100ms): {summary['slow_queries_count']}")
        print("\nQuery Statistics:")
        print("-" * 60)
        
        for query_name, stats in summary['query_stats'].items():
            print(f"\n{query_name}:")
            print(f"  Count: {stats['count']}")
            print(f"  Avg Time: {stats['avg_time_ms']}ms")
            print(f"  Min Time: {stats['min_time_ms']}ms")
            print(f"  Max Time: {stats['max_time_ms']}ms")
            print(f"  Total Time: {stats['total_time_ms']}ms")
            print(f"  Error Rate: {stats['error_rate']}%")
        
        if summary['slow_queries_count'] > 0:
            print(f"\nRecent Slow Queries:")
            print("-" * 30)
            for query in self.slow_queries[-5:]:  # Show last 5 slow queries
                print(f"  {query['query']}: {query['time']:.3f}s")
        
        print("="*60)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()