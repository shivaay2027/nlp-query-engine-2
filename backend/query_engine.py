
import time
from cachetools import TTLCache
from schema_discovery import SchemaDiscovery
from sqlalchemy import create_engine, text
from typing import Optional

class QueryEngine:
    def __init__(self, connection_string, schema, doc_processor=None):
        self.connection_string = connection_string
        self.schema = schema
        self.doc_processor = doc_processor
        self.engine = create_engine(connection_string, pool_pre_ping=True)
        self.cache = TTLCache(maxsize=1000, ttl=300)
        self.history = []
        self.sd = SchemaDiscovery()

    def _classify(self, q: str):
        s = q.lower()
        if any(x in s for x in ('resume','cv','document','skill','skills','mention','review')):
            if any(x in s for x in ('how many','count','average','where','list','show','top')):
                return 'hybrid'
            return 'document'
        if any(x in s for x in ('how many','count','average','sum','max','min','group','top','where','list')):
            return 'structured'
        return 'hybrid'

    def get_history(self):
        return self.history[-100:]

    def process_query(self, user_query: str):
        start = time.time()
        if user_query in self.cache:
            res = self.cache[user_query]
            res['metrics']['cache_hit'] = True
            return res
        qtype = self._classify(user_query)
        out = {'query': user_query, 'type': qtype, 'results': {}, 'metrics': {}}
        try:
            if qtype in ('structured','hybrid'):
                mapped = self.sd.map_natural_language_to_schema(user_query, self.schema)
                structured = self._execute_structured(user_query, mapped)
                out['results']['structured'] = structured
            if qtype in ('document','hybrid') and self.doc_processor:
                docs = self.doc_processor.search(user_query)
                out['results']['documents'] = docs
            out['metrics'] = {'time': round(time.time() - start, 3), 'cache_hit': False}
            self.cache[user_query] = out
            self.history.append({'q': user_query, 't': out['metrics']['time'], 'type': qtype})
            return out
        except Exception as e:
            return {'error': str(e)}

    def _execute_structured(self, user_query, mapping: dict):
        s = user_query.lower()
        with self.engine.connect() as conn:
            # how many / count
            if 'how many' in s or 'count' in s:
                # find an employees table
                table = None
                for t,v in self.schema.get('inferred', {}).items():
                    if v == 'employees':
                        table = t; break
                if not table:
                    table = list(self.schema['tables'].keys())[0]
                sql = text(f"SELECT COUNT(*) as cnt FROM {table}")
                r = conn.execute(sql).fetchone()
                return {'rows': [{'count': int(r['cnt']) if r else 0}]}
            # average salary by department
            if 'average' in s and ('salary' in s or 'compens' in s or 'pay' in s):
                # try to locate salary and dept columns
                salary_col = None; dept_col = None; table_for_salary = None
                for t, meta in self.schema['tables'].items():
                    for c in meta['columns']:
                        name = c['name'].lower()
                        if not salary_col and any(k in name for k in ('sal','compens','pay')):
                            salary_col = c['name']; table_for_salary = t
                        if not dept_col and any(k in name for k in ('dept','division','department')):
                            dept_col = c['name']
                if salary_col and dept_col and table_for_salary:
                    sql = text(f"SELECT {dept_col} as department, AVG({salary_col}) as avg_salary FROM {table_for_salary} GROUP BY {dept_col}")
                    rows = [dict(r) for r in conn.execute(sql)]
                    return {'rows': rows}
            # fallback: return top 10 from likely employees table
            table = None
            for t,v in self.schema.get('inferred', {}).items():
                if v == 'employees':
                    table = t; break
            if not table:
                table = list(self.schema['tables'].keys())[0]
            sql = text(f"SELECT * FROM {table} LIMIT 10")
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            return {'rows': rows}
