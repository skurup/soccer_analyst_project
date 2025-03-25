import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from vector_db import SoccerAnalystVectorDB
import seaborn as sns

def visualize_embeddings():
    # Initialize the vector database
    db = SoccerAnalystVectorDB()
    
    # Get all collections
    collections = db.collections
    
    # Create a figure
    plt.figure(figsize=(15, 10))
    
    # Colors for different collections
    colors = sns.color_palette("husl", len(collections))
    
    # Plot each collection's embeddings
    for (name, collection), color in zip(collections.items()):
        # Get all documents from the collection
        results = collection.get()
        if results and 'embeddings' in results and results['embeddings']:
            # Convert embeddings to numpy array
            embeddings = np.array(results['embeddings'])
            
            # Reduce dimensionality to 2D using t-SNE
            tsne = TSNE(n_components=2, random_state=42)
            embeddings_2d = tsne.fit_transform(embeddings)
            
            # Plot the points
            plt.scatter(
                embeddings_2d[:, 0],
                embeddings_2d[:, 1],
                label=name,
                color=color,
                alpha=0.6
            )
            
            # Add labels for some points
            for i, doc_id in enumerate(results['ids'][:5]):  # Label first 5 points
                plt.annotate(
                    doc_id,
                    (embeddings_2d[i, 0], embeddings_2d[i, 1]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8
                )
    
    plt.title('ChromaDB Embeddings Visualization')
    plt.xlabel('t-SNE dimension 1')
    plt.ylabel('t-SNE dimension 2')
    plt.legend()
    
    # Save the plot
    plt.savefig('embeddings_visualization.png')
    plt.close()
    
    # Print statistics
    print("\nCollection Statistics:")
    stats = db.get_statistics_summary()
    for collection_name, count in stats.items():
        print(f"{collection_name}: {count} documents")

if __name__ == "__main__":
    visualize_embeddings() 