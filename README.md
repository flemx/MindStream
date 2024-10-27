# MindStream Project

## Overview
MindStream is a data processing pipeline that crawls data, converts JSON files to CSV, and ingests the data into Salesforce Data Cloud using the Bulk Ingest API. The solution supports RAG (Retrieval-Augmented Generation) search for Agent AI.

## Features
- JWT-based authentication with Salesforce Data Cloud
- Crawl data from a specified source using `DataCrawler`
- Convert crawled JSON data into CSV format using `JSONToCSVConverter`
- Ingest the CSV data into Salesforce Data Cloud using `DataCloudBulkIngest`

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Salesforce access token and API key for the data source
- Private key file for JWT authentication

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd mindstream_project
   ```

2. Install the package locally:
   
   For standard installation:
   ```bash
   python -m build
   pip install .
   ```

   For development (if you plan to modify the code):
   ```bash
   python -m build
   pip install -e .  # Install in editable/development mode
   ```

   > **Note:** The `-e` flag installs the package in "editable" or "development" mode, allowing you to modify the source code without reinstalling.

3. Update the configuration values in `config.py` with your credentials and settings.

4. Place your Salesforce private key in `salesforce.key` file.

### Running the Project

The pipeline can be configured using three parameter groups or a configuration file.

### Quick Start Example

```bash
python main.py pipeline \
--bulk-params "access_token=DC-123 instance_url=https://example.salesforce.com" \
--crawler-params "api_key=CR-456 crawl_url=https://docs.example.com whitelist=docs" \
--sfdc-params "access_token=SF-789"
```

``` bash
export DC_TOKEN="DC-123"
export CRAWLER_KEY="CR-456"
export SF_TOKEN="SF-789"
python main.py pipeline \
--bulk-params "access_token=$DC_TOKEN instance_url=https://example.salesforce.com" \
--crawler-params "api_key=$CRAWLER_KEY crawl_url=https://docs.example.com" \
--sfdc-params "access_token=$SF_TOKEN"
```

### Using Configuration File

```bash
python main.py pipeline --config-file config.json
```

Configuration file example:

```json
{
   "bulk_ingest":{
      "access_token": "DC-123",
      "instance_url": "https://example.salesforce.com"
   },
   "crawler": {
      "api_key": "CR-456",
      "crawl_url": "https://docs.example.com",
      "whitelist": ["docs"]
   },
   "sfdc_access_token": "SF-789"
}
```
Note: Replace the example tokens and URLs with your actual configuration values.
