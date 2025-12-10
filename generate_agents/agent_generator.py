import json
from pathlib import Path
import random

# file with personas to pick from, should be in parent folder
from_file = 'all_personas.json'

# file to save personas to
to_file = 'run3_agents.jsonl'

num_of_democrats = 22
num_of_republicans = 22
num_of_nonpartisan = 6
# num_of_democrats = 2
# num_of_republicans = 2
# num_of_nonpartisan = 1
total_number_of_agents = num_of_democrats + num_of_republicans + num_of_nonpartisan

print('Total number of Agents to generate:', total_number_of_agents)
print(f'Democrats: {num_of_democrats/total_number_of_agents}% | Republicans: {num_of_republicans/total_number_of_agents}% | Non-partisan: {num_of_nonpartisan/total_number_of_agents}%')
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
    with open(to_path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write('')
    
except:
    raise

agent_list = []
a_id = 1
while num_of_democrats > 0 or num_of_republicans > 0 or num_of_nonpartisan > 0:
    random_index = random.randrange(len(agent_data))
    selected_agent = agent_data.pop(random_index) # avoid duplicates

    agent = {
        'agent_id': a_id,
        'party': selected_agent['party'],
        'bio': selected_agent['bio'],
        'persona': selected_agent['persona']}

    if agent['party'] == 'Democrat' and num_of_democrats > 0:
        print(f'Selected {agent['party']} #{num_of_democrats}')
        num_of_democrats -= 1

    elif agent['party'] == 'Republican' and num_of_republicans > 0:
        print(f'Selected {agent['party']} #{num_of_republicans}')
        num_of_republicans -= 1

    elif agent['party'] == 'Non-partisan' and num_of_nonpartisan > 0:
        print(f'Selected {agent['party']} #{num_of_nonpartisan}')
        num_of_nonpartisan -= 1

    else:
        continue # skip if all spots for selected party are taken

    with open(to_path, 'a', encoding='utf-8', errors='ignore') as f:
        f.write(f'{json.dumps(agent, indent=None, ensure_ascii=False)}\n')

    a_id += 1