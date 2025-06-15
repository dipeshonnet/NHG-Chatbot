import os
import hashlib
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any

import pandas as pd
import chainlit as cl
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.prompts import PromptTemplate
from llama_index.readers.file import PDFReader, ImageReader

class Config:
    """Configuration constants for the application."""
    
    # Model settings
    LLM_MODEL = "gpt-4-turbo-preview"
    EMBEDDING_MODEL = "text-embedding-3-small"
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 1024
    
    # Index settings
    CHUNK_SIZE = 2048
    CHUNK_OVERLAP = 200
    SIMILARITY_TOP_K = 3
    
    # Directories
    DATA_DIR = "./data"
    STORAGE_DIR = "./storage"
    
    # File limits
    MAX_TITLE_LENGTH = 100
    MAX_FIELD_LENGTH = 50
    MAX_URL_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 75
    MAX_PRODUCTS_DISPLAYED = 2
    
    # Keywords for product recommendations
    HEALTH_KEYWORDS = [
        "test", "testing", "consultation", "consult", "supplement", "treatment",
        "product", "buy", "purchase", "order", "price", "cost", "available",
        "vitamin", "mineral", "herb", "natural", "organic", "health", "wellness",
        "therapy", "analysis", "screening", "assessment", "recommendation"
    ]

    # Copilot configuration
    COPILOT_CONFIG = {
        "allowed_origins": ["https://www.naturalhealthgroup.com.au"],
        "theme": {
            "primary_color": "#2E8B57",  # Sea Green for health theme
            "font_family": "Arial, sans-serif",
            "button_color": "#228B22",
            "header_background": "#F0F8F0"
        },
        "position": "bottom-right",
        "size": "medium",
        "greeting_message": "Hi! I'm Zoe, your natural health assistant. How can I help you today?",
        "placeholder": "Ask me about health products, consultations, or wellness advice...",
        "max_history": 50
    }

class FileManager:
    """Handles file operations and metadata management."""
    
    @staticmethod
    def get_file_hash(file_path: str) -> Optional[str]:
        """Calculate MD5 hash of a file to detect changes."""
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    @staticmethod
    def save_file_metadata(data_dir: str, storage_dir: str) -> Dict[str, Any]:
        """Save metadata about processed files."""
        metadata = {}
        metadata_file = os.path.join(storage_dir, "file_metadata.json")
        
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                metadata[filename] = {
                    'hash': FileManager.get_file_hash(file_path),
                    'modified': os.path.getmtime(file_path),
                    'processed_at': datetime.now().isoformat()
                }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    @staticmethod
    def check_files_changed(data_dir: str, storage_dir: str) -> bool:
        """Check if any files have changed since last processing."""
        metadata_file = os.path.join(storage_dir, "file_metadata.json")
        
        if not os.path.exists(metadata_file):
            return True
        
        try:
            with open(metadata_file, 'r') as f:
                old_metadata = json.load(f)
        except Exception:
            return True
        
        current_files = set(os.listdir(data_dir))
        old_files = set(old_metadata.keys())
        
        # Check for added/removed files
        if current_files != old_files:
            print("Files changed: Added/Removed files detected")
            return True
        
        # Check for modified files
        for filename in current_files:
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                current_hash = FileManager.get_file_hash(file_path)
                old_hash = old_metadata.get(filename, {}).get('hash')
                
                if current_hash != old_hash:
                    print(f"File changed: {filename}")
                    return True
        
        return False


