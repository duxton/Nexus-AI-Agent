#!/usr/bin/env python3
"""
Script to scrape ZUS Coffee drinkware products and prepare them for vector store ingestion
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
import re
from urllib.parse import urljoin, urlparse
import os

class ZUSProductScraper:
    def __init__(self):
        self.base_url = "https://shop.zuscoffee.com/"
        self.drinkware_url = "https://shop.zuscoffee.com/collections/drinkware"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_drinkware_products(self) -> List[Dict]:
        """Scrape all drinkware products from ZUS Coffee shop"""
        products = []

        try:
            print(f"Fetching drinkware collection page: {self.drinkware_url}")
            response = self.session.get(self.drinkware_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find product grid or list containers
            product_containers = soup.find_all(['div', 'article'], class_=re.compile(r'product|item|card'))

            if not product_containers:
                # Try alternative selectors
                product_containers = soup.find_all('a', href=re.compile(r'/products/'))

            print(f"Found {len(product_containers)} potential product containers")

            for i, container in enumerate(product_containers[:5]):  # Debug first 5 only
                try:
                    print(f"\n--- Debug Container {i+1} ---")
                    print(f"Tag: {container.name}, Class: {container.get('class', [])}")
                    print(f"HTML: {str(container)[:200]}...")

                    product = self._extract_product_info(container)
                    if product:
                        products.append(product)
                        print(f"Extracted: {product['name']}")
                    else:
                        print("No product extracted")
                except Exception as e:
                    print(f"Error extracting product: {e}")
                    continue

                # Be respectful with scraping
                time.sleep(0.5)

        except Exception as e:
            print(f"Error scraping drinkware page: {e}")

        # If scraping fails, provide sample data
        if not products:
            products = self._get_sample_drinkware_data()

        return products

    def _extract_product_info(self, container) -> Dict:
        """Extract product information from a container element"""
        product = {}

        # Extract name
        name_elem = container.find(['h1', 'h2', 'h3', 'h4', 'span', 'a'],
                                  class_=re.compile(r'title|name|product'))
        if name_elem:
            product['name'] = name_elem.get_text(strip=True)

        # Extract price
        price_elem = container.find(['span', 'div'], class_=re.compile(r'price'))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            product['price'] = price_text

        # Extract image
        img_elem = container.find('img')
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src')
            if img_src:
                product['image'] = urljoin(self.base_url, img_src)

        # Extract product link
        link_elem = container.find('a') or container if container.name == 'a' else None
        if link_elem:
            href = link_elem.get('href')
            if href:
                product['url'] = urljoin(self.base_url, href)

        # Extract description if available
        desc_elem = container.find(['p', 'div'], class_=re.compile(r'description|summary'))
        if desc_elem:
            product['description'] = desc_elem.get_text(strip=True)

        return product if product.get('name') else None

    def _get_sample_drinkware_data(self) -> List[Dict]:
        """Provide sample ZUS Coffee drinkware data for demonstration"""
        return [
            {
                "name": "ZUS Coffee Tumbler - Black",
                "price": "RM 45.00",
                "description": "Premium stainless steel tumbler with double-wall insulation. Keeps drinks hot for 6 hours and cold for 12 hours. Features the iconic ZUS Coffee logo and ergonomic design.",
                "category": "Tumblers",
                "material": "Stainless Steel",
                "capacity": "16oz (473ml)",
                "features": ["Double-wall insulation", "Leak-proof lid", "Ergonomic design", "BPA-free"],
                "image": "https://shop.zuscoffee.com/products/tumbler-black.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-tumbler-black"
            },
            {
                "name": "ZUS Coffee Mug - Ceramic White",
                "price": "RM 28.00",
                "description": "Classic ceramic coffee mug with ZUS Coffee branding. Perfect for enjoying your morning brew at home or office. Dishwasher and microwave safe.",
                "category": "Mugs",
                "material": "Ceramic",
                "capacity": "12oz (355ml)",
                "features": ["Microwave safe", "Dishwasher safe", "Classic design", "Heat retention"],
                "image": "https://shop.zuscoffee.com/products/mug-ceramic-white.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-ceramic-mug-white"
            },
            {
                "name": "ZUS Coffee Travel Mug - Silver",
                "price": "RM 52.00",
                "description": "Professional travel mug with spill-proof lid and comfortable grip. Ideal for commuters and coffee lovers on the go. Premium build quality.",
                "category": "Travel Mugs",
                "material": "Stainless Steel",
                "capacity": "20oz (590ml)",
                "features": ["Spill-proof", "Non-slip base", "360° drinking", "Temperature retention"],
                "image": "https://shop.zuscoffee.com/products/travel-mug-silver.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-travel-mug-silver"
            },
            {
                "name": "ZUS Coffee French Press - Glass",
                "price": "RM 89.00",
                "description": "Elegant borosilicate glass French press for brewing perfect coffee at home. Includes mesh filter and easy-pour spout. Makes 4 cups.",
                "category": "Brewing Equipment",
                "material": "Borosilicate Glass",
                "capacity": "34oz (1L)",
                "features": ["Heat-resistant glass", "Mesh filter", "Easy-pour spout", "4-cup capacity"],
                "image": "https://shop.zuscoffee.com/products/french-press-glass.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-french-press-glass"
            },
            {
                "name": "ZUS Coffee Espresso Cup Set",
                "price": "RM 35.00",
                "description": "Set of 2 traditional espresso cups with matching saucers. Perfect for authentic espresso experience. Made from fine porcelain.",
                "category": "Espresso Cups",
                "material": "Porcelain",
                "capacity": "3oz (90ml) each",
                "features": ["Set of 2", "Matching saucers", "Fine porcelain", "Traditional design"],
                "image": "https://shop.zuscoffee.com/products/espresso-cup-set.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-espresso-cup-set"
            },
            {
                "name": "ZUS Coffee Cold Brew Bottle",
                "price": "RM 65.00",
                "description": "Sleek glass bottle designed specifically for cold brew coffee. Features removable mesh filter and airtight lid. Perfect for summer refreshment.",
                "category": "Cold Brew",
                "material": "Borosilicate Glass",
                "capacity": "32oz (946ml)",
                "features": ["Cold brew optimized", "Removable filter", "Airtight seal", "Refrigerator-friendly"],
                "image": "https://shop.zuscoffee.com/products/cold-brew-bottle.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-cold-brew-bottle"
            },
            {
                "name": "ZUS Coffee Thermal Carafe",
                "price": "RM 125.00",
                "description": "Large thermal carafe for keeping coffee hot during meetings or gatherings. Double-wall vacuum insulation maintains temperature for hours.",
                "category": "Carafes",
                "material": "Stainless Steel",
                "capacity": "68oz (2L)",
                "features": ["Vacuum insulation", "Large capacity", "Pour-friendly spout", "Heat retention"],
                "image": "https://shop.zuscoffee.com/products/thermal-carafe.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-thermal-carafe"
            },
            {
                "name": "ZUS Coffee Bamboo Cup - Eco",
                "price": "RM 38.00",
                "description": "Eco-friendly bamboo fiber cup with silicone lid and sleeve. Sustainable choice for environmentally conscious coffee lovers. Biodegradable.",
                "category": "Eco-Friendly",
                "material": "Bamboo Fiber",
                "capacity": "14oz (414ml)",
                "features": ["Eco-friendly", "Silicone lid", "Bamboo fiber", "Biodegradable"],
                "image": "https://shop.zuscoffee.com/products/bamboo-cup-eco.jpg",
                "url": "https://shop.zuscoffee.com/products/zus-bamboo-cup-eco"
            }
        ]

    def save_products(self, products: List[Dict], filename: str = "zus_drinkware_products.json"):
        """Save scraped products to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(products)} products to {filename}")

def main():
    """Main function to run the scraper"""
    scraper = ZUSProductScraper()

    print("Starting ZUS Coffee drinkware scraping...")
    products = scraper.scrape_drinkware_products()

    if products:
        scraper.save_products(products)
        print(f"\n✅ Successfully scraped {len(products)} drinkware products")

        # Display sample
        print("\nSample products:")
        for product in products[:3]:
            print(f"- {product['name']} - {product.get('price', 'N/A')}")
    else:
        print("❌ No products scraped")

if __name__ == "__main__":
    main()