'''
train_rl.py
Trains the agent.

tensorboard --logdir=./logs
To run: poetry run python src/lob_market_making_sim/models/rl/train_rl.py
'''

import numpy as np
from pathlib import Path
import random

from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from lob_market_making_sim.models.rl.env import LOBMarketMakerEnv
from lob_market_making_sim.io.loader import lobster_to_arrow, arrow_to_events

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent
print(BASE_DIR)
DATA_DIR = BASE_DIR / "data"
MODEL_DEST = BASE_DIR / "src" / "lob_market_making_sim" / "models" / "rl" / "dqn_lob_market_maker"

def load_all_tickers_for_date(data_dir, date_str="2012-06-21"):
    '''
    Looks in the given data_dir and finds all available days of LOBSTER
    message data.
    Parameters:
    data_dir (str): path to the directory which will contain data for trading days
    date_str (str): the date to look for in files in the data directory
    Returns:
    List[str] of filepaths of found directories
    '''
    paths = list(data_dir.glob(f"*_{date_str}_*_message_1.csv"))
    paths.sort()
    print(f"Found {len(paths)} tickers for {date_str}")
    return paths

def make_env(path):
    '''
    Create a new environment per episode.
    Parameters:
    path: the datafile we would like to load into the environment
    Returns:
    _init (function) to create a new Gymnasium environment
    '''

    # Define a nested function
    # factories: functions that return other functions (often which
    # can create objects or environments with specific parameters)
    def _init():
        # Load events for one trading day
        events_arrow = lobster_to_arrow(path)
        events = arrow_to_events(events_arrow)
        env = LOBMarketMakerEnv(event_sequence=events)
        return Monitor(env) # for TensorBoard logging
    return _init

def main():

    # Will fetch all of the training data in the directory
    all_days = load_all_tickers_for_date(DATA_DIR)

    # Sample a random day per episode
    def random_env_fn():
        path = random.choice(all_days)
        return make_env(path)()
    
    # https://stable-baselines.readthedocs.io/en/master/guide/vec_envs.html
    # Method for stacking multiple independent environemnts into a single environment
    # Trains on n environments per step
    # Now, actions that are passed are of dimension n
    env = DummyVecEnv([random_env_fn])

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
    eval_env = make_env(all_days[0])() # Use one fixed day for evaluation
    eval_callback = EvalCallback(
        env,
        best_model_save_path="./models/",
        log_path="./logs/",
        eval_freq=5000,
        deterministic=True,
        render=False,
    )

    # Train the model
    model.learn(total_timesteps=200_000, callback=eval_callback)

    # Save the model
    model.save(MODEL_DEST)


if __name__ == "__main__":
    main()