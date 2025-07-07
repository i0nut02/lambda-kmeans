import os
import boto3
import numpy as np
from PIL import Image
from io import BytesIO
import time
import json
import logging


s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

INPUT_BUCKET = os.environ['INPUT_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']

def kmeans_numpy(X, n_clusters, max_iter=100, tol=1e-4):
    np.random.seed(0)
    centroids = X[np.random.choice(len(X), n_clusters, replace=False)]
    for _ in range(max_iter):
        distances = np.linalg.norm(X[:, None] - centroids[None, :], axis=2)
        labels = np.argmin(distances, axis=1)
        new_centroids = np.array([X[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i] for i in range(n_clusters)])
        if np.allclose(centroids, new_centroids, atol=tol):
            break
        centroids = new_centroids
    return labels, centroids

def lambda_handler(event, context):
    start_time_total = time.time()
    
    # ayload API Gateway 
    # JSON format : {"image_key": "path/to/image.jpg", "k_clusters": 8}
    # Default k_cluster: 4
    try:
        body = json.loads(event.get('body', '{}'))
        in_key = body['image_key']
        k_clusters = int(body.get('k_clusters', 4))  
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid payload: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing image_key or invalid JSON in request body'})
        }

    # get image from S3
    start_time_s3_download = time.time()
    try:
        resp = s3.get_object(Bucket=INPUT_BUCKET, Key=in_key)
        img = Image.open(resp['Body']).convert('RGB')
    except s3.exceptions.NoSuchKey:
        logger.error(f"Image not found in S3: {in_key}")
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'Image key not found: {in_key}'})
        }
    s3_download_duration = (time.time() - start_time_s3_download) * 1000
    original_width, original_height = img.size

    # K-means moment, we need to REMOVE REMOVE REMOVE img.resize if we are testing forrrrreal
    start_time_processing = time.time()
    img = img.resize((256, 256)) 
    arr = np.array(img)
    pixels = arr.reshape(-1, 3).astype(np.float32)
    labels, centers = kmeans_numpy(pixels, n_clusters=k_clusters)
    processing_duration = (time.time() - start_time_processing) * 1000

    start_time_reconstruction = time.time()
    new_colors = centers.astype(np.uint8)
    seg_pixels = new_colors[labels]
    seg_arr = seg_pixels.reshape(arr.shape)
    seg_img = Image.fromarray(seg_arr)
    buffer = BytesIO()
    seg_img.save(buffer, format='PNG')
    buffer.seek(0)
    reconstruction_duration = (time.time() - start_time_reconstruction) * 1000

    # S3 output
    start_time_s3_upload = time.time()
    base_name = os.path.splitext(os.path.basename(in_key))[0]
    out_key = f"segmented/{base_name}_K{k_clusters}.png"
    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=out_key,
        Body=buffer,
        ContentType='image/png'
    )
    s3_upload_duration = (time.time() - start_time_s3_upload) * 1000
    
    total_duration = (time.time() - start_time_total) * 1000

    # LOG CloudWatch 
    log_data = {
        "metric_name": "ImageProcessingPerformance",
        "image_key": in_key,
        "clusters": k_clusters,
        "original_width": original_width,
        "original_height": original_height,
        "memory_configured_mb": context.memory_limit_in_mb, # Aggiungiamo la memoria
        "duration_total_ms": round(total_duration, 2),
        "duration_s3_download_ms": round(s3_download_duration, 2),
        "duration_processing_kmeans_ms": round(processing_duration, 2),
        "duration_reconstruction_ms": round(reconstruction_duration, 2),
        "duration_s3_upload_ms": round(s3_upload_duration, 2)
    }
    logger.info(json.dumps(log_data))

    return {
        'statusCode': 200,
        'body': json.dumps({
            'input_key': in_key,
            'output_bucket': OUTPUT_BUCKET,
            'output_key': out_key,
            'clusters_used': k_clusters,
            'processing_time_ms': round(total_duration, 2)
        })
    }