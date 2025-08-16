import requests
import json

# Test the API
def test_api():
    # API endpoint
    url = "http://localhost:8000/insights"
    
    # Test websites
    test_sites = [
        "https://memy.co.in",
        "https://hairoriginals.com"
    ]
    
    for site in test_sites:
        print(f"\n🧪 Testing: {site}")
        print("=" * 50)
        
        try:
            # Make API call
            response = requests.post(url, json={"website_url": site})
            
            if response.status_code == 200:
                data = response.json()
                
                # Print results
                print(f"✅ Brand Name: {data.get('brand_name', 'N/A')}")
                print(f"📦 Total Products: {len(data.get('products', []))}")
                print(f"⭐ Hero Products: {len(data.get('hero_products', []))}")
                print(f"📞 Contact Emails: {len(data.get('contact_info', {}).get('emails', []))}")
                print(f"📱 Social Links: {len(data.get('social_links', []))}")
                print(f"❓ FAQs: {len(data.get('faqs', []))}")
                print(f"🔗 Important Links: {len(data.get('important_links', []))}")
                
                # Show some products
                if data.get('products'):
                    print("\n📦 First 3 Products:")
                    for i, product in enumerate(data['products'][:3]):
                        print(f"  {i+1}. {product.get('title', 'N/A')} - {product.get('price', 'N/A')}")
                
                # Show social links
                if data.get('social_links'):
                    print("\n📱 Social Links:")
                    for social in data['social_links']:
                        print(f"  {social.get('platform', 'N/A')}: {social.get('url', 'N/A')}")
                
                print("\n✅ SUCCESS!")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Message: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting API Tests...")
    test_api()
    print("\n🏁 Tests completed!")