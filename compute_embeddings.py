import json
import os
import sys
import random
import numpy as np
from datetime import datetime
from pathlib import Path

# Try imports
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    import pandas as pd
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please run: pip install sentence-transformers scikit-learn pandas")
    sys.exit(1)

# Configuration
INPUT_FILE = "discord_messages.json"
OUTPUT_FILE = "wrapped-frontend/public/vector_data.json"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_MESSAGES = 2000 # Limit for performance/demo
N_CLUSTERS = 8 # Number of "Nebulae"
MIN_LENGTH = 20     # Minimum characters to be meaningful

def load_and_filter_messages(filepath):
    print(f"Loading {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both formats (flat messages or sessions)
    all_messages = []
    
    if 'messages' in data:
        print("Detected flat message format")
        all_messages = data['messages']
    elif isinstance(data, list):
        print("Detected session format")
        for s in data:
            for m in s.get('messages', []):
                if 'timestamp' not in m:
                    m['timestamp'] = s.get('start_time')
                all_messages.append(m)
    else:
        print("Unknown data format")
        return []
            
    print(f"Total messages found: {len(all_messages)}")
    
    # Filter for meaningful content
    valid_messages = [
        m for m in all_messages 
        if m.get('content') and len(m['content']) >= MIN_LENGTH
        and not m['content'].startswith('http') # Skip just links
    ]
    print(f"Valid messages (> {MIN_LENGTH} chars): {len(valid_messages)}")
    
    # Sample if too many
    if len(valid_messages) > MAX_MESSAGES:
        # Prefer recent messages? Or random?
        # Let's do a mix: 50% recent, 50% random from the rest
        # Sort by timestamp (assuming ISO format)
        valid_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        recent = valid_messages[:MAX_MESSAGES // 2]
        others = valid_messages[MAX_MESSAGES // 2:]
        random_others = random.sample(others, MAX_MESSAGES // 2)
        selected = recent + random_others
    else:
        selected = valid_messages
        
    print(f"Selected {len(selected)} messages for analysis")
    return selected

def generate_embeddings(messages):
    print(f"Loading embedding model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)
    
    texts = [m['content'] for m in messages]
    print("Generating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    return embeddings

def reduce_dimensions(embeddings):
    print("Reducing dimensions...")
    
    # Step 1: PCA to 50 dims (standard practice before t-SNE)
    if embeddings.shape[1] > 50:
        pca = PCA(n_components=50)
        pca_result = pca.fit_transform(embeddings)
    else:
        pca_result = embeddings
        
    # Step 2: t-SNE to 3 dims
    tsne = TSNE(n_components=3, random_state=42, perplexity=30, n_iter=1000)
    tsne_result = tsne.fit_transform(pca_result)
    
    return tsne_result

def perform_clustering(embeddings, n_clusters=8):
    print(f"Performing K-Means clustering (k={n_clusters})...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10) # n_init added for sklearn 1.4+
    cluster_labels = kmeans.fit_predict(embeddings)
    return cluster_labels

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found")
        return

    # 1. Load Data
    messages = load_and_filter_messages(INPUT_FILE)
    if not messages:
        print("No messages found to analyze.")
        return

    # 2. Embed
    embeddings = generate_embeddings(messages)
    
    # 3. Reduce Dimensions (3D)
    coords = reduce_dimensions(embeddings)
    
    # 4. Cluster
    cluster_labels = perform_clustering(embeddings, n_clusters=N_CLUSTERS)
    
    # 5. Format Output
    points = []
    for i, msg in enumerate(messages):
        points.append({
            "id": msg.get('id', f"msg_{i}"),
            "x": float(coords[i][0]),
            "y": float(coords[i][1]),
            "z": float(coords[i][2]),
            "cluster": int(cluster_labels[i]),
            "content": msg['content'],
            "author": msg['author'],
            "timestamp": msg['timestamp'],
            "date": msg['timestamp'][:10],
            "channel_id": msg.get('channel_id'),
            "message_id": msg.get('id')
        })
        
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "count": len(points),
        "clusters": N_CLUSTERS,
        "points": points
    }
    
    # 6. Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
        
    print(f"✅ Saved vector space data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
