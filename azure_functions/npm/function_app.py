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

# Only initialize clients if not in test mode
if os.environ.get("ENV") != "TEST":
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
else:
    # Dummy placeholders for tests — you can patch these later
    query_client = None
    ingest_client = None
    ingestion_props = None

app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 10 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def Ingest_data(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Daily NPM download ingestion started")

    try:
        # Fetch both PackageName and ClientName
        query = "npm | project PackageName, ClientName | distinct PackageName, ClientName"
        result = query_client.execute(DATABASE, query)
        package_rows = list(result.primary_results[0])
        logging.info(f"Retrieved {len(package_rows)} unique packages with clients")

        records = []
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        date_str = yesterday.isoformat()

        for row in package_rows:
            package = row["PackageName"]
            client = row["ClientName"]

            try:
                api_url = f"https://api.npmjs.org/downloads/point/{date_str}:{date_str}/{package}"
                response = requests.get(api_url)

                if response.status_code == 404:
                    logging.warning(f"Package not found: {package}")
                    downloads = 0
                else:
                    response.raise_for_status()
                    data = response.json()
                    downloads = data.get("downloads", 0)

                record = {
                    "PackageName": package,
                    "Version": "cumulative",
                    "Date": date_str,
                    "Downloads": downloads,
                    "PackageManager": "npm",
                    "ClientName": client
                }
                records.append(record)
                logging.info(f"{package} ({client}) - {downloads} downloads")

            except Exception as e:
                logging.error(f"Error fetching data for {package}: {e}")

            time.sleep(2)  # Prevent API throttling

        if records:
            json_data = "\n".join(json.dumps(r) for r in records)
            json_stream = io.BytesIO(json_data.encode("utf-8"))
            ingest_client.ingest_from_stream(json_stream, ingestion_properties=ingestion_props)
            logging.info(f"Ingested {len(records)} records into PackMan table")
        else:
            logging.warning("No data to ingest today")

    except Exception as e:
        logging.error(f"Function failed: {e}")
