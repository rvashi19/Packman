import requests
import json
import io
from datetime import datetime, timedelta
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat

# ADX connection setup
CLUSTER = "https://internproject.eastus.kusto.windows.net"
DATABASE = "Project"
TABLE = "PackMan"

kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)
ingest_client = QueuedIngestClient(kcsb)

ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TABLE,
    data_format=DataFormat.JSON,
    ingestion_mapping_reference="JsonMappingWithVersion"
)

def ingest_package_data(package_name: str, version: str = None, client_name: str = ""):
    version = version or "cumulative"
    try:
        # Date range
        start_date = "2025-07-01"
        end_date = "2025-07-01"
        api_url = f"https://api.npmjs.org/downloads/range/{start_date}:{end_date}/{package_name}"

        response = requests.get(api_url)
        response.raise_for_status()
        all_data = response.json().get("downloads", [])

        stats = {entry["day"]: entry["downloads"] for entry in all_data}

        # Fill dates even with 0 downloads
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        date_list = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
                     for i in range((end_dt - start_dt).days + 1)]

        records = [
            {
                "PackageName": package_name,
                "Version": version,
                "Date": date + "T00:00:00Z",
                "Downloads": stats.get(date, 0),
                "PackageManager": "npm",
                "ClientName": client_name
            }
            for date in date_list
        ]

        json_data = "\n".join(json.dumps(record) for record in records)
        json_stream = io.BytesIO(json_data.encode("utf-8"))
        ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)

        print(f"✅ Ingested NPM package: {package_name} (Client: {client_name})")

    except Exception as e:
        print(f"❌ Error ingesting {package_name}: {e}")
