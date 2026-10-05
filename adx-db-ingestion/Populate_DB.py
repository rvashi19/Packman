import requests
import csv
import os
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat 

# Configuration
PACKAGE_NAME = "qsharp"
API_URL = f"https://pypistats.org/api/packages/{PACKAGE_NAME}/overall"

# ADX configuration
CLUSTER = "https://project.eastasia.kusto.windows.net"
DATABASE = "PYPI Packages"
TABLE = "PyPIDownloads"

# Connect using Azure CLI authentication
KCSB_INGEST = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
ingest_client = QueuedIngestClient(KCSB_INGEST)


ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TABLE,
    data_format=DataFormat.CSV
)

# API call to fetch data
response = requests.get(API_URL)
if response.status_code != 200:
    raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

data = response.json().get("data", [])

# write data to CSV
csv_file = f"{PACKAGE_NAME}_downloads.csv"
with open(csv_file, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["PackageName", "Date", "Downloads"])
    for entry in data:
        if entry["category"] == "with_mirrors":
            writer.writerow([PACKAGE_NAME, entry["date"], entry["downloads"]])

# Ingest the CSV file into ADX 
ingest_client.ingest_from_file(csv_file, ingestion_properties=ingestion_props)

print(f"✅ Ingestion complete for package '{PACKAGE_NAME}' into table '{TABLE}'")
