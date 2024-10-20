# MindStream Project

## Overview
MindStream is a data processing pipeline that crawls data, converts JSON files to CSV, and ingests the data into Salesforce Data Cloud using the Bulk Ingest API. The solution supports RAG (Retrieval-Augmented Generation) search for Agent AI.

## Features
- Crawl data from a specified source using `DataCrawler`.
- Convert crawled JSON data into CSV format using `JSONToCSVConverter`.
- Ingest the CSV data into Salesforce Data Cloud using `DataCloudBulkIngest`.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Salesforce access token and API key for the data source.

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd mindstream_project
   ```

2. Install the package locally:
   ```bash
   python -m build
   pip install .
   ```

3. Update the configuration values in `config.py` with your credentials and settings.

### Running the Project
To run the project, execute the following command:
```bash
mindstream
```
This command will crawl the data, convert it to CSV, and ingest it into Salesforce Data Cloud.