class DocumentLoader:
    """Handles loading and processing of different document types."""
    
    @staticmethod
    def load_from_txt(file_path: str) -> List[Document]:
        """Load data from a text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return [Document(text=text)]
    
    @staticmethod
    def load_from_csv(file_path: str) -> List[Document]:
        """Load data from a CSV file and create product documents."""
        documents = []
        
        try:
            print(f"Processing CSV file: {file_path}")
            df = pd.read_csv(file_path)
            processed_count = 0
            
            for idx, row in df.iterrows():
                # Skip invalid products
                if pd.isna(row['post_title']) or not str(row['post_title']).strip():
                    continue
                
                doc = DocumentLoader._create_product_document(row)
                if doc:
                    documents.append(doc)
                    processed_count += 1
            
            print(f"Successfully processed {processed_count} health products from CSV")
            return documents
            
        except Exception as e:
            print(f"Error loading CSV file {file_path}: {e}")
            return []
    
    @staticmethod
    def _create_product_document(row: pd.Series) -> Optional[Document]:
        """Create a document from a product row."""
        title = str(row['post_title']).strip()
        content_parts = [f"Product: {title}"]
        
        # Add product information
        content_parts.extend(DocumentLoader._extract_product_content(row))
        
        # Create metadata
        metadata = DocumentLoader._create_minimal_metadata(row, title)
        
        # Create product data for later extraction
        product_data = DocumentLoader._create_product_data(row, title)
        
        # Combine content with product data
        full_content = "\n".join(content_parts)
        full_content += f"\n\n[PRODUCT_DATA]{json.dumps(product_data)}[/PRODUCT_DATA]"
        
        return Document(text=full_content, metadata=metadata)
    
    @staticmethod
    def _extract_product_content(row: pd.Series) -> List[str]:
        """Extract and format product content from row."""
        content_parts = []
        
        # Product Description
        if pd.notna(row['post_content']) and str(row['post_content']).strip():
            content = DocumentLoader._clean_html(str(row['post_content']).strip())
            content_parts.append(f"Description: {content}")
        
        # Product Excerpt
        if pd.notna(row['post_excerpt']) and str(row['post_excerpt']).strip():
            excerpt = DocumentLoader._clean_html(str(row['post_excerpt']).strip())
            content_parts.append(f"Summary: {excerpt}")
        
        # SEO Description
        if pd.notna(row['meta:_yoast_wpseo_metadesc']) and str(row['meta:_yoast_wpseo_metadesc']).strip():
            seo_desc = str(row['meta:_yoast_wpseo_metadesc']).strip()
            content_parts.append(f"Overview: {seo_desc}")
        
        # Category and Tags
        if pd.notna(row['tax:product_cat']) and str(row['tax:product_cat']).strip():
            category = str(row['tax:product_cat']).strip()
            content_parts.append(f"Category: {category}")
        
        if pd.notna(row['tax:product_tag']) and str(row['tax:product_tag']).strip():
            tags = str(row['tax:product_tag']).strip()
            content_parts.append(f"Tags: {tags}")
        
        # Pricing Information
        price_info = DocumentLoader._extract_price_info(row)
        if price_info:
            content_parts.append(" | ".join(price_info))
        
        # Additional product details
        for field, label in [
            ('stock_status', 'Availability'),
            ('sku', 'SKU')
        ]:
            if pd.notna(row[field]) and str(row[field]).strip():
                value = str(row[field]).strip()
                content_parts.append(f"{label}: {value}")
        
        return content_parts
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """Clean HTML tags from text."""
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()
    
    @staticmethod
    def _extract_price_info(row: pd.Series) -> List[str]:
        """Extract pricing information from row."""
        price_info = []
        
        if pd.notna(row['regular_price']) and str(row['regular_price']).strip():
            regular_price = str(row['regular_price']).strip()
            price_info.append(f"Regular Price: ${regular_price}")
        
        if pd.notna(row['sale_price']) and str(row['sale_price']).strip():
            sale_price = str(row['sale_price']).strip()
            price_info.append(f"Sale Price: ${sale_price}")
        
        return price_info
    
    @staticmethod
    def _create_minimal_metadata(row: pd.Series, title: str) -> Dict[str, Any]:
        """Create minimal metadata to avoid size issues."""
        metadata = {
            'title': title[:Config.MAX_TITLE_LENGTH],
            'type': 'health_product',
            'source': 'catalog'
        }
        
        # Add essential fields with length limits
        metadata_fields = [
            ('sku', 'sku', Config.MAX_FIELD_LENGTH),
            ('regular_price', 'price', 20),
            ('sale_price', 'sale_price', 20),
            ('stock_status', 'stock', 20),
            ('tax:product_cat', 'category', Config.MAX_FIELD_LENGTH),
            ('product_page_url', 'url', Config.MAX_URL_LENGTH)
        ]
        
        for field, key, max_len in metadata_fields:
            if pd.notna(row[field]) and str(row[field]).strip():
                metadata[key] = str(row[field]).strip()[:max_len]
        
        return metadata
    
    @staticmethod
    def _create_product_data(row: pd.Series, title: str) -> Dict[str, str]:
        """Create comprehensive product data for later extraction."""
        fields = [
            'regular_price', 'sale_price', 'stock_status', 'product_page_url',
            'tax:product_cat', 'post_excerpt', 'meta:_yoast_wpseo_metadesc'
        ]
        
        product_data = {'product_title': title}
        
        for field in fields:
            key = field.replace(':', '_').replace('meta_', '')
            value = str(row.get(field, '')).strip() if pd.notna(row.get(field)) else ''
            product_data[key] = value
        
        return product_data


class ProductRecommendationSystem:
    """Handles product recommendations and formatting."""
    
    @staticmethod
    def extract_product_data_from_content(content: str) -> Dict[str, Any]:
        """Extract product data from document content."""
        try:
            pattern = r'\[PRODUCT_DATA\](.*?)\[/PRODUCT_DATA\]'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return {}
        except Exception:
            return {}
    
    @staticmethod
    def should_show_products(query: str) -> bool:
        """Determine if product recommendations should be shown."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in Config.HEALTH_KEYWORDS)
    
    @staticmethod
    def extract_products_from_response(response) -> List[Dict[str, Any]]:
        """Extract product information from query response."""
        if not (hasattr(response, 'source_nodes') and response.source_nodes):
            return []
        
        products = []
        seen_products = set()
        
        for node in response.source_nodes:
            if (node.metadata and 
                node.metadata.get('type') == 'health_product'):
                
                product_data = ProductRecommendationSystem.extract_product_data_from_content(node.text)
                if product_data:
                    product_id = product_data.get('product_title', '')
                    if product_id and product_id not in seen_products:
                        seen_products.add(product_id)
                        products.append(product_data)
        
        return products[:Config.MAX_PRODUCTS_DISPLAYED]
    
    @staticmethod
    def format_product_recommendations(products: List[Dict[str, Any]]) -> str:
        """Format product recommendations for display."""
        if not products:
            return ""
        
        recommendation_text = "\n\n🛒 **Available Products & Services:**\n\n"
        
        for i, product in enumerate(products, 1):
            recommendation_text += ProductRecommendationSystem._format_single_product(i, product)
        
        return recommendation_text
    
    @staticmethod
    def _format_single_product(index: int, product: Dict[str, Any]) -> str:
        """Format a single product for display."""
        product_name = product.get('product_title', product.get('title', 'Health Product'))
        text = f"**{index}. {product_name}**\n"
        
        # Price information
        text += ProductRecommendationSystem._format_price_info(product)
        
        # Stock status
        stock_status = product.get('stock_status')
        if stock_status:
            status_emoji = "✅" if stock_status.lower() == "instock" else "⚠️"
            text += f"{status_emoji} Status: {stock_status.title()}\n"
        
        # Category
        category = product.get('tax_product_cat')
        if category:
            text += f"📂 Category: {category}\n"
        
        # Description
        text += ProductRecommendationSystem._format_description(product)
        
        # Purchase link
        product_url = product.get('product_page_url', product.get('url'))
        if product_url:
            text += f"🔗 <a href='{product_url}' target='_self'><strong>View Product & Purchase</strong></a>\n"
        
        return text + "\n"
    
    @staticmethod
    def _format_price_info(product: Dict[str, Any]) -> str:
        """Format price information for a product."""
        regular_price = product.get('regular_price')
        sale_price = product.get('sale_price')
        
        if not regular_price:
            return ""
        
        price_text = f"💰 Price: ${regular_price}"
        if sale_price and sale_price != regular_price:
            price_text = f"💰 Price: ~~${regular_price}~~ **${sale_price}** (On Sale!)"
        
        return price_text + "\n"
    
    @staticmethod
    def _format_description(product: Dict[str, Any]) -> str:
        """Format product description."""
        description = product.get('_yoast_wpseo_metadesc', product.get('post_excerpt'))
        
        if not description or not description.strip():
            return ""
        
        clean_desc = re.sub(r'<[^>]+>', '', description).strip()
        if len(clean_desc) > Config.MAX_DESCRIPTION_LENGTH:
            clean_desc = clean_desc[:Config.MAX_DESCRIPTION_LENGTH] + "..."
        
        return f"📝 {clean_desc}\n"


