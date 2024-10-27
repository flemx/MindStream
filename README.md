# MindStream Project

## Overview
MindStream is a data processing pipeline that crawls data, converts JSON files to CSV, and ingests the data into Salesforce Data Cloud using the Bulk Ingest API. The solution supports RAG (Retrieval-Augmented Generation) search for Agent AI.

## Features
- Crawl data from a specified source using `DataCrawler`
- Convert crawled JSON data into CSV format using `JSONToCSVConverter`
- Ingest the CSV data into Salesforce Data Cloud using `DataCloudBulkIngest`

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Salesforce access token and API key for the data source
- Data Cloud Bulk Ingest Access Token

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


### Running the Project

The pipeline can be configured using three parameter groups or a configuration file.

### Quick Start Example

```bash
python main.py pipeline \
--bulk-params "access_token=DC-123 instance_url=https://example.salesforce.com" \
--crawler-params "api_key=CR-456 crawl_url=https://docs.example.com whitelist=docs" \
--sfdc-params "access_token=SF-789"
```

####Parameters explanation####
--bulk-params:
- access_token is the token for the Data Cloud Bulk Ingest API.
- instance_url is the instance URL for the Data Cloud Bulk Ingest API.
--crawler-params 
- api_key is the API key for the Data Crawler.
- crawl_url is the URL to crawl.
- whitelist is the list of keywords to whitelist in the crawler, separated by commas.
--sfdc-params
- access_token is the Salesforce access token, to return status updates to Salesforce. (optional)


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
