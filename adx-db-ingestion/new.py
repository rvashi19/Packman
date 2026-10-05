import pandas as pd

# === Step 1: Load Excel files ===
npm_df = pd.read_excel("npm_packages_with_full_name.xlsx")
pypi_df = pd.read_excel("packages-publlished-pypi.xlsx")
master_df = pd.read_excel("Packages.xlsx")

# === Step 2: Clean column names ===
npm_df.columns = npm_df.columns.str.strip().str.lower()
pypi_df.columns = pypi_df.columns.str.strip().str.lower()
master_df.columns = master_df.columns.str.strip().str.lower()

# === Step 3: Normalize values for safe matching ===
npm_df["full_package_name"] = npm_df["full_package_name"].astype(str).str.strip().str.lower()
pypi_df["data_packagename"] = pypi_df["data_packagename"].astype(str).str.strip().str.lower()
master_df["package name"] = master_df["package name"].astype(str).str.strip().str.lower()

# === Step 4: Drop duplicates in master (keep only first match) ===
master_unique = master_df.drop_duplicates(subset="package name", keep="first")

# === Step 5: Merge with master to get Client Name ===
npm_merged = npm_df.merge(
    master_unique[["package name", "client name"]],
    left_on="full_package_name",
    right_on="package name",
    how="left"
)

pypi_merged = pypi_df.merge(
    master_unique[["package name", "client name"]],
    left_on="data_packagename",
    right_on="package name",
    how="left"
)

# === Step 6 (Optional): Keep only matched rows ===
# npm_merged = npm_merged.dropna(subset=["client name"])
# pypi_merged = pypi_merged.dropna(subset=["client name"])

# === Step 7: Save to Excel ===
npm_merged.to_excel("npm_with_client_name.xlsx", index=False)
pypi_merged.to_excel("pypi_with_client_name.xlsx", index=False)

print("✅ Done. Files saved as:")
print(" - npm_with_client_name.xlsx")
print(" - pypi_with_client_name.xlsx")
