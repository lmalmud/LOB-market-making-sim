# Limit Order Book Market Making Simulation

This project implements a high-frequency market-making simulation environment using limit order book (LOB) data. The pipeline spans from raw message ingestion to reinforcement learning-based quoting strategies.

---

## 📊 Project Overview

- **Data Source**: LOBSTER or NASDAQ ITCH tick data
- **Simulation Kernel**: Matching engine replays LOB events in time order
- **Strategies Implemented**:
  - Avellaneda–Stoikov baseline model
  - Reinforcement Learning (DQN & PPO) market maker
- **Evaluation**: PnL distribution, inventory heatmaps, adverse selection cost

---

## 🧩 Roadmap

### ✅ 3.1 Data Ingestion
- Parses nanosecond message logs into an event queue
- Outputs stored as pyarrow parquet for zero-copy slicing

### ✅ 3.2 Matching Engine
- Core order object and order book logic
- Priority queue updates and state tracking

### ✅ 3.3 Baseline Strategy
- Avellaneda–Stoikov spread formula
- Hooks into order placement with inventory-sensitive quotes

### 🚧 3.4 RL Market Maker (in progress)
- Gym-compatible LOB environment
- Reward: spread PnL − λ·|inventory| − α·inventory²
- Agents: DQN → PPO with RLlib/Stable-Baselines

### 🔜 3.5 Evaluation & Visualization
- Risk-adjusted returns, inventory heatmaps, Sharpe ratios
