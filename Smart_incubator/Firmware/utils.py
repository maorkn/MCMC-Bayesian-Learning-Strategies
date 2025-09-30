# utils.py - Utility Functions
import urandom
import json

def generate_random_interval(min_min, max_min):
    """Generates a random interval (minutes) between min_min and max_min."""
    return urandom.randint(min_min, max_min)

def save_json(data, filename):
    """Save data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")
        return False 