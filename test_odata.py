import requests
import urllib3
import os
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv()

# Load from .env
HOST = os.getenv("S4H_HOST")
USER = os.getenv("S4H_USER")
PASSWORD = os.getenv("S4H_PASSWORD")

def test_ping():
    print("\n--- Test 1: Basic Connectivity ---")
    url = f"https://{HOST}:44300/sap/bc/ping"
    response = requests.get(url, auth=(USER, PASSWORD), verify=False)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ S/4HANA is reachable!")
    else:
        print("❌ Connection failed")

def test_odata():
    print("\n--- Test 2: OData Connectivity ---")
    url = f"https://{HOST}:44300/sap/opu/odata/sap/API_BUSINESS_PARTNER/$metadata"
    response = requests.get(url, auth=(USER, PASSWORD), verify=False)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ OData API working!")
    else:
        print(f"❌ OData failed: {response.text[:200]}")

def test_system_info():
    print("\n--- Test 3: System Information ---")
    url = f"https://{HOST}:44300/sap/opu/odata/sap/SBASIC/$metadata"
    response = requests.get(url, auth=(USER, PASSWORD), verify=False)
    print(f"Status: {response.status_code}")

if __name__ == "__main__":
    print(f"Connecting to S/4HANA: {HOST}")
    test_ping()
    test_odata()
    test_system_info()
    print("\n✅ Session 2 connectivity tests complete!")