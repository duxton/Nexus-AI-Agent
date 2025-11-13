#!/usr/bin/env python3
"""
Product Knowledge Base with Vector Store for ZUS Coffee drinkware
Implements RAG (Retrieval-Augmented Generation) for product queries
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import pickle

load_dotenv()

class ProductVectorStore:
    """Vector store for product embeddings using FAISS"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        self.index = None
        self.products = []
        self.product_texts = []

    def create_product_text(self, product: Dict) -> str:
        """Create searchable text representation of a product"""
        text_parts = []

        # Basic info
        text_parts.append(f"Product: {product['name']}")

        if 'price' in product:
            text_parts.append(f"Price: {product['price']}")

        if 'category' in product:
            text_parts.append(f"Category: {product['category']}")

        if 'material' in product:
            text_parts.append(f"Material: {product['material']}")

        if 'capacity' in product:
            text_parts.append(f"Capacity: {product['capacity']}")

        # Description
        if 'description' in product:
            text_parts.append(f"Description: {product['description']}")

        # Features
        if 'features' in product and product['features']:
            features_text = ", ".join(product['features'])
            text_parts.append(f"Features: {features_text}")

        return " | ".join(text_parts)

    def ingest_products(self, products: List[Dict]) -> None:
        """Ingest products into vector store"""
        print(f"Ingesting {len(products)} products into vector store...")

        self.products = products
        self.product_texts = [self.create_product_text(product) for product in products]

        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(
            self.product_texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Create FAISS index
        print("Creating FAISS index...")
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for similarity

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype(np.float32))

        print(f"✅ Vector store created with {self.index.ntotal} products")

    def search(self, query: str, k: int = 5) -> List[Tuple[Dict, float]]:
        """Search for similar products"""
        if self.index is None:
            return []

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)

        # Return results with scores
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
            if idx >= 0:  # Valid index
                results.append((self.products[idx], float(score)))

        return results

    def save(self, filepath: str) -> None:
        """Save vector store to disk"""
        data = {
            'products': self.products,
            'product_texts': self.product_texts,
            'embedding_dim': self.embedding_dim
        }

        with open(f"{filepath}.pkl", 'wb') as f:
            pickle.dump(data, f)

        if self.index:
            faiss.write_index(self.index, f"{filepath}.faiss")

        print(f"✅ Vector store saved to {filepath}")

    def load(self, filepath: str) -> bool:
        """Load vector store from disk"""
        try:
            with open(f"{filepath}.pkl", 'rb') as f:
                data = pickle.load(f)

            self.products = data['products']
            self.product_texts = data['product_texts']
            self.embedding_dim = data['embedding_dim']

            if os.path.exists(f"{filepath}.faiss"):
                self.index = faiss.read_index(f"{filepath}.faiss")
                print(f"✅ Vector store loaded from {filepath}")
                return True

        except Exception as e:
            print(f"❌ Failed to load vector store: {e}")

        return False


class ProductKnowledgeBase:
    """RAG system for product knowledge base"""

    def __init__(self):
        self.vector_store = ProductVectorStore()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def initialize(self, force_rebuild: bool = False) -> bool:
        """Initialize the knowledge base"""
        vector_store_path = "data/product_vector_store"

        # Try to load existing vector store
        if not force_rebuild and self.vector_store.load(vector_store_path):
            return True

        # Build new vector store
        print("Building new product knowledge base...")

        # Load or scrape products
        products = self._load_products()
        if not products:
            print("❌ No products available for indexing")
            return False

        # Create vector store
        self.vector_store.ingest_products(products)

        # Save vector store
        os.makedirs("data", exist_ok=True)
        self.vector_store.save(vector_store_path)

        return True

    def _load_products(self) -> List[Dict]:
        """Load products from JSON file or scraping"""
        # Try to load from JSON
        json_file = "zus_drinkware_products.json"
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Fallback to scraping
        print("JSON file not found, running scraper...")
        from scrape_zus_products import ZUSProductScraper
        scraper = ZUSProductScraper()
        products = scraper.scrape_drinkware_products()
        scraper.save_products(products, json_file)
        return products

    def query(self, user_query: str, max_results: int = 5) -> Dict:
        """Query the product knowledge base"""
        try:
            # Search for relevant products
            results = self.vector_store.search(user_query, k=max_results)

            if not results:
                return {
                    "answer": "I couldn't find any relevant products for your query.",
                    "products": [],
                    "sources": []
                }

            # Prepare context for LLM
            context_products = []
            for product, score in results:
                context_products.append({
                    "name": product["name"],
                    "price": product.get("price", "N/A"),
                    "description": product.get("description", ""),
                    "features": product.get("features", []),
                    "material": product.get("material", ""),
                    "capacity": product.get("capacity", ""),
                    "category": product.get("category", ""),
                    "relevance_score": score
                })

            # Generate answer using LLM
            answer = self._generate_answer(user_query, context_products)

            return {
                "answer": answer,
                "products": context_products[:3],  # Top 3 most relevant
                "sources": [p["name"] for p in context_products[:3]],
                "total_found": len(results)
            }

        except Exception as e:
            return {
                "answer": f"I encountered an error while searching: {str(e)}",
                "products": [],
                "sources": [],
                "error": str(e)
            }

    def _generate_answer(self, query: str, products: List[Dict]) -> str:
        """Generate answer using OpenAI with retrieved products as context"""
        try:
            # Prepare context
            context = "Based on ZUS Coffee's drinkware collection, here are the relevant products:\n\n"

            for i, product in enumerate(products[:3], 1):
                context += f"{i}. {product['name']} - {product['price']}\n"
                context += f"   Description: {product['description']}\n"

                if product['features']:
                    context += f"   Features: {', '.join(product['features'])}\n"

                if product['material']:
                    context += f"   Material: {product['material']}\n"

                if product['capacity']:
                    context += f"   Capacity: {product['capacity']}\n"

                context += "\n"

            # Create prompt
            prompt = f"""You are a helpful ZUS Coffee product expert. Use the provided product information to answer the customer's question about drinkware products.

Product Information:
{context}

Customer Question: {query}

Please provide a helpful, accurate response based on the product information. If recommending products, explain why they match the customer's needs. Be friendly and informative.

Response:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable ZUS Coffee product specialist helping customers find the perfect drinkware."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"I found relevant products but couldn't generate a detailed response: {str(e)}"


# Global instance
product_kb = ProductKnowledgeBase()


def main():
    """Test the product knowledge base"""
    print("🔍 Testing Product Knowledge Base")

    # Initialize
    if product_kb.initialize():
        print("✅ Product KB initialized successfully")

        # Test queries
        test_queries = [
            "I need a travel mug for my commute",
            "What ceramic mugs do you have?",
            "Show me eco-friendly options",
            "I want something for cold brew",
            "What's the most expensive product?",
            "Do you have anything made of bamboo?"
        ]

        for query in test_queries:
            print(f"\n❓ Query: {query}")
            result = product_kb.query(query)
            print(f"💬 Answer: {result['answer']}")
            print(f"📦 Found {result.get('total_found', 0)} products")

    else:
        print("❌ Failed to initialize product KB")


if __name__ == "__main__":
    main()