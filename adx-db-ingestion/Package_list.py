import pandas as pd
import json
import io
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat

# ADX connection config
CLUSTER = "https://internproject.eastus.kusto.windows.net"
DATABASE = "Project"
TABLE = "PYPI"
MAPPING_NAME = "PackagesJsonMapping"

# Updated Excel file path
EXCEL_PATH = "pypi_with_client_name.xlsx"

# Connect to ADX
kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
ingest_client = QueuedIngestClient(kcsb)

ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TABLE,
    data_format=DataFormat.JSON,
    ingestion_mapping_reference=MAPPING_NAME
)

# === Load Excel and Prepare Data ===
df = pd.read_excel(EXCEL_PATH)
df.columns = df.columns.str.strip().str.lower()

# Ensure required columns are present and cleaned
df["data_packagename"] = df["data_packagename"].astype(str).str.strip()
df["client name"] = df["client name"].astype(str).str.strip()

# Drop rows with missing package names
df = df.dropna(subset=["data_packagename"])

# Drop duplicates — keep the first occurrence
df_unique = df.drop_duplicates(subset=["data_packagename"], keep="first")

# Create list of dicts for ingestion
records = [
    {"PackageName": row["data_packagename"], "ClientName": row["client name"]}
    for _, row in df_unique.iterrows()
]

# Convert to JSONL stream
json_data = "\n".join([json.dumps(record) for record in records])
json_stream = io.BytesIO(json_data.encode("utf-8"))

# Ingest into ADX
ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)

# Logging
print(f"✅ Ingested {len(records)} unique PyPI packages with client names into ADX.")
