
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os, shutil, time, uuid

from schema_discovery import SchemaDiscovery
from document_processor import DocumentProcessor
from query_engine import QueryEngine
from utils import get_ingestion_manager

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title='NLP Employee Query Engine Demo')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# global instances for demo; in production use per-request / DI
SD = SchemaDiscovery()
DOC_PROC = DocumentProcessor(storage_dir=UPLOAD_DIR)
ENGINE = None
ING_MANAGER = get_ingestion_manager()

@app.post('/api/ingest/database')
async def ingest_database(connection_string: str = Form(...)):
    global ENGINE
    try:
        schema = SD.analyze_database(connection_string)
        ENGINE = QueryEngine(connection_string, schema, doc_processor=DOC_PROC)
        return {'status':'ok', 'schema': schema}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/api/ingest/documents')
async def ingest_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    saved_paths = []
    for f in files:
        dest = os.path.join(UPLOAD_DIR, f.filename)
        with open(dest, 'wb') as out:
            shutil.copyfileobj(f.file, out)
        saved_paths.append(dest)
    job_id = ING_MANAGER.create_job(len(saved_paths))
    # process in background thread
    def _job(paths, job):
        def cb(): ING_MANAGER.update_progress(job, processed=1)
        DOC_PROC.process_documents(paths, job_update_callback=cb)
    background_tasks.add_task(_job, saved_paths, job_id)
    return {'status':'started', 'job_id': job_id, 'files': [os.path.basename(p) for p in saved_paths]}

@app.get('/api/ingest/status/{job_id}')
async def ingest_status(job_id: str):
    s = ING_MANAGER.get_status(job_id)
    if not s:
        raise HTTPException(status_code=404, detail='job id not found')
    return s

@app.post('/api/query')
async def query_endpoint(query: str = Form(...)):
    global ENGINE
    if ENGINE is None:
        raise HTTPException(status_code=400, detail='No database connected. Call /api/ingest/database first.')
    res = ENGINE.process_query(query)
    return res

@app.get('/api/query/history')
async def query_history():
    global ENGINE
    if ENGINE is None:
        return {'history': []}
    return {'history': ENGINE.get_history()}

@app.get('/api/schema')
async def get_schema():
    global ENGINE, SD
    # if engine exists, return its schema; else empty
    if ENGINE is not None:
        return {'schema': ENGINE.schema}
    return {'schema': {}}

# simple health endpoint
@app.get('/api/health')
async def health():
    return {'status':'ok'}
