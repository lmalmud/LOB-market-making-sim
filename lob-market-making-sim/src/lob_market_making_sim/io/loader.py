'''
loader.py
Functionality for parsing a .csv file of event orders into
an iterable, using the types defined in schema.py
'''

import pyarrow as pa
import pyarrow.csv
import lob_market_making_sim.io.schema as schema

def lobster_to_arrow(raw_msg_path):
    '''
    Converts the data contained in a LOBSTER dataset to a pandas Table.
    Parameters:
    raw_msg_path (string): location of the .csv file to be converted
    Returns:
    pa.Table: parsed table
    Raises:
    '''

    convert_options = pa.csv.ConvertOptions(column_types=schema.COL_SCHEMA) # Enforce types
    read_options = pa.csv.ReadOptions(column_names=list(schema.COLS)) # Set appropriate column names
    return pa.csv.read_csv(raw_msg_path,
                           read_options=read_options,
                           convert_options=convert_options)

def arrow_to_events(table):
    '''
    Converts information in a Pyarrow data loaded from LOBSTER order events
    to an iterable of OrderEvents.
    Parameters:
    table (pa.Table): table with relevent order event information
    Returns:
    Iterable[OrderEvent]
    '''
    events = []
    for row in table.to_pylist():
        # Create an OrderEvent for each row
        events.append(schema.OrderEvent(ts=row['time'],
                          etype=schema.EventType(row['event_type'],), # Use the enum EventType
                          oid=row['order_id'],
                          size=row['size'],
                          price=row['price'],
                          direction=schema.Direction(row['direction'])))
    return events
        