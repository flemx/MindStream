# MindStream Project

## Overview
MindStream is a data processing pipeline that crawls data, converts JSON files to CSV, and ingests the data into Salesforce Data Cloud using the Bulk Ingest API. The solution supports RAG (Retrieval-Augmented Generation) search for Agent AI.

## Features
- JWT-based authentication with Salesforce Data Cloud
- Crawl data from a specified source using `DataCrawler`
- Convert crawled JSON data into CSV format using `JSONToCSVConverter`
- Ingest the CSV data into Salesforce Data Cloud using `DataCloudBulkIngest`
- Support for multiple org configurations and management
- Flexible pipeline execution (full pipeline or individual steps)
- Configurable crawler and ingestor settings

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

### Running the Project

The project provides several commands for managing orgs, configuration, and running the pipeline:

#### Pipeline Commands

1. Run individual pipeline steps:
   ```bash
   # Execute crawler with optional overrides
   mindstream crawl [--org myorg] [--output-path ./custom/path]
                   [--page-limit 100] [--crawl-url URL] [--api-key KEY]
                   [--whitelist "domain1.com,domain2.com"]
                   [-p respect_robots=true] [-p custom_param=value]

   # Convert JSON to CSV
   mindstream convert [--org myorg] 
                     [--input-path ./data.json]
                     [--output-path ./csv_output]

   # Upload CSV to Data Cloud
   mindstream upload [--org myorg]
                    [--input-path ./data.csv]
                    [--object-api-name "CustomDoc"]
                    [--source-name "custom_source"]
                    [--max-concurrent-jobs 5]
   ```

2. Run the complete pipeline:
   ```bash
   # Run with stored configuration
   mindstream pipeline

   # Run with overrides
   mindstream pipeline --org myorg \
                      --page-limit 100 \
                      --crawl-url "https://example.com" \
                      --api-key "your-key" \
                      --object-api-name "CustomDoc" \
                      --source-name "custom_source"
   ```

#### Configuration Management

1. View configuration:
   ```bash
   # Show all configuration
   mindstream config show

   # Show specific components
   mindstream config show --crawler
   mindstream config show --ingestor

   # Show org-specific config
   mindstream config show --org myorg
   ```

2. Configure crawler settings:
   ```bash
   # Set global crawler config
   mindstream config crawler set --page-limit 100 \
                               --crawl-url "https://example.com" \
                               --api-key "your-key" \
                               --whitelist "domain1.com,domain2.com"

   # Set org-specific crawler config
   mindstream config crawler set --org myorg \
                               --page-limit 100 \
                               --crawl-url "https://example.com"

   # Add custom parameters
   mindstream config crawler set -p respect_robots=true \
                               -p metadata=true \
                               -p custom_param=value
   ```

3. Configure ingestor settings:
   ```bash
   # Set global ingestor config
   mindstream config ingestor set --object-api-name "CustomDoc" \
                                 --source-name "custom_source" \
                                 --max-concurrent-jobs 5

   # Set org-specific ingestor config
   mindstream config ingestor set --org myorg \
                                 --source-name "org_specific_source"
   ```

## Authentication Setup

Authentication in MindStream is managed through the `org` commands. When you add a new org, the system automatically:
1. Creates the necessary directory structure
2. Authenticates with Salesforce using web login
3. Generates SSL certificates for JWT authentication
4. Deploys required metadata

### Managing Orgs

1. Add and authenticate orgs:
   ```bash
   # Add org and set as default
   mindstream org add --default

   # Add org with an alias
   mindstream org add --alias myorg

   # Add org with alias and set as default
   mindstream org add --alias myorg --default
   ```

2. Manage existing orgs:
   ```bash
   # Set current working org
   mindstream org use myorg

   # List all connected orgs
   mindstream org list

   # Re-authenticate an existing org
   mindstream org login user@example.com

   # Regenerate certificates
   mindstream org regenerate-certs [--username user@example.com] [--all-orgs]
   ```

3. Access org files:
   ```bash
   # Open current org directory
   mindstream open

   # Open specific org directory
   mindstream open --org myorg
   ```

### Getting Help

#### Show general help
```bash
mindstream --help
mindstream help
```

#### Show command-specific help
```bash
mindstream crawl --help
mindstream convert --help
mindstream upload --help
mindstream pipeline --help
mindstream config --help
mindstream org --help
```

## Configuration Storage

The project uses a `~/.mindstream` directory to store temporary data and configuration files:

```
~/.mindstream/
├── orgs/ # Org-specific data
│ ├── user@example.com/
│ │ ├── certificates/ # JWT certificates
│ │ ├── config.json # Org configuration
│ │ ├── results/ # Crawler results
│ │ └── csv_files/ # Converted CSV files
│ └── another@example.com/
└── global_config.json # Global configuration
```


### Configuration Hierarchy

The system follows this configuration hierarchy:
1. Command-line overrides (highest priority)
2. Org-specific configuration
3. Global defaults
4. Built-in defaults (lowest priority)

### Default Values

| Configuration      | Default Value     | Description                                    |
|------------------- |-------------------|------------------------------------------------|
| page_limit         | 50                | Maximum number of pages to crawl               |
| object_api_name    | "Document"        | Salesforce object API name                     |
| source_name        | "mindstream_data" | Source name for Data Cloud ingestion           |
| max_concurrent_jobs| 5                 | Maximum concurrent ingestion jobs              |
| crawl_url          | ""                | URL to start crawling from                     |
| api_key            | ""                | API key for authentication                     |
| whitelist          | []                | List of patterns to include while crawling     |

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
   mindstream config crawler set --api-key "your-spider-cloud-api-key"
   ```