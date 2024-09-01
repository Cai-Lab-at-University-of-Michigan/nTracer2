from time import time
import functools
import asyncio
def print_time(tag: str):
    def decorator(func):
        @functools.wraps(func)
        def time_wrapper(*args, **kwargs):
            start_time = time()
            result = func(*args, **kwargs)
            end_time = time()
            print(f'[{tag}] {func.__name__}: {end_time - start_time:.4f}s')
            return result
    
        @functools.wraps(func)
        async def async_time_wrapper(*args, **kwargs):
            start_time = time()
            result = await func(*args, **kwargs)
            end_time = time()
            print(f'[{tag}] {func.__name__}: {end_time - start_time:.4f}s')
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_time_wrapper
        else:
            return time_wrapper
    
    return decorator
