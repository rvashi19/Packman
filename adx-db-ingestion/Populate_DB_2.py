import requests
import json
import io
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat
from datetime import datetime

# Config
PACKAGE_NAME = "qsharp-jupyterlab"
API_URL = f"https://pypistats.org/api/packages/{PACKAGE_NAME}/overall"
CLUSTER = "https://project.eastasia.kusto.windows.net"
DATABASE = "PYPI Packages"
TABLE = "PyPIDownloads"

# Azure auth
kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
ingest_client = QueuedIngestClient(kcsb)

# Ingestion properties
ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TABLE,
    data_format=DataFormat.JSON,
    ingestion_mapping_reference="JsonMapping"
)

# Get data
response = requests.get(API_URL)
response.raise_for_status()
data = response.json().get("data", [])

# Filter and prepare JSON records
records = [
    {
        "PackageName": PACKAGE_NAME,
        "Date": datetime.strptime(entry["date"], "%Y-%m-%d").isoformat() + "Z",
        "Downloads": entry["downloads"]
    }
    for entry in data if entry["category"] == "with_mirrors"
]

# Create in-memory JSON stream
json_data = "\n".join([json.dumps(record) for record in records])
json_stream = io.BytesIO(json_data.encode("utf-8"))

# Ingest
ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)

print("Ingestion complete (JSON)")
