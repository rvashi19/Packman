import requests
from datetime import datetime

start_date = "2025-01-01"
end_date = "2025-06-15"
package_name = "@azure/arm-authorization-profile-2020-09-01-hybrid"

# API URL
url = f"https://api.npmjs.org/downloads/range/{start_date}:{end_date}/{package_name}"

# request
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print("Successful API call!")
    print("\nSample Response:\n")
    print(data)  
else:
    print(f"Failed with status code: {response.status_code}")
    print(response.text)
