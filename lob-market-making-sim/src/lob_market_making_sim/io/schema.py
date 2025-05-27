'''
schema.py
Define the schema that will be used as files are imported.
One canonical container for easier typing & testing.

Dataclass Reference
https://www.dataquest.io/blog/how-to-use-python-data-classes/#:~:text=In%20Python%2C%20a%20data%20class,a%20program%20or%20a%20system.
LOBSTER Reference
https://lobsterdata.com/info/DataStructure.php
'''

from enum import Enum               # Class to associate numbers with keywords
from dataclasses import dataclass   # Class designed to only hold values
import pyarrow as pa

COLS = ['time', 'event_type', 'order_id', 'size', 'price', 'direction']
COL_SCHEMA = events_schema = pa.schema([
        pa.field('time', pa.float64()),
        pa.field('event_type', pa.int32()),
        pa.field('order_id', pa.int64()),
        pa.field('size', pa.int64()),
        pa.field('price', pa.int64()),
        pa.field('direction', pa.int64())
    ])

class Direction(Enum): 
    '''
    Direction of trade as indicated in the message file.
    '''
    BUY = 1         # A buy order is initiated by a seller 
    SELL= - 1       # A sell order is initiated by a buyer
    
class EventType(Enum):
    '''
    All possible event types as indicated in message file.
    '''
    ADD = 1                 # Submission of a new limit order
    CANCEL = 2              # Cancellation (partial deletion of a limit order)
    DELETE = 3              # Total deletion of a limit order
    EXECUTE_VISIBLE = 4     # Execution of a visible limit order
    EXECUTE_HIDDEN = 5      # Execution of a hidden limit order
    CROSS = 6               # Inditates a cross/auction trade
    HALT = 7                # Trade halt indicator
    
@dataclass(slots=True)
class OrderEvent:
    '''
    One event, as formatted in the message file.
    '''
    ts: int # nanoseconds since midnight
    etype: EventType
    oid: int # unique order id
    size: int # shares after event
    price: int # price in integer ticks
    direction: Direction