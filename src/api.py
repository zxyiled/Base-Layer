import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_URL = os.getenv("DATASET_URL", "")

def get_data():
    print(f"Connecting to the API in: {API_URL}...")

    try:
        response = requests.get(API_URL)
        response.raise_for_status()

        data = response.json()
        print("Dataset loaded successfully.")
        return data

    except requests.exceptions.RequestException as e:
        print(f"Error to connect to the API: {e}")
        return None    

if __name__ == "__main__":
    print("Testing API connection...")
    my_dataset = get_data()

    if my_dataset:
        print("\n Dataset loaded successfully.")
        print(my_dataset[:2])
    else:
        print("\n Failed to load dataset.")
        
    
