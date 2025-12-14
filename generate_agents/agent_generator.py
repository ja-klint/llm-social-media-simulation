import json
from pathlib import Path
import numpy as np

# file with personas to pick from, should be in parent folder
from_file = 'all_personas.json'

# file to save personas to
to_file = 'run3_agents.jsonl'

run_id = 3

num_of_democrats = 22
num_of_republicans = 22
num_of_nonpartisan = 6

party_counts = {
    'Democrat': num_of_democrats,
    'Republican': num_of_republicans,
    'Non-partisan': num_of_nonpartisan
}

total_number_of_agents = num_of_democrats + num_of_republicans + num_of_nonpartisan

rng = np.random.default_rng(run_id)

print('Total number of Agents to generate:', total_number_of_agents)
print(f'Democrats: {100*round(num_of_democrats/total_number_of_agents, 3)}% | Republicans: {100*round(num_of_republicans/total_number_of_agents, 3)}% | Non-partisan: {100*round(num_of_nonpartisan/total_number_of_agents, 3)}%')
input('\nPress ENTER to proceed.')

from_path = Path(__file__).parent / from_file
to_path = Path(__file__).parent / to_file
to_path.parent.mkdir(exist_ok=True, parents=True) # create path

if to_path.is_file():
    print(f'WARNING! This will override the existing file with path:\n{to_path}')
    input('\nPress ENTER to proceed.')

try:
    with open(from_path, 'r', encoding='utf-8', errors='ignore') as f:
        agent_data: list = json.load(f)
    rng.shuffle(agent_data)

    with open(to_path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write('')
    
except:
    raise

agent_list = []
a_id = 1

for selected_agent in agent_data:

    party = selected_agent['party']

    if party_counts[party] > 0:
        agent = {
            'agent_id': a_id,
            'party': selected_agent['party'],
            'bio': selected_agent['bio'],
            'persona': selected_agent['persona'].rstrip()}

        print(f'Selected {party} #{party_counts[party]}')

        party_counts[party] -= 1

        with open(to_path, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(f'{json.dumps(agent, indent=None, ensure_ascii=False)}\n')
        
        a_id += 1

    if a_id > total_number_of_agents:
        break