class IndexManager:
    """Manages the vector store index creation and loading."""
    
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = OpenAI(
            api_key=self.openai_api_key,
            model=Config.LLM_MODEL,
            temperature=0.6,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        self.embed_model = OpenAIEmbedding(
            api_key=self.openai_api_key,
            model=Config.EMBEDDING_MODEL
        )
    
    def load_or_create_index(self) -> VectorStoreIndex:
        """Load existing index or create new one if needed."""
        print("Initializing index with dynamic update checking...")
        
        # Create directories
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.STORAGE_DIR, exist_ok=True)
        
        # Check if rebuild is needed
        needs_rebuild = FileManager.check_files_changed(Config.DATA_DIR, Config.STORAGE_DIR)
        
        if not needs_rebuild:
            index = self._try_load_existing_index()
            if index:
                return index
            needs_rebuild = True
        
        if needs_rebuild:
            return self._build_new_index()
    
    def _try_load_existing_index(self) -> Optional[VectorStoreIndex]:
        """Try to load existing index from storage."""
        try:
            storage_context = StorageContext.from_defaults(persist_dir=Config.STORAGE_DIR)
            index = load_index_from_storage(storage_context)
            print("✅ Loaded existing index from storage")
            return index
        except Exception as e:
            print(f"⚠️ Failed to load existing index: {e}")
            return None
    
    def _build_new_index(self) -> VectorStoreIndex:
        """Build a new index from data files."""
        print("🔄 Files have changed, rebuilding index...")
        print("🔨 Building new index from data files...")
        
        documents = self._load_all_documents()
        
        if not documents:
            print("⚠️ No documents found. Please add files to the ./data directory")
            documents = [Document(text="Welcome to Natural Health Group. Please add your data files to get started.")]
        
        # Create nodes with text splitter
        text_splitter = SentenceSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        nodes = text_splitter.get_nodes_from_documents(documents)
        
        # Create and save index
        index = VectorStoreIndex(nodes, embed_model=self.embed_model)
        index.storage_context.persist(persist_dir=Config.STORAGE_DIR)
        
        # Save metadata for change detection
        FileManager.save_file_metadata(Config.DATA_DIR, Config.STORAGE_DIR)
        
        print(f"✅ Created and saved new index with {len(nodes)} nodes")
        return index
    
    def _load_all_documents(self) -> List[Document]:
        """Load all documents from the data directory."""
        documents = []
        
        for filename in os.listdir(Config.DATA_DIR):
            file_path = os.path.join(Config.DATA_DIR, filename)
            docs = self._load_single_file(filename, file_path)
            if docs:
                documents.extend(docs)
        
        return documents
    
    def _load_single_file(self, filename: str, file_path: str) -> List[Document]:
        """Load a single file based on its type."""
        try:
            if filename.endswith(".pdf"):
                reader = PDFReader()
                docs = reader.load_data(file=file_path)
                print(f"✅ Loaded PDF: {filename}")
                return docs
            elif filename.endswith(".txt"):
                docs = DocumentLoader.load_from_txt(file_path)
                print(f"✅ Loaded TXT: {filename}")
                return docs
            elif filename.endswith(".csv"):
                docs = DocumentLoader.load_from_csv(file_path)
                print(f"✅ Loaded CSV: {filename}")
                return docs
            elif filename.lower().endswith((".jpg", ".jpeg", ".png")):
                reader = ImageReader()
                docs = reader.load_data(file=file_path)
                print(f"✅ Loaded Image: {filename}")
                return docs
            else:
                print(f"⏭️ Skipping unsupported file type: {filename}")
                return []
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return []


