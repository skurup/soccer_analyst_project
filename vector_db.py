import chromadb
from chromadb.config import Settings
import os

class SoccerAnalystVectorDB:
    """Vector database for storing and querying soccer analysis data"""
    
    def __init__(self, persist_directory="soccer_analyst_db"):
        """Initialize the vector database"""
        # Ensure the persist directory exists
        self.persist_directory = os.path.join(os.getcwd(), persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create collections if they don't exist
        self.collections = {}
        collection_names = [
            "manchester_united",
            "epl_teams",
            "match_reports",
            "tactical_analysis",
            "team_stats"
        ]
        
        for name in collection_names:
            try:
                # Try to get existing collection
                collection = self.client.get_collection(name)
            except Exception:
                # Create new collection if it doesn't exist
                collection = self.client.create_collection(name)
            self.collections[name] = collection
        
    def add_document(self, document, metadata=None, collection_name="match_reports"):
        """Add a single document to a collection"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist")
            
        if metadata is None:
            metadata = {}
            
        # Convert any non-scalar values in metadata to strings
        processed_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                processed_metadata[key] = str(value)
            else:
                processed_metadata[key] = value
                
        # Get current count for ID generation
        try:
            current_count = len(self.collections[collection_name].get()['ids'])
        except Exception:
            current_count = 0
            
        self.collections[collection_name].add(
            documents=[document],
            metadatas=[processed_metadata],
            ids=[f"doc_{current_count + 1}"]
        )
        
    def add_documents(self, collection_name, documents, metadatas=None, ids=None):
        """Add multiple documents to a collection"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist")
            
        if isinstance(documents, str):
            documents = [documents]
            
        if metadatas is None:
            metadatas = [{}] * len(documents)
            
        # Convert any non-scalar values in metadatas to strings
        processed_metadatas = []
        for metadata in metadatas:
            processed_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    processed_metadata[key] = str(value)
                else:
                    processed_metadata[key] = value
            processed_metadatas.append(processed_metadata)
            
        if ids is None:
            # Get current count for ID generation
            try:
                current_count = len(self.collections[collection_name].get()['ids'])
            except Exception:
                current_count = 0
            ids = [f"doc_{current_count + i + 1}" for i in range(len(documents))]
            
        self.collections[collection_name].add(
            documents=documents,
            metadatas=processed_metadatas,
            ids=ids
        )
        
    def query_collection(self, collection_name, query_text, n_results=3, where=None):
        """Query a collection"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} does not exist")
            
        try:
            results = self.collections[collection_name].query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            print(f"Error querying collection {collection_name}: {str(e)}")
            return {"ids": [], "distances": [], "metadatas": [], "documents": []}
        
    def get_statistics_summary(self):
        """Get summary statistics for all collections"""
        stats = {}
        for name, collection in self.collections.items():
            try:
                stats[name] = len(collection.get()['ids'])
            except Exception:
                stats[name] = 0
        return stats 