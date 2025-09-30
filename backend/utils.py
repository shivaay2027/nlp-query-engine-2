
import os, time, threading, uuid
from typing import Dict

class IngestionJobManager:
    def __init__(self):
        self.jobs = {}  # job_id -> status dict

    def create_job(self, total_files:int):
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {'total': total_files, 'processed': 0, 'status': 'running', 'started_at': time.time(), 'finished_at': None}
        return job_id

    def update_progress(self, job_id, processed=1):
        if job_id in self.jobs:
            self.jobs[job_id]['processed'] += processed
            if self.jobs[job_id]['processed'] >= self.jobs[job_id]['total']:
                self.jobs[job_id]['status'] = 'finished'
                self.jobs[job_id]['finished_at'] = time.time()

    def get_status(self, job_id):
        return self.jobs.get(job_id, None)

# singleton for demo
_ingestion_manager = IngestionJobManager()

def get_ingestion_manager():
    return _ingestion_manager
