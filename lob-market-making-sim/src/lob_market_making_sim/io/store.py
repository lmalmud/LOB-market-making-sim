'''
store.py
'''

import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List

class ArrowStore:
    '''
    Helper that batches consecutive pyarrow.Tables in memory
    and flushes them as one Parquet file.

    Usage
    store = ArrowStore(schema=my_schema)
    for table in table_generator():
        store.add_batch(table)
    store.flush('data/parquet/AMZN_2025-06-12.parquet')
    '''
    def __init__(self, schema):
        '''
        Parameters
        schema (pyarrow.Schema): the format that batches must conform to
        '''
        self._schema = schema
        self._batches: List[pa.RecordBatch] = []
    
    def add_batch(self, tbl):
        '''
        Appends a pyarrowTable to the in-memory buffer.
        Parameters
        tbl (pyarrow.Table): the next chunk of data to be parsed (but conform to schema)
        Raises
        ValueError
            If incoming schema differs from stored one
        '''
        if pa.schema(tbl.schema) != self._schema:
            raise ValueError('Incoming table schema does not match stored schema.')
        # tbl.to_batches() converts pyarrow table to list of pyarrow RecordBatches
        self._batches.extend(tbl.to_batches()) # use .extend since there may be multiple batches
    
    def flush(self, out_path: str | Path, 
              *, # means that everything after must be specified as keyword parameter
              compression: str = "snappy") -> Path:
        '''
        Write all buffered batches to a single Partqut file
        and clear the buffer.
        Parameters
        out_path (str or pathlib.Path): destination file
        compression ('snappy', 'zstd', None): Parquet column-level compresison code
        Returns
        pathlib.Path: fully qualified path of Parquet file written
        Raises
        RuntimeError
            If no data to flush
        '''
        out_path = Path(out_path)
        # Creates the parent folder if it does not already exist
        # without raising errors if it is already present
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._batches:
            raise RuntimeError('No data buffered - nothing to flush')
        
        # Convert to a pandas table from the already parsed batches
        table = pa.Table.from_batches(self._batches, schema=self._schema)
        # Write the table to a Parquet file at the given path with particular compression
        pq.write_table(table, out_path, compression = compression)
    
        self._batches.clear() # Reset internal buffer
        return out_path