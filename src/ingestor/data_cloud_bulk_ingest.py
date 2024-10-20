import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class DataCloudBulkIngest:
    def __init__(self, access_token, instance_url, object_api_name, source_name, max_concurrent_jobs=5):
        self.access_token = access_token
        self.instance_url = instance_url
        self.object_api_name = object_api_name
        self.source_name = source_name
        self.max_concurrent_jobs = max_concurrent_jobs
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        self.bulk_ingest_endpoint = f"{self.instance_url}/api/v1/ingest/jobs"

    def create_bulk_ingest_job(self):
        job_data = {
            "object": self.object_api_name,
            "sourceName": self.source_name,
            "operation": "upsert"
        }
        response = requests.post(self.bulk_ingest_endpoint, headers=self.headers, json=job_data)
        if response.status_code in [200, 201]:
            job_info = response.json()
            job_id = job_info.get('id')
            print(f"Created Bulk Ingest Job with ID: {job_id}")
            return job_id
        else:
            print(f"Failed to create Bulk Ingest Job. Status code: {response.status_code}, Response: {response.text}")
            return None

    def upload_data_to_job(self, job_id, csv_file_path):
        upload_endpoint = f"{self.bulk_ingest_endpoint}/{job_id}/batches"
        headers_upload = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'text/csv'
        }
        with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            csv_data = csv_file.read()
        response = requests.put(upload_endpoint, headers=headers_upload, data=csv_data)
        if response.status_code in [200, 201]:
            print(f"Uploaded data to Job ID: {job_id}")
            return True
        else:
            print(f"Failed to upload data to Job ID: {job_id}. Status code: {response.status_code}, Response: {response.text}")
            return False

    def close_job(self, job_id):
        close_endpoint = f"{self.bulk_ingest_endpoint}/{job_id}"
        close_data = {
            "state": "UploadComplete"
        }
        response = requests.patch(close_endpoint, headers=self.headers, json=close_data)
        if response.status_code == 200:
            print(f"Closed Job ID: {job_id}")
            return True
        else:
            print(f"Failed to close Job ID: {job_id}. Status code: {response.status_code}, Response: {response.text}")
            return False

    def monitor_job(self, job_id):
        status_endpoint = f"{self.bulk_ingest_endpoint}/{job_id}"
        while True:
            response = requests.get(status_endpoint, headers=self.headers)
            if response.status_code == 200:
                job_info = response.json()
                state = job_info.get('state')
                print(f"Job ID: {job_id}, State: {state}")
                if state in ['JobComplete', 'Failed', 'Aborted']:
                    break
                else:
                    time.sleep(10)  # Wait before checking again
            else:
                print(f"Failed to get status for Job ID: {job_id}. Status code: {response.status_code}, Response: {response.text}")
                break

    def process_csv_file(self, csv_file_path):
        job_id = self.create_bulk_ingest_job()
        if not job_id:
            return
        if not self.upload_data_to_job(job_id, csv_file_path):
            return
        if not self.close_job(job_id):
            return
        self.monitor_job(job_id)

    def execute_bulk_ingest(self, csv_files):
        with ThreadPoolExecutor(max_workers=self.max_concurrent_jobs) as executor:
            futures = {executor.submit(self.process_csv_file, csv_file_path): csv_file_path for csv_file_path in csv_files}
            for future in as_completed(futures):
                csv_file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {csv_file_path}: {e}")