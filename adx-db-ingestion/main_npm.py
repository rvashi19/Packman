import pandas as pd
from populate_PackMan_npm import ingest_package_data

def load_npm_package_data(excel_path: str) -> list[tuple[str, str]]:
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip().str.lower()

    # Ensure columns are in the correct format
    df["full_package_name"] = df["full_package_name"].astype(str).str.strip()
    df["client name"] = df["client name"].astype(str).str.strip()

    # Drop missing values in package name
    df = df.dropna(subset=["full_package_name"])

    # Remove duplicates based on package name
    df_unique = df.drop_duplicates(subset=["full_package_name"], keep="first")

    # Return list of tuples: (package_name, client_name)
    return list(zip(df_unique["full_package_name"], df_unique["client name"]))

if __name__ == "__main__":
    package_data = load_npm_package_data("npm_with_client_name.xlsx")
    print(f"🔍 Found {len(package_data)} unique NPM packages.")

    for package_name, client_name in package_data:
        print(f"\n🚀 Ingesting: {package_name} (Client: {client_name})")
        ingest_package_data(package_name, client_name=client_name)