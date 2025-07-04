import os
import boto3
import numpy as np
from PIL import Image
from io import BytesIO

# Client S3
s3 = boto3.client('s3')

# Numero di cluster (opzionale: sovrascrivibile via env var)
K = int(os.getenv('NUM_CLUSTERS', 4))
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']

# KMeans minimale solo con numpy
def kmeans_numpy(X, n_clusters=4, max_iter=100, tol=1e-4):
    np.random.seed(0)
    centroids = X[np.random.choice(len(X), n_clusters, replace=False)]

    for _ in range(max_iter):
        distances = np.linalg.norm(X[:, None] - centroids[None, :], axis=2)
        labels = np.argmin(distances, axis=1)

        new_centroids = np.array([X[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
                                  for i in range(n_clusters)])

        if np.allclose(centroids, new_centroids, atol=tol):
            break
        centroids = new_centroids

    return labels, centroids

def lambda_handler(event, context):
    # 1) Estrai info da evento
    in_bucket = event['Records'][0]['s3']['bucket']['name']
    in_key    = event['Records'][0]['s3']['object']['key']

    # 2) Scarica immagine da S3
    resp = s3.get_object(Bucket=in_bucket, Key=in_key)
    img = Image.open(resp['Body']).convert('RGB')

    # (opzionale) Ridimensiona
    img = img.resize((256, 256))

    # 3) Prepara i dati
    arr = np.array(img)
    pixels = arr.reshape(-1, 3).astype(np.float32)

    # 4) KMeans solo numpy
    labels, centers = kmeans_numpy(pixels, n_clusters=K)
    new_colors = centers.astype(np.uint8)

    # 5) Ricostruisci immagine
    seg_pixels = new_colors[labels]
    seg_arr = seg_pixels.reshape(arr.shape)
    seg_img = Image.fromarray(seg_arr)

    # 6) Serializza immagine
    buffer = BytesIO()
    seg_img.save(buffer, format='PNG')
    buffer.seek(0)

    # 7) Scrivi su S3
    base_name = os.path.splitext(os.path.basename(in_key))[0]
    out_key = f"{base_name}_segmented_K{K}.png"

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=out_key,
        Body=buffer,
        ContentType='image/png'
    )

    return {
        'statusCode': 200,
        'body': {
            'input_bucket': in_bucket,
            'input_key': in_key,
            'output_bucket': OUTPUT_BUCKET,
            'output_key': out_key
        }
    }