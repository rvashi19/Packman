import pandas as pd
import json
import io
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat

# ADX connection config
CLUSTER = "https://internproject.eastus.kusto.windows.net"
DATABASE = "Project"
TABLE = "npm"
MAPPING_NAME = "PackagesJsonMapping"

# Excel file path
EXCEL_PATH = "npm_with_client_name.xlsx"

# Connect to ADX
kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
ingest_client = QueuedIngestClient(kcsb)

ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TABLE,
    data_format=DataFormat.JSON,
    ingestion_mapping_reference=MAPPING_NAME
)

# === Load and clean the data ===
df = pd.read_excel(EXCEL_PATH)
df.columns = df.columns.str.strip().str.lower()

df["full_package_name"] = df["full_package_name"].astype(str).str.strip()
df["client name"] = df["client name"].astype(str).str.strip()

# Drop rows missing package names
df = df.dropna(subset=["full_package_name"])

# Drop duplicates by package name
df_unique = df.drop_duplicates(subset=["full_package_name"], keep="first")

# Prepare records for ingestion
records = [
    {"PackageName": row["full_package_name"], "ClientName": row["client name"]}
    for _, row in df_unique.iterrows()
]

# Convert to JSONL
json_data = "\n".join([json.dumps(record) for record in records])
json_stream = io.BytesIO(json_data.encode("utf-8"))

# Ingest into ADX
ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)

print(f"✅ Ingested {len(records)} unique NPM packages with client names into ADX.")
