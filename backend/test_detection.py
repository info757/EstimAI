#!/usr/bin/env python3
"""Test script for the detection endpoint."""
import requests
import json

def test_detection():
    """Test the detection endpoint."""
    base_url = "http://localhost:8000"
    
    # Test parameters
    file = "280-utility-construction-plans.pdf"
    page = 6  # 0-based
    points_per_foot = 50.0
    
    print(f"Testing detection for {file}, page {page + 1}")
    
    try:
        # Make request to detection endpoint
        response = requests.post(
            f"{base_url}/api/v1/detect",
            params={
                "file": file,
                "page": page,
                "points_per_foot": points_per_foot
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Detection successful!")
            print(f"File: {data['file']}")
            print(f"Page: {data['page']}")
            print(f"Points per foot: {data['points_per_foot']}")
            print(f"Total detections: {len(data['counts'])}")
            print(f"Totals: {data['totals']}")
            print(f"Review session ID: {data['review_session_id']}")
            
            print("\nDetected items:")
            for i, item in enumerate(data['counts'], 1):
                print(f"  {i}. {item['type']} at ({item['x_pdf']:.1f}, {item['y_pdf']:.1f}) "
                      f"confidence={item['confidence']:.2f}")
        else:
            print(f"❌ Detection failed: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_detection()
