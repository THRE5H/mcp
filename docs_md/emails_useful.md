*******
"problem": "Users experience intermittent timeout errors when downloading large datasets from the dnext API, causing scheduled tasks to fail or require multiple attempts.",
      "solution": "To resolve timeout issues when downloading large datasets via the dnext API, increase the wait time in the polling loop that checks the task status. Below is an improved Python script example that implements an exponential backoff wait time up to 30 seconds, ensuring the task has enough time to complete before timing out.

```python
import pandas as pd
import requests
import json
import time
from io import BytesIO

def task_status(urlTask, task_id, headers):
    success = False
    wait_time = 2
    while not success and wait_time < 30:
        time.sleep(wait_time)
        status_res = requests.get(urlTask + task_id, headers=headers, timeout=30)
        try:
            success = status_res.json().get(\"status\") == \"SUCCEEDED\"
        except:
            wait_time += 1
            continue
        if not success:
            wait_time += 1
    return success

def _get_task_status(task_id, headers, urlTask):
    if task_status(urlTask, task_id, headers):
        return True
    return False

def _get_dataset(dataset_code, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        \"format\": \"csv\"
    })
    urlDataset = f'https://api.dnext.io/v1.0/data/datasets/{dataset_code}/download'
    urlTask = 'https://api.dnext.io/v1.0/tasks/'

    resultdownload = requests.post(urlDataset, headers=headers, data=payload, timeout=30).json()

    if \"task\" not in resultdownload or \"id\" not in resultdownload[\"task\"]:
        raise ValueError(\"Task ID not found in the response\")

    task_id = resultdownload[\"task\"][\"id\"]

    if _get_task_status(task_id, headers, urlTask):
        if \"result\" in resultdownload and \"url\" in resultdownload[\"result\"]:
            file_url = resultdownload[\"result\"][\"url\"]
            data_response = requests.get(file_url, allow_redirects=True)
            return pd.read_csv(BytesIO(data_response.content))
        else:
            raise ValueError(\"Download URL not found in the response\")
    else:
        raise TimeoutError(\"Task did not succeed within the allowed limit\")

def _get_token(email: str, pwd: str, organisation: str):
    \"\"\"Retrieve an authentication token.\"\"\"
    url = f'https://api.dnext.io/v1.0/auth/custom-login?org={organisation}'
    payload = json.dumps({
        'email': email,
        'password': pwd,
        'organization': organisation
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
    response.raise_for_status()  # Raise an error for invalid responses
    return response.json()['token']


def _extract_data(dataset_code: str, email: str, pwd: str, organisation: str) -> pd.DataFrame:
    \"\"\"Extract data from the API.\"\"\"
    token = _get_token(email=email, pwd=pwd, organisation=organisation)
    return _get_dataset(dataset_code, token)

# Example usage:
_extract_data(\"[organisation]-[uuid]\", \"username.lastname@org.domain\", \"password", \"[organisation]\")
```

Notes:
- The key improvement is the `wait_time` variable in the `task_status` function, which starts at 2 seconds and increases by 1 second after each unsuccessful check, up to a maximum of 30 seconds.
- This approach controls the real elapsed time waiting for the task to complete, rather than relying on a fixed number of retries.
- If you encounter timeout errors with larger datasets, increase the maximum wait time (currently 30 seconds) accordingly.
- Replace the placeholder email, password, and environment parameters with your actual credentials.
",
      "keywords": [
        "dnext API",
        "timeout",
        "wait_time",
        "task status polling",
        "Python script",
        "dataset download",
        "exponential backoff",
        "requests",
        "pandas"
      ],
      "category": "API / Script"

*******
"problem": "User is unable to download TradeMatrix aggregated data due to changes in the download URL and needs a correct script to authenticate and retrieve the data.",
      "solution": "Use the following Python script to authenticate with the DNEXT API, check task status, and download TradeMatrix aggregated tradeflow data. Replace \"email", \"password\", and \"organisation\" with your actual credentials and environment name.

```python
import requests
import pandas as pd
from io import BytesIO
import time
import json

def connect(email, pwd, organisation):
    '''
    email: email used to connect to your dnext environment
    pwd: password
    organisation: name of your enviroment, first part in your dnext URL before the dot
    organisation.dnext.io -> organisation = 'organisation'
    '''
    url = f'https://api.dnext.io/v1.0/auth/custom-login?org={organisation}'
    payload = json.dumps({ 
        'email': f'{email}', 
        'password': f'{pwd}', 
        'organization': f'{organisation}'
    })
    headers = { 'Content-Type': 'application/json' }
    response = requests.post(url, headers=headers, data=payload)
    token = response.json()['token']
    return token

token = connect(\"email\",\"password\",\"organisation\")

def _get_task_status(task_id, token):
    my_headers = { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
    success = False
    wait_time = 2
    while not success and wait_time < 30:
        time.sleep(wait_time)
        status_res = requests.get(f'https://api.dnext.io/v1.0/tasks/{task_id}', headers=my_headers)
        try:
            success = status_res.json()['status'] == 'SUCCEEDED'
        except:
            wait_time += 1
            continue
        if not success:
            wait_time += 1
    if success:
        return True
    else:
        return False

def download_tradeflow(code, token):
    my_headers = { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
    data = {\"intraflows\": {\"strategy\":\"exclude\"}, \"row\":False,\"refresh\":True,\"format\":\"csv\"}
    dl_url = f'https://api.dnext.io/v1.0/fundamentals/tradeflows/aggregations//download'
    res = requests.post(dl_url, headers=my_headers, data=json.dumps(data))
    print(res.json())
    task_id = res.json()['task']['id']
    data_ready = _get_task_status(task_id, token)
    if data_ready:
        data_url = res.json()['result']['url']
        data_resp = requests.get(data_url)
        df = pd.read_csv(BytesIO(data_resp.content))
    else:
        df = None
    return df

df = download_tradeflow(\"organisation-[uuid]\", token)
```

