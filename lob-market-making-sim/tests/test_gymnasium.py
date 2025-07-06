
from lob_market_making_sim.models.rl.env import LOBMarketMakerEnv
import pandas as pd
import pyarrow as pa
import lob_market_making_sim.io.loader as loader
from pathlib import Path

path = Path(__file__).parent.parent
source_data = path / "notebooks" / "data" / "parquet" / "AMZN_2025-06-12.parquet"
print("my path")
print(source_data)

# Import dataframe that has been built previously
df = pd.read_parquet(source_data)

# Convert dataframe to Iterable[OrderEvent]
events = loader.arrow_to_events(pa.Table.from_pandas(df))

env = LOBMarketMakerEnv(event_sequence=events)
obs, _ = env.reset()

done = False
while not done:
    action = env.action_space.sample()
    obs, reward, done, _, _ = env.step(action)
