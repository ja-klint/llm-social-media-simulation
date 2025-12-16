from simulation import Simulation
from dotenv import load_dotenv
from pathlib import Path

# Load OpenAI api key from path
load_dotenv(dotenv_path='simulation/api_keys.env')

# Interventions: 'CONTROL', 'SOCIAL_PROOF', 'IDENTITY'
# intervention = 'CONTROL'
# intervention = 'SOCIAL_PROOF'
intervention = 'IDENTITY'
run_id = 3

num_agents = 50
num_timesteps = 2000

news_path = Path(__file__).parent.joinpath('News_Category_Dataset_v3.jsonl')

simulation = Simulation(num_agents, num_timesteps, intervention, news_path, run_id=run_id)
simulation.run()