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

### Configuration Management

MindStream provides a flexible configuration system that can be managed through CLI commands. You can set both global defaults and org-specific configurations.

#### Setting Global Defaults

Use the `mindstream config set` command to configure global defaults:

```bash
# Set individual configuration values
mindstream config set --page-limit 100 # Maximum number of pages to crawl
mindstream config set --object-api-name "Document" # Ingestion object API name
mindstream config set --source-name "mindstream_data" # Source name for Data Cloud ingestion
mindstream config set --max-concurrent-jobs 5 # Maximum concurrent ingestion jobs
mindstream config set --crawl-url "<The website you want to crawl>" # URL to start crawling from
mindstream config set --api-key "your-api-key" # API key for spider cloud crawler authentication

# Set whitelist patterns (comma-separated)
mindstream config set --whitelist "/docs/*,/api/*" # Only crawl docs and API paths
```

The whitelist patterns determine which URLs should be included during the crawling process. These patterns support both glob-style (`*`) and regex patterns, and are matched against the full URL path.



#### Viewing Current Configuration

To view your current global configuration:
```bash
mindstream config show
```

Example output:
```json
{
  "current_org": "user@salesforce.com",
  "version": "1.0",
  "defaults": {
    "page_limit": 100,
    "object_api_name": "Document",
    "source_name": "mindstream_data",
    "max_concurrent_jobs": 5,
    "crawl_url": "<The website you want to crawl>",
    "api_key": "your-api-key",
    "whitelist": []
  }
}
```

#### Managing Multiple Orgs

1. Add a new org:
```bash
mindstream org add user@salesforce.com
```

2. Switch to an org:
```bash
mindstream org use user@salesforce.com
```

Each org maintains its own configuration and can override global defaults. The configuration is stored in:
- `~/.mindstream/orgs/<username>/config.json`

#### Configuration Hierarchy

The system follows this configuration hierarchy:
1. Org-specific configuration (if set)
2. Global defaults (if org-specific not set)
3. Built-in defaults (if neither above is set)

#### Default Values

Here are the default values used if not explicitly set:

| Configuration      | Default Value        | Description                                    |
|-------------------|---------------------|------------------------------------------------|
| page_limit        | 50                 | Maximum number of pages to crawl               |
| object_api_name   | "Document"         | Salesforce object API name                     |
| source_name       | "sfdc_ai_documents"| Source name for Data Cloud ingestion          |
| max_concurrent_jobs| 5                 | Maximum concurrent ingestion jobs              |
| crawl_url         | ""                | URL to start crawling from                     |
| api_key           | ""                | API key for authentication                     |
| whitelist         | []                | List of patterns to include while crawling     |




## Spider Cloud Integration

MindStream uses [Spider Cloud](https://spider.cloud/) for high-performance web crawling. Spider Cloud offers:
- Up to 20,000 pages/second crawling speed
- LLM-ready markdown output
- Smart mode with automatic headless Chrome switching
- Automatic proxy rotation and anti-bot detection

### Getting an API Key

1. Sign up at [spider.cloud](https://spider.cloud/)
2. You'll receive $200 in free credits when you spend $100
3. Copy your API key from the dashboard
4. Add it to your configuration:
```bash
mindstream config set --api-key "your-spider-cloud-api-key"
```
