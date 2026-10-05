import pandas as pd
from Populate_PackMan import ingest_package_data  # importing function

def load_unique_package_data(excel_path: str) -> list[tuple[str, str]]:
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip().str.lower()
    df["data_packagename"] = df["data_packagename"].astype(str).str.strip()
    df["client name"] = df["client name"].astype(str).str.strip()
    
    df = df.dropna(subset=["data_packagename"])
    df_unique = df.drop_duplicates(subset=["data_packagename"], keep="first")

    return list(zip(df_unique["data_packagename"], df_unique["client name"]))

if __name__ == "__main__":
    package_data = load_unique_package_data("pypi_with_client_name.xlsx")
    print(f"🔍 Found {len(package_data)} unique PyPI packages.")

    for package_name, client_name in package_data:
        print(f"\n🚀 Ingesting: {package_name} for client: {client_name}")
        ingest_package_data(package_name, client_name=client_name)
