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

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   .\venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the package locally:
   
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

4. Update the configuration values in `config.py` with your credentials and settings.

5. Place your Salesforce private key in `salesforce.key` file.

### Running the Project

The project provides several commands:

1. Run the complete pipeline:
   ```bash
   mindstream pipeline
   ```

2. Generate authentication token:
   ```bash
   mindstream auth
   ```

The pipeline command will crawl the data, convert it to CSV, and ingest it into Salesforce Data Cloud.

## Authentication Setup

There are multiple ways to authenticate with Salesforce Data Cloud:

### 1. Using Salesforce CLI (Recommended for Development)
The simplest way to authenticate is using your existing Salesforce CLI authentication:

```bash
# Using default org
mindstream auth --use-cli

# Using specific org alias
mindstream auth --use-cli --alias mindstream
```

### 2. Using JWT Authentication
For automated processes or CI/CD pipelines, you can use JWT-based authentication.

First, generate SSL certificates:
```bash
mindstream auth --generate-cert
```

This will:
- Create a `certificates` directory in the project root
- Generate `salesforce.key` and `salesforce.crt`
- Automatically update the connected app XML with the certificate
- Add the certificates directory to .gitignore

Then generate an access token:
```bash
mindstream auth
```

### 3. Generate Access Token
To generate a new access token using the default JWT method:
```bash
mindstream auth
```

### 4. Configuration Storage

The project uses a `~/.mindstream` directory to store temporary data and configuration files.

```
mindstream_project/
├── .mindstream/                      # Main temporary directory
│   ├── orgs/                         # Directory for org-specific data
│   │   ├── user1@salesforce.com/     # Org-specific directory
│   │   │   ├── certificates/         # Org certificates
│   │   │   ├── csv_files/           # Converted CSV files
│   │   │   ├── results/             # Crawled data results
│   │   │   └── config.json          # Org-specific configuration
│   │   └── user2@salesforce.com/
│   └── global_config.json           # Global configuration
```
   