class HealthAssistant:
    """Main application class that handles the chat interface with copilot features."""
    
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.index_manager = IndexManager()
        self.product_system = ProductRecommendationSystem()
        
        # Enhanced system prompt for copilot
        self.system_prompt = """You are Zoe, a helpful and friendly natural health expert representing Natural Health Group Australia. 

IDENTITY: Always introduce yourself as Zoe from Natural Health Group when greeting new users.

COMMUNICATION STYLE:
• Be conversational, warm, and approachable
• Keep responses concise (2-3 paragraphs max for most queries)
• Use emojis appropriately to make conversations friendly
• Match the user's tone and energy level

CAPABILITIES:
• Provide natural health advice and wellness guidance
• Recommend appropriate products from our catalog
• Help users book consultations
• Answer questions about our services and treatments
• Provide general health information (not medical diagnosis)

IMPORTANT GUIDELINES:
• Always clarify that you provide wellness guidance, not medical diagnosis
• Encourage users to book consultations for personalized advice
• Promote our products and services naturally in conversation
• If unsure about something, offer to connect them with our team
• Be proactive in suggesting relevant products or services"""
        
        # Keywords for booking detection
        self.booking_keywords = [
            "book", "booking", "schedule", "appointment", "consultation", "consult",
            "meet", "meeting", "session", "visit", "see you", "talk to you",
            "speak with", "reserve", "arrange", "set up", "plan", "when can"
        ]
        
        # Track conversation context for better copilot experience
        self.conversation_context = {}
    
    def create_query_engine(self, index: VectorStoreIndex):
        """Create and configure the query engine for copilot."""
        llm = OpenAI(
            api_key=self.openai_api_key,
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        
        custom_template = PromptTemplate(
            f"{self.system_prompt}\n\n"
            "COPILOT RESPONSE GUIDELINES:\n"
            "• Keep responses concise and scannable (use bullet points when helpful)\n"
            "• Be proactive - suggest next steps or related products/services\n"
            "• Use a friendly, conversational tone with appropriate emojis\n"
            "• Always end with a call-to-action or question to continue engagement\n"
            "• Focus on how Natural Health Group can help solve their specific needs\n"
            "• Never mention data sources, documents, or technical details\n\n"
            "Context from our knowledge base:\n{context_str}\n\n"
            "User question: {query_str}\n\n"
            "Your response as Zoe:"
        )
        
        return index.as_query_engine(
            text_qa_template=custom_template,
            streaming=True,
            similarity_top_k=Config.SIMILARITY_TOP_K,
            llm=llm,
            response_mode="tree_summarize"
        )
    
    async def handle_message(self, message: cl.Message):
        """Handle incoming chat messages with enhanced copilot features."""
        user_id = self._get_user_id()
        
        # Track conversation context
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = {
                "message_count": 0,
                "topics": [],
                "last_interaction": datetime.now()
            }
        
        self.conversation_context[user_id]["message_count"] += 1
        self.conversation_context[user_id]["last_interaction"] = datetime.now()
        
        # Handle different types of queries
        if self._wants_to_book_appointment(message.content):
            await self._handle_booking_request()
            return
        
        if self._is_greeting(message.content):
            await self._handle_greeting()
            return
        
        # Regular query processing
        query_engine = cl.user_session.get("query_engine")
        
        # Get response from query engine
        response = await cl.make_async(query_engine.query)(message.content)
        
        # Stream the response
        msg = cl.Message(content="", author="Zoe")
        await msg.send()
        
        full_response = ""
        for token in response.response_gen:
            full_response += token
            await msg.stream_token(token)
        
        # Add contextual enhancements
        await self._add_contextual_enhancements(msg, message.content, response)
        
        await msg.update()
    
    def _get_user_id(self) -> str:
        """Get or create user ID for session tracking."""
        user_id = cl.user_session.get("user_id")
        if not user_id:
            user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cl.user_session.set("user_id", user_id)
        return user_id
    
    def _is_greeting(self, message: str) -> bool:
        """Check if message is a greeting."""
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        message_lower = message.lower().strip()
        return any(greeting in message_lower for greeting in greetings) and len(message.split()) <= 3
    
    async def _handle_greeting(self):
        """Handle greeting messages with personalized response."""
        greeting_responses = [
            "Hi there! I'm Zoe from Natural Health Group 🌿",
            "Hello! Great to meet you! I'm Zoe, your natural health assistant 😊",
            "Hey! I'm Zoe from Natural Health Group. I'm here to help with all your wellness questions! 🌱"
        ]
        
        import random
        greeting = random.choice(greeting_responses)
        
        follow_up = (
            "\n\nI can help you with:\n"
            "• Natural health advice and wellness tips 🌿\n"
            "• Product recommendations for your specific needs 💊\n"
            "• Booking consultations with our experts 📅\n"
            "• Information about our treatments and services ✨\n\n"
            "What brings you here today?"
        )
        
        await cl.Message(content=greeting + follow_up, author="Zoe").send()
    
    async def _add_contextual_enhancements(self, msg: cl.Message, query: str, response):
        """Add contextual enhancements based on query and response."""
        enhancements = []
        
        # Add product recommendations if appropriate
        if self.product_system.should_show_products(query):
            products = self.product_system.extract_products_from_response(response)
            if products:
                recommendation_text = self.product_system.format_product_recommendations(products)
                enhancements.append(recommendation_text)
        
        # Add consultation prompt for complex health queries
        if self._should_suggest_consultation(query):
            consultation_prompt = (
                "\n\n💡 **Want personalized advice?** Our consultation can create a customized plan just for you!\n"
                "🔗 <a href='https://www.naturalhealthgroup.com.au/book-a-consultation/' target='_self'>Book a consultation here</a> 📅"
            )
            enhancements.append(consultation_prompt)
        
        # Add follow-up questions to keep conversation going
        follow_up = self._generate_follow_up_question(query)
        if follow_up:
            enhancements.append(f"\n\n{follow_up}")
        
        # Stream all enhancements
        for enhancement in enhancements:
            await msg.stream_token(enhancement)
    
    def _should_suggest_consultation(self, query: str) -> bool:
        """Determine if consultation should be suggested."""
        consultation_triggers = [
            "chronic", "persistent", "ongoing", "complex", "multiple symptoms",
            "not sure", "confused", "overwhelmed", "personalized", "specific to me"
        ]
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in consultation_triggers)
    
    def _generate_follow_up_question(self, query: str) -> Optional[str]:
        """Generate contextual follow-up questions."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["sleep", "insomnia", "tired"]):
            return "Are you also interested in learning about natural sleep aids or relaxation techniques? 😴"
        elif any(word in query_lower for word in ["digestion", "stomach", "gut"]):
            return "Would you like to know about our digestive health protocols or gut-healing supplements? 🌱"
        elif any(word in query_lower for word in ["stress", "anxiety", "overwhelmed"]):
            return "Are you looking for natural stress management strategies or calming supplements? 🧘‍♀️"
        elif any(word in query_lower for word in ["weight", "metabolism", "energy"]):
            return "Interested in our metabolic support programs or energy-boosting supplements? ⚡"
        
        return None
    
    def _wants_to_book_appointment(self, message: str) -> bool:
        """Check if user wants to book an appointment or consultation."""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.booking_keywords)
    
    async def _handle_booking_request(self):
        """Handle appointment booking requests with enhanced copilot experience."""
        booking_message = (
            "I'd love to help you book a consultation! 📅✨\n\n"
            "<a href='https://www.naturalhealthgroup.com.au/book-a-consultation/' target='_self'><strong>Book online now</strong></a> - Choosing your preferred time\n"
            "**What to expect:**\n"
            "• Comprehensive health assessment 📋\n"
            "• Personalized treatment plan 🎯\n"
        )
        
        await cl.Message(content=booking_message, author="Zoe").send()


# Initialize the main application
health_assistant = HealthAssistant()


@cl.cache
def load_index():
    """Load or create index - cached for performance."""
    return health_assistant.index_manager.load_or_create_index()

# Author rename decorator
@cl.author_rename
def rename(orig_author: str):
    """Rename assistant to Zoe for consistent branding."""
    rename_mapping = {
        "Assistant": "Zoe",
        "AI": "Zoe",
        "System": "Zoe"
    }
    return rename_mapping.get(orig_author, orig_author)


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    index = load_index()
    query_engine = health_assistant.create_query_engine(index)
    
    cl.user_session.set("query_engine", query_engine)
    cl.user_session.set("index", index)
    
    # Enhanced greeting for copilot
    welcome_message = (
        "Hi! I'm Zoe from Natural Health Group! 🌿\n\n"
        "I'm here to help you with natural health solutions, product recommendations, "
        "and booking consultations with our expert team.\n\n"
        "What can I help you with today? 😊"
    )
    
    await cl.Message(content=welcome_message, author="Zoe").send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    await health_assistant.handle_message(message)