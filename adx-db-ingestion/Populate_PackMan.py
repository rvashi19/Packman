import requests
import json
import io
from datetime import datetime, timedelta
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat

# ADX Configuration
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
        api_url = f"https://pypistats.org/api/packages/{package_name}/overall"
        response = requests.get(api_url)
        response.raise_for_status()
        all_data = response.json().get("data", [])

        stats = {
            entry["date"]: entry["downloads"]
            for entry in all_data
            if entry["category"] == "without_mirrors"
        }

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 6, 25)
        delta = (end_date - start_date).days + 1
        date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta)]

        records = [
            {
                "PackageName": package_name,
                "Version": version,
                "Date": date + "T00:00:00Z",
                "Downloads": stats.get(date, 0),
                "PackageManager": "PYPI",
                "ClientName": client_name
            }
            for date in date_list
        ]

        json_data = "\n".join(json.dumps(record) for record in records)
        json_stream = io.BytesIO(json_data.encode("utf-8"))
        ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)

        print(f"✅ Ingested data for {package_name} (client: {client_name})")

    except Exception as e:
        print(f"❌ Error ingesting {package_name}: {e}")
