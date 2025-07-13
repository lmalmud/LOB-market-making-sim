'''
test_rl.py
Tests the model on Apple trading data.

To run: poetry run python src/lob_market_making_sim/models/rl/test_rl.py
'''
from pathlib import Path
from stable_baselines3 import DQN
from lob_market_making_sim.models.rl.env import LOBMarketMakerEnv
from lob_market_making_sim.io.loader import lobster_to_arrow, arrow_to_events

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent
EVENT_SOURCE = BASE_DIR / "data" / "test" / "AAPL_2012-06-21_34200000_57600000_message_1.csv"
MODEL_DEST = BASE_DIR / "src" / "lob_market_making_sim" / "models" / "rl" / "dqn_lob_market_maker"
events_arrow = lobster_to_arrow(EVENT_SOURCE)
events = arrow_to_events(events_arrow)

model = DQN.load(MODEL_DEST)
env = LOBMarketMakerEnv(event_sequence=events)

obs, _ = env.reset()
done = False
while not done:
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, _, _ = env.step(action)

print("cash:")
print(env.engine.cash)
print("inventory:")
print(env.engine.inv)