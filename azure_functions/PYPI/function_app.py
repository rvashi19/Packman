import logging
import azure.functions as func
import requests
import json
import io
from datetime import datetime, timedelta
from azure.kusto.data import KustoConnectionStringBuilder, KustoClient
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.data.data_format import DataFormat
import time
import os


# Azure Data Explorer config
CLUSTER = os.environ.get("CLUSTER")
DATABASE = os.environ.get("DATABASE")
PACKAGES_TABLE = os.environ.get("PACKAGES_TABLE")
TARGET_TABLE = os.environ.get("TARGET_TABLE")
MAPPING_NAME = os.environ.get("MAPPING_NAME")

# Authenticate with Azure Managed Identity
kcsb = KustoConnectionStringBuilder.with_aad_managed_service_identity_authentication(CLUSTER)
query_client = KustoClient(kcsb)
ingest_client = QueuedIngestClient(kcsb)

# Ingestion properties
ingestion_props = IngestionProperties(
    database=DATABASE,
    table=TARGET_TABLE,
    data_format=DataFormat.JSON,
    ingestion_mapping_reference=MAPPING_NAME
)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 5 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def Ingest_data(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Daily PyPI download ingestion started")

    try:
        # Fetch both PackageName and ClientName
        query = "PYPI | project PackageName, ClientName | distinct PackageName, ClientName"
        result = query_client.execute(DATABASE, query)
        package_rows = list(result.primary_results[0])
        logging.info(f"Retrieved {len(package_rows)} unique packages with clients")

        records = []
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        iso_yesterday = datetime.combine(yesterday, datetime.min.time()).isoformat() + "Z"
        yesterday_str = yesterday.isoformat()

        for row in package_rows:
            package = row["PackageName"]
            client = row["ClientName"]

            try:
                api_url = f"https://pypistats.org/api/packages/{package}/overall"
                response = requests.get(api_url)

                if response.status_code == 404:
                    logging.warning(f"Package not found: {package}")
                    record = {
                        "PackageName": package,
                        "Version": "cumulative",
                        "Date": iso_yesterday,
                        "Downloads": 0,
                        "PackageManager": "PYPI",
                        "ClientName": client
                    }
                    records.append(record)
                    continue

                response.raise_for_status()
                all_data = response.json().get("data", [])

                # Match entry with yesterday’s date
                match = next(
                    (entry for entry in all_data
                     if entry["category"] == "without_mirrors" and entry["date"] == yesterday_str),
                    None
                )

                if not match:
                    logging.warning(f"No download data for {package} on {yesterday_str}")
                    continue

                record = {
                    "PackageName": package,
                    "Version": "cumulative",
                    "Date": yesterday_str + "T00:00:00Z",
                    "Downloads": match["downloads"],
                    "PackageManager": "PYPI",
                    "ClientName": client
                }
                records.append(record)
                logging.info(f"{package} ({client}) - {match['downloads']} downloads")

            except Exception as e:
                logging.error(f"Error fetching data for {package}: {e}")

            time.sleep(2)

        # Ingesting to ADX
        if records:
            json_data = "\n".join(json.dumps(r) for r in records)
            json_stream = io.BytesIO(json_data.encode("utf-8"))
            ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)
            logging.info(f"Ingested {len(records)} records to PackMan table")
        else:
            logging.warning("No data to ingest today")

    except Exception as e:
        logging.error(f"Function failed: {e}")