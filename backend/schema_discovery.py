
from sqlalchemy import create_engine, inspect, MetaData
from difflib import get_close_matches

class SchemaDiscovery:
    def analyze_database(self, connection_string: str):
        engine = create_engine(connection_string, connect_args={"check_same_thread": False} if "sqlite" in connection_string else {})
        inspector = inspect(engine)
        schema = {'tables': {}}
        try:
            for t in inspector.get_table_names():
                cols = inspector.get_columns(t)
                fks = inspector.get_foreign_keys(t)
                schema['tables'][t] = {
                    'columns': [{ 'name': c['name'], 'type': str(c['type']) } for c in cols],
                    'foreign_keys': fks
                }
            # infer purposes
            inferred = {}
            for t in schema['tables']:
                lower = t.lower()
                if any(x in lower for x in ('emp','staff','person','personnel')):
                    inferred[t] = 'employees'
                elif any(x in lower for x in ('dept','division')):
                    inferred[t] = 'departments'
            schema['inferred'] = inferred
        except Exception as e:
            schema['error'] = str(e)
        return schema

    def map_natural_language_to_schema(self, query: str, schema: dict):
        tokens = [t.strip(' ,.?') for t in query.lower().split() if t]
        all_columns = []
        for table, meta in schema.get('tables', {}).items():
            for c in meta['columns']:
                all_columns.append((table, c['name']))
        col_names = [c for (_, c) in all_columns]
        candidates = {}
        for tok in tokens:
            matches = get_close_matches(tok, col_names, n=3, cutoff=0.6)
            if matches:
                idx = col_names.index(matches[0])
                candidates[tok] = {'table': all_columns[idx][0], 'column': matches[0]}
        return candidates
