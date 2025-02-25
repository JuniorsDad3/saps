from azure.storage.blob import BlobServiceClient

blob_service_client = BlobServiceClient.from_connection_string(DefaultEndpointsProtocol=https;AccountName=sectorservic;AccountKey=GJvminD4Ol3fRS0qkSVeXexItyMv/WmSWpiuK+vjnv3sqGpuepPBMcLJfNjBC6jIEfdf8fBYbNd6+AStW7wMFw==;EndpointSuffix=core.windows.net)

# Access container or blob
container_client = blob_service_client.get_container_client("sectorservic")
