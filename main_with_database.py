from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Optional
from database import SimpleDatabase

# Create FastAPI app
app = FastAPI(title="Shopify Store Insights with Database")

# Initialize database
db = SimpleDatabase()

# Simple data models
class Product(BaseModel):
    title: str
    price: str = ""
    image: str = ""
    handle: str = ""

class BrandInfo(BaseModel):
    website_url: str
    brand_name: str = ""
    products: List[Product] = []
    hero_products: List[Product] = []
    privacy_policy: str = ""
    return_policy: str = ""
    faqs: List[dict] = []
    social_links: List[dict] = []
    contact_info: dict = {}
    about_brand: str = ""
    important_links: List[dict] = []

class WebsiteRequest(BaseModel):
    website_url: str

class CompetitorAnalysis(BaseModel):
    main_brand: BrandInfo
    competitors: List[BrandInfo] = []

# All the scraping functions from the previous file
def get_page(url):
    """Get webpage content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Website not found")
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=401, detail="Website not found or not accessible")

def get_products(website_url):
    """Get products from /products.json"""
    products = []
    try:
        products_url = website_url.rstrip('/') + '/products.json'
        response = requests.get(products_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('products', []):
                price = ""
                image = ""
                
                if item.get('variants'):
                    price = f"${item['variants'][0].get('price', '0')}"
                
                if item.get('images'):
                    image = item['images'][0].get('src', '')
                
                product = Product(
                    title=item.get('title', ''),
                    price=price,
                    image=image,
                    handle=item.get('handle', '')
                )
                products.append(product)
    except:
        pass
    
    return products

def get_hero_products(soup, all_products):
    """Get hero products from homepage"""
    hero_products = []
    product_links = soup.find_all('a', href=True)
    
    for link in product_links[:10]:
        href = link.get('href', '')
        if '/products/' in href:
            handle = href.split('/')[-1]
            for product in all_products:
                if product.handle == handle:
                    hero_products.append(product)
                    break
    
    return hero_products[:6]

def get_social_links(soup):
    """Find social media links"""
    social_links = []
    social_sites = ['instagram', 'facebook', 'twitter', 'tiktok', 'youtube']
    
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '').lower()
        for site in social_sites:
            if site in href:
                social_links.append({
                    "platform": site.title(),
                    "url": link['href']
                })
                break
    
    return social_links

def get_contact_info(soup):
    """Get contact information"""
    text = soup.get_text()
    contact = {}
    
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        contact['emails'] = list(set(emails))
    
    phones = re.findall(r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phones:
        contact['phones'] = phones
    
    return contact

def find_policy_page(soup, website_url, policy_type):
    """Find and get policy content"""
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '').lower()
        text = link.get_text().lower()
        
        if policy_type in href or policy_type in text:
            try:
                if href.startswith('http'):
                    policy_url = href
                else:
                    policy_url = website_url.rstrip('/') + href
                
                policy_soup = get_page(policy_url)
                return policy_soup.get_text()[:500]  # First 500 characters
            except:
                continue
    
    return ""

def get_faqs(soup, website_url):
    """Get FAQs from the website"""
    faqs = []
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '').lower()
        text = link.get_text().lower()
        
        if 'faq' in href or 'faq' in text or 'help' in text:
            try:
                if href.startswith('http'):
                    faq_url = href
                else:
                    faq_url = website_url.rstrip('/') + href
                
                faq_soup = get_page(faq_url)
                
                questions = faq_soup.find_all(['h3', 'h4', 'h5'])
                for i, q in enumerate(questions[:5]):
                    question_text = q.get_text().strip()
                    answer_text = ""
                    
                    next_element = q.find_next(['p', 'div'])
                    if next_element:
                        answer_text = next_element.get_text().strip()[:200]
                    
                    if question_text and answer_text:
                        faqs.append({
                            "question": question_text,
                            "answer": answer_text
                        })
                
                break
            except:
                continue
    
    return faqs

def get_important_links(soup, website_url):
    """Get important links"""
    important_links = []
    important_words = ['track', 'contact', 'blog', 'about', 'support', 'shipping']
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '').lower()
        text = link.get_text().lower().strip()
        
        for word in important_words:
            if word in href or word in text:
                full_url = href if href.startswith('http') else website_url.rstrip('/') + href
                important_links.append({
                    "name": link.get_text().strip(),
                    "url": full_url
                })
                break
        
        if len(important_links) >= 8:
            break
    
    return important_links

def get_brand_info(soup):
    """Get brand name and about info"""
    brand_name = ""
    about_text = ""
    
    title = soup.find('title')
    if title:
        brand_name = title.get_text().split('-')[0].split('|')[0].strip()
    
    about_sections = soup.find_all(['div', 'section'], class_=re.compile(r'about|story|intro', re.I))
    for section in about_sections:
        text = section.get_text().strip()
        if len(text) > len(about_text) and len(text) < 300:
            about_text = text
    
    return brand_name, about_text

def scrape_website(website_url):
    """Main scraping function"""
    # Check if it's a Shopify store
    try:
        test_response = requests.get(website_url + '/products.json', timeout=5)
        if test_response.status_code != 200:
            main_page = requests.get(website_url, timeout=5)
            if 'shopify' not in main_page.text.lower():
                raise HTTPException(status_code=400, detail="This doesn't appear to be a Shopify store")
    except:
        raise HTTPException(status_code=401, detail="Website not found or not accessible")
    
    # Get main page
    soup = get_page(website_url)
    
    # Get all data
    brand_name, about_text = get_brand_info(soup)
    all_products = get_products(website_url)
    hero_products = get_hero_products(soup, all_products)
    social_links = get_social_links(soup)
    contact_info = get_contact_info(soup)
    privacy_policy = find_policy_page(soup, website_url, 'privacy')
    return_policy = find_policy_page(soup, website_url, 'return')
    faqs = get_faqs(soup, website_url)
    important_links = get_important_links(soup, website_url)
    
    # Create result
    result = BrandInfo(
        website_url=website_url,
        brand_name=brand_name,
        products=all_products,
        hero_products=hero_products,
        privacy_policy=privacy_policy,
        return_policy=return_policy,
        faqs=faqs,
        social_links=social_links,
        contact_info=contact_info,
        about_brand=about_text,
        important_links=important_links
    )
    
    return result

def find_competitors(brand_name):
    """Simple competitor finding using web search"""
    competitors = []
    
    if not brand_name:
        return competitors
    
    # Some common Shopify stores for demo
    demo_competitors = [
        "https://colourpop.com",
        "https://www.allbirds.com",
        "https://www.bombas.com"
    ]
    
    # Try to scrape 2 competitors
    for comp_url in demo_competitors[:2]:
        try:
            comp_data = scrape_website(comp_url)
            competitors.append(comp_data)
        except:
            continue  # Skip if scraping fails
    
    return competitors

# API Endpoints
@app.get("/")
def home():
    return {
        "message": "Shopify Store Insights API with Database",
        "endpoints": [
            "/insights - Get store insights",
            "/insights-with-db - Get insights and save to DB",
            "/competitor-analysis - Get competitor analysis",
            "/get-saved-data/{website_url} - Get saved data from DB"
        ]
    }

@app.post("/insights")
def get_insights(request: WebsiteRequest):
    """Get store insights without saving to database"""
    try:
        result = scrape_website(request.website_url)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/insights-with-db")
def get_insights_with_db(request: WebsiteRequest):
    """Get store insights and save to database"""
    try:
        # Scrape the website
        result = scrape_website(request.website_url)
        
        # Convert to dict for database
        data_dict = {
            'website_url': result.website_url,
            'brand_name': result.brand_name,
            'about_brand': result.about_brand,
            'privacy_policy': result.privacy_policy,
            'return_policy': result.return_policy,
            'contact_info': result.contact_info,
            'products': [p.dict() for p in result.products],
            'hero_products': [p.dict() for p in result.hero_products],
            'social_links': result.social_links,
            'faqs': result.faqs,
            'important_links': result.important_links
        }
        
        # Save to database
        brand_id = db.save_brand_data(data_dict)
        
        # Add database info to response
        result_dict = result.dict()
        result_dict['database_saved'] = True
        result_dict['brand_id'] = brand_id
        
        return result_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/competitor-analysis")
def get_competitor_analysis(request: WebsiteRequest):
    """BONUS: Get competitor analysis"""
    try:
        # Get main brand data
        main_brand = scrape_website(request.website_url)
        
        # Find competitors
        competitors = find_competitors(main_brand.brand_name)
        
        # Save all data to database
        all_brands = [main_brand] + competitors
        for brand in all_brands:
            data_dict = {
                'website_url': brand.website_url,
                'brand_name': brand.brand_name,
                'about_brand': brand.about_brand,
                'privacy_policy': brand.privacy_policy,
                'return_policy': brand.return_policy,
                'contact_info': brand.contact_info,
                'products': [p.dict() for p in brand.products],
                'hero_products': [p.dict() for p in brand.hero_products],
                'social_links': brand.social_links,
                'faqs': brand.faqs,
                'important_links': brand.important_links
            }
            db.save_brand_data(data_dict)
        
        result = CompetitorAnalysis(
            main_brand=main_brand,
            competitors=competitors
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/get-saved-data")
def get_saved_data(website_url: str):
    """Get saved data from database"""
    try:
        saved_data = db.get_brand_data(website_url)
        
        if not saved_data:
            raise HTTPException(status_code=404, detail="No data found for this website")
        
        return {
            "message": "Data retrieved from database",
            "data": saved_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    try:
        db.create_tables()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """Close database connection on shutdown"""
    try:
        db.close()
        print("✅ Database connection closed!")
    except Exception as e:
        print(f"❌ Error closing database: {e}")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)