Replace the placeholders with your actual email, password, and environment name. This script logs in, requests the aggregated tradeflow data download, polls the task status until completion, and then downloads the CSV data into a pandas DataFrame.",
      "keywords": [
        "DNEXT API",
        "TradeMatrix",
        "aggregated data",
        "download script",
        "authentication token",
        "task status polling",
        "Python",
        "requests",
        "pandas"
      ],
      "category": "API / Script"

*******


"problem": "Email delivery failure with error code 554 5.4.14 indicating a possible mail loop or hop count exceeded when sending to a recipient address that does not exist or is misconfigured.",
      "solution": "To resolve the 554 5.4.14 mail loop or hop count exceeded error: 1) Verify that the recipient email address is correct and exists on the destination domain. 2) If using a hybrid environment with directory synchronization, ensure the recipient's email address is properly synchronized between Office 365 and the local directory. 3) Check for and correct any misconfigured mail forwarding or inbox rules that may cause loops. 4) Verify mail flow settings and MX records for the domain to ensure they are correctly configured. 5) For organizations with mailboxes split between Office 365 and on-premises, ensure that outbound connectors are properly configured to route mail to local mailboxes to avoid loops. 6) Clear the Outlook autocomplete cache for the recipient address and re-enter the full email address manually when resending. 7) Consult Microsoft documentation for error code 5.4.14 for additional troubleshooting steps.",
      "keywords": [
        "email delivery failure",
        "554 5.4.14",
        "mail loop",
        "hop count exceeded",
        "Office 365",
        "hybrid environment",
        "directory synchronization",
        "mail forwarding rules",
        "MX records",
        "outbound connector",
        "autocomplete cache",
        "email address verification",
        "mail flow configuration"
      ],
      "category": "Error Resolution"
*******
"problem": "Users experienced issues retrieving data for the new 'wheat aggregation' trade flow code via the DNEXT API after the update on dataset and trade flow UIDs.",
      "solution": "To correctly download aggregated TradeMatrix data using the updated trade flow codes, use the following Python script. Replace \"email\", \"password\", and \"[organisation]\" with your actual DNEXT login credentials and environment name.

```python
import requests
import pandas as pd
from io import BytesIO
import time
import json

# Login to API and get token
def connect(email, pwd, organisation):
    '''
    email: email used to connect to your dnext environment
    pwd: password 
    organisation: name of your enviroment, first part in your dnext URL before the dot
    organisation.dnext.io -> organisation = 'organisation'
    '''
    # Login to API and get token
    url = f'https://api.dnext.io/v1.0/auth/custom-login?org={organisation}'
    
    payload = json.dumps({
        'email': f'{email}',
        'password': f'{pwd}',
        'organization': f'{organisation}'
    })
 
    headers = {
        'Content-Type': 'application/json'
    }
 
    response = requests.post(url, headers=headers, data=payload)
    token = response.json()['token']
    return token
    
token = connect(\"email",\"password\",\"[organisation]\")

def _get_task_status(task_id, token):
    my_headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    success = False
    wait_time = 2
    while not success and wait_time < 30:
        time.sleep(wait_time)
        status_res = requests.get(f'https://api.dnext.io/v1.0/tasks/{task_id}', headers=my_headers)
        try:
            success = status_res.json()['status'] == 'SUCCEEDED'
        except:
            wait_time += 1
            continue
        if not success:
            wait_time += 1
    if success:
        return True
    else:
        return False

def download_tradeflow(code, token):
    my_headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    data = {\"intraflows\":{\"strategy\":\"exclude\"},\"row\":False,\"refresh\":True,\"format\":\"csv\"}
    dl_url = f'https://api.dnext.io/v1.0/fundamentals/tradeflows/aggregations/{code}/download'
    res = requests.post(dl_url, headers=my_headers, data=json.dumps(data))
    print(res.json())
    task_id = res.json()['task']['id']
    data_ready = _get_task_status(task_id, token)
    if data_ready:
        data_url = res.json()['result']['url']
        data_resp = requests.get(data_url)
        df = pd.read_csv(BytesIO(data_resp.content))
    else:
        df = None
    return df

df = download_tradeflow(\"[organisation]-[uuid]\", token)
```

This script handles authentication, requests the aggregated trade flow data download task, waits for task completion, and then downloads the CSV data into a pandas DataFrame.",
      "keywords": [
        "DNEXT",
        "API",
        "trade flow",
        "aggregation",
        "data download",
        "Python script",
        "token authentication",
        "task status",
        "CSV download"
      ],
      "category": "API / Script"

*******
