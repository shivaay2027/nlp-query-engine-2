
import os, pdfplumber, traceback
from docx import Document
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.neighbors import NearestNeighbors

class DocumentProcessor:
    def __init__(self, storage_dir):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.docs = []  # {id,path,text,meta,embedding?}
        self.model = None
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            # model unavailable; fall back to token index
            self.model = None
        self.nn = None

    def _extract_text(self, path):
        lower = path.lower()
        try:
            if lower.endswith('.pdf'):
                with pdfplumber.open(path) as pdf:
                    pages = [p.extract_text() or '' for p in pdf.pages]
                    return '\n\n'.join(pages)
            elif lower.endswith('.docx'):
                doc = Document(path)
                return '\n\n'.join(p.text for p in doc.paragraphs)
            elif lower.endswith('.csv'):
                df = pd.read_csv(path)
                return df.to_csv(index=False)
            else:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            return ''

    def dynamic_chunking(self, content: str, doc_type: str):
        paras = [p.strip() for p in content.split('\n') if p.strip()]
        chunks = []
        cur = ''
        for p in paras:
            if len(cur) + len(p) < 2000:
                cur += '\n' + p
            else:
                chunks.append(cur.strip())
                cur = p
        if cur.strip():
            chunks.append(cur.strip())
        return chunks

    def process_documents(self, file_paths, job_update_callback=None):
        new_texts = []
        created = []
        for p in file_paths:
            text = self._extract_text(p)
            chunks = self.dynamic_chunking(text, os.path.splitext(p)[1].lower())
            for c in chunks:
                entry = {'id': len(self.docs), 'path': p, 'text': c, 'meta': {'source': os.path.basename(p)}}
                self.docs.append(entry)
                new_texts.append(c)
            created.append({'path': p, 'chunks': len(chunks)})
            if job_update_callback:
                job_update_callback()
        # embeddings
        if self.model and new_texts:
            all_texts = [d['text'] for d in self.docs]
            embs = self.model.encode(all_texts, batch_size=32, show_progress_bar=False)
            self.embeddings = np.vstack(embs)
            self.nn = NearestNeighbors(n_neighbors=5, metric='cosine')
            self.nn.fit(self.embeddings)
            for i,d in enumerate(self.docs):
                d['embedding'] = self.embeddings[i]
        else:
            for d in self.docs:
                d['tokens'] = set(d['text'].lower().split())
        return created

    def search(self, query, top_k=5):
        if getattr(self, 'nn', None) is not None:
            q_emb = self.model.encode([query])
            dists, inds = self.nn.kneighbors(q_emb, n_neighbors=min(top_k, len(self.docs)))
            results = []
            for dist, idx in zip(dists[0], inds[0]):
                results.append({'score': float(1 - dist), 'text': self.docs[idx]['text'], 'source': self.docs[idx]['meta']['source']})
            return results
        else:
            q_tokens = set(query.lower().split())
            scored = []
            for d in self.docs:
                overlap = len(q_tokens & d.get('tokens', set()))
                if overlap > 0:
                    scored.append((overlap, d))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [{'score': s, 'text': d['text'], 'source': d['meta']['source']} for s,d in scored[:top_k]]
            return results
