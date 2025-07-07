'''
train_rl.py
Trains the agent.

tensorboard --logdir=./logs
To run: poetry run python src/lob_market_making_sim/models/rl/train_rl.py
'''

import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback
from lob_market_making_sim.models.rl.env import LOBMarketMakerEnv
from lob_market_making_sim.io.loader import lobster_to_arrow, arrow_to_events
from pathlib import Path

def main():

    # Load events for one trading day
    BASE_DIR = Path(__file__).parent.parent.parent.parent.parent
    EVENT_SOURCE = BASE_DIR / "data" / "AMZN_2012-06-21_34200000_57600000_message_1.csv"
    MODEL_DEST = BASE_DIR / "src" / "lob_market_making_sim" / "models" / "rl" / "dqn_lob_market_maker"
    events_arrow = lobster_to_arrow(EVENT_SOURCE)
    events = arrow_to_events(events_arrow)

    # Create the environment
    env = LOBMarketMakerEnv(event_sequence=events)
    env = Monitor(env) # for TensorBoard logging

    # Create the agent
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=1e-4,
        buffer_size=50000,
        exploration_fraction=0.1,
        learning_starts=1000,
        batch_size=32,
        tau=1.0,
        target_update_interval=500,
        train_freq=1,
        gradient_steps=1,
        verbose=1,
        tensorboard_log="./logs"
    )

    # Evaluation callback
    eval_callback = EvalCallback(
        env,
        best_model_save_path="./models/",
        log_path="./logs/",
        eval_freq=5000,
        deterministic=True,
        render=False,
    )


    # Train the model
    model.learn(total_timesteps=100_000, callback=eval_callback)

    # Save the model
    model.save(MODEL_DEST)

if __name__ == "__main__":
    main()