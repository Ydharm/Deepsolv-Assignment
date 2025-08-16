import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'shopify_insights',
    'user': 'root',
    'password': 'password'  # Change this to your MySQL password
}

class SimpleDatabase:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            print("✅ Connected to MySQL database")
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
    
    def create_tables(self):
        """Create necessary tables"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        
        # Create brands table
        brands_table = """
        CREATE TABLE IF NOT EXISTS brands (
            id INT AUTO_INCREMENT PRIMARY KEY,
            website_url VARCHAR(500) UNIQUE NOT NULL,
            brand_name VARCHAR(200),
            about_brand TEXT,
            privacy_policy TEXT,
            return_policy TEXT,
            contact_info JSON,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Create products table
        products_table = """
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand_id INT,
            title VARCHAR(500),
            price VARCHAR(50),
            image_url TEXT,
            handle VARCHAR(200),
            is_hero_product BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
        """
        
        # Create social_links table
        social_table = """
        CREATE TABLE IF NOT EXISTS social_links (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand_id INT,
            platform VARCHAR(50),
            url VARCHAR(500),
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
        """
        
        # Create faqs table
        faqs_table = """
        CREATE TABLE IF NOT EXISTS faqs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand_id INT,
            question TEXT,
            answer TEXT,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
        """
        
        # Create important_links table
        links_table = """
        CREATE TABLE IF NOT EXISTS important_links (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand_id INT,
            name VARCHAR(200),
            url VARCHAR(500),
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
        """
        
        try:
            cursor.execute(brands_table)
            cursor.execute(products_table)
            cursor.execute(social_table)
            cursor.execute(faqs_table)
            cursor.execute(links_table)
            
            self.connection.commit()
            print("✅ Database tables created successfully!")
            
        except Error as e:
            print(f"❌ Error creating tables: {e}")
        
        cursor.close()
    
    def save_brand_data(self, brand_data):
        """Save complete brand data to database"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Insert or update brand
            brand_query = """
            INSERT INTO brands (website_url, brand_name, about_brand, privacy_policy, return_policy, contact_info)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            brand_name = VALUES(brand_name),
            about_brand = VALUES(about_brand),
            privacy_policy = VALUES(privacy_policy),
            return_policy = VALUES(return_policy),
            contact_info = VALUES(contact_info)
            """
            
            brand_values = (
                brand_data['website_url'],
                brand_data['brand_name'],
                brand_data['about_brand'],
                brand_data['privacy_policy'],
                brand_data['return_policy'],
                json.dumps(brand_data['contact_info'])
            )
            
            cursor.execute(brand_query, brand_values)
            
            # Get brand ID
            cursor.execute("SELECT id FROM brands WHERE website_url = %s", (brand_data['website_url'],))
            brand_id = cursor.fetchone()[0]
            
            # Clear existing data for this brand
            cursor.execute("DELETE FROM products WHERE brand_id = %s", (brand_id,))
            cursor.execute("DELETE FROM social_links WHERE brand_id = %s", (brand_id,))
            cursor.execute("DELETE FROM faqs WHERE brand_id = %s", (brand_id,))
            cursor.execute("DELETE FROM important_links WHERE brand_id = %s", (brand_id,))
            
            # Insert products
            for product in brand_data['products']:
                product_query = """
                INSERT INTO products (brand_id, title, price, image_url, handle, is_hero_product)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                is_hero = any(hero.get('handle') == product.get('handle') for hero in brand_data['hero_products'])
                
                product_values = (
                    brand_id,
                    product.get('title'),
                    product.get('price'),
                    product.get('image'),
                    product.get('handle'),
                    is_hero
                )
                
                cursor.execute(product_query, product_values)
            
            # Insert social links
            for social in brand_data['social_links']:
                social_query = """
                INSERT INTO social_links (brand_id, platform, url)
                VALUES (%s, %s, %s)
                """
                
                social_values = (
                    brand_id,
                    social.get('platform'),
                    social.get('url')
                )
                
                cursor.execute(social_query, social_values)
            
            # Insert FAQs
            for faq in brand_data['faqs']:
                faq_query = """
                INSERT INTO faqs (brand_id, question, answer)
                VALUES (%s, %s, %s)
                """
                
                faq_values = (
                    brand_id,
                    faq.get('question'),
                    faq.get('answer')
                )
                
                cursor.execute(faq_query, faq_values)
            
            # Insert important links
            for link in brand_data['important_links']:
                link_query = """
                INSERT INTO important_links (brand_id, name, url)
                VALUES (%s, %s, %s)
                """
                
                link_values = (
                    brand_id,
                    link.get('name'),
                    link.get('url')
                )
                
                cursor.execute(link_query, link_values)
            
            self.connection.commit()
            print(f"✅ Successfully saved data for brand: {brand_data['brand_name']}")
            return brand_id
            
        except Error as e:
            print(f"❌ Error saving brand data: {e}")
            self.connection.rollback()
            return None
        
        cursor.close()
    
    def get_brand_data(self, website_url):
        """Get brand data from database"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            # Get brand info
            cursor.execute("SELECT * FROM brands WHERE website_url = %s", (website_url,))
            brand = cursor.fetchone()
            
            if not brand:
                return None
            
            brand_id = brand['id']
            
            # Get products
            cursor.execute("SELECT * FROM products WHERE brand_id = %s", (brand_id,))
            products = cursor.fetchall()
            
            # Get social links
            cursor.execute("SELECT * FROM social_links WHERE brand_id = %s", (brand_id,))
            social_links = cursor.fetchall()
            
            # Get FAQs
            cursor.execute("SELECT * FROM faqs WHERE brand_id = %s", (brand_id,))
            faqs = cursor.fetchall()
            
            # Get important links
            cursor.execute("SELECT * FROM important_links WHERE brand_id = %s", (brand_id,))
            important_links = cursor.fetchall()
            
            # Combine all data
            result = {
                'brand': brand,
                'products': products,
                'social_links': social_links,
                'faqs': faqs,
                'important_links': important_links
            }
            
            return result
            
        except Error as e:
            print(f"❌ Error retrieving brand data: {e}")
            return None
        
        cursor.close()
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ MySQL connection closed")

# Example usage
if __name__ == "__main__":
    db = SimpleDatabase()
    db.create_tables()
    
    # Test data
    test_data = {
        'website_url': 'https://example.com',
        'brand_name': 'Test Brand',
        'about_brand': 'This is a test brand',
        'privacy_policy': 'Test privacy policy',
        'return_policy': 'Test return policy',
        'contact_info': {'emails': ['test@example.com']},
        'products': [
            {'title': 'Test Product', 'price': '$10', 'image': '', 'handle': 'test-product'}
        ],
        'hero_products': [],
        'social_links': [
            {'platform': 'Instagram', 'url': 'https://instagram.com/test'}
        ],
        'faqs': [
            {'question': 'Test question?', 'answer': 'Test answer'}
        ],
        'important_links': [
            {'name': 'Contact Us', 'url': 'https://example.com/contact'}
        ]
    }
    
    # Save test data
    brand_id = db.save_brand_data(test_data)
    print(f"Saved brand with ID: {brand_id}")
    
    db.close()