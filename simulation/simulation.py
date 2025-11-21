from soc_platform import Platform
from agent import Agent, FeedAction, ProfileAction

from openai import OpenAI
from pathlib import Path

import random
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path='llm-social-media-simulation/simulation/api_keys.env') # temp fix

def pick_agent(agents: dict[int, Agent]):
    return agents[random.randint(1, len(agents))]

def log_timestep(run_id: int, intervention: str, timestep: int, agent_id: int,
                action: str | None, new_post_id: int | None, repost_target_id: int | None,
                liked_ids: list[int], disliked_ids: list[int],
                followed_agent_id: int | None):
    
    data = {'run_id': run_id, 'intervention': intervention, 'timestep': timestep, 'agent_id': agent_id, 'action': action, 'new_post_id': new_post_id, 'repost_target_id': repost_target_id,
            'liked_ids': liked_ids, 'disliked_ids': disliked_ids, 'followed_agent_id': followed_agent_id}
    log_path = Path(__file__).parents[1].joinpath(f'data/{intervention}/run{run_id}_timesteps.jsonl')

    log_path.parent.mkdir(exist_ok=True, parents=True)
    with open (log_path, 'a', encoding='utf-8', errors='ignore') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def run_simulation(num_agents: int, num_timesteps: int, agents_path: Path, news_path: Path, intervention: str, start_timestep: int = 1, openai_model: str = 'gpt-4o-mini', **kwargs):
    '''Run a full simulation with given parameters.'''

    run_id = kwargs.get('run_id', None)
    if run_id == None:
        # Get next run_id
        # (take max from existing run files?)

        run_id = 0 # temporary

    # Initialize platform
    platform = Platform()

    # Initialize agents
    Agent.llm_client = OpenAI()
    Agent.llm_model = openai_model

    # Load agents
    with open(agents_path, 'r', encoding='utf-8', errors='ignore') as f:
        agent_data = [json.loads(line) for line in f]
    # print(agent_data)
    platform.agents = {(a_id+1): Agent(a_id+1, agent_dict) for a_id, agent_dict in enumerate(agent_data) if a_id < num_agents}
    print(len(platform.agents))
    print(platform.agents)
    for k, v in platform.agents.items():
        print(k)

    input('Check')

    # Load news
    with open(news_path, 'r', encoding='utf-8', errors='ignore') as f:
        platform.headlines = [hl.rstrip() for hl in f.readlines()]
    print(platform.headlines[:10])

    input('Check')

    for timestep in range(start_timestep, num_timesteps+1): # Maybe create timestep function and Simulation class
        print('Timestep:', timestep)
        # set default values for new timestep
        agent, feed_action, profile_action = [None]*3

        # select one agent to perform actions
        agent = pick_agent(platform.agents)
        print('Agent picked:', agent)
        input('Check')

        # get feed, ask for action
        post_feed = platform.get_post_feed(agent)
        print(f'Post feed:\n{post_feed}')
        news_feed = platform.get_news_feed()
        print(f'News feed:\n{news_feed}')

        # finish platform.get_post_feed() and platfom.get_news_feed() before continuing.

        feed_action = agent.feed_action(post_feed=post_feed, news_feed=news_feed)
        print(feed_action.action)
        print(feed_action.post_content)
        input()

        if feed_action.action == 'REPOST':
            # get profile of post author and ask to follow or not
            author = platform.get_author(feed_action.repost_target_id)
            profile = platform.get_profile(agent=author, viewer=agent)

            print('Author', author)
            print('Profile:', profile)
            input('Check')
            profile_action = agent.profile_action(profile=profile)

            if profile_action.action == 'FOLLOW':
                followed = author.a_id
            else:
                followed = None
        else:
            profile_action = None
            followed = None

        if feed_action.action == 'WRITE_POST':
            # register post on platform and get Post object to log
            post = platform.write_post(author=agent, content=feed_action.post_content, timestep=timestep)
            post_id = post.p_id
        else:
            post = None
            post_id = None

        if feed_action.action == 'OBSERVE':
            action = None
        else:
            action = feed_action.action

        likes = feed_action.likes
        dislikes = feed_action.dislikes

        platform.register_likes(likes)
        platform.register_dislikes(dislikes)

        repost_target_id = feed_action.repost_target_id
        
        log_timestep(run_id=run_id, intervention=intervention, timestep=timestep, agent_id=agent.a_id, action=action, new_post_id=post_id, repost_target_id=repost_target_id, liked_ids=likes, disliked_ids=dislikes, followed_agent_id=followed)

def continue_run(run_id: int, add_timesteps: int = 0):
    '''Continue a previously started simulation run.

    :param int run_id: The id of the simulation run to continue.
    :param int add_timesteps: Leave as 0 to continue unfinished simulations.
    '''

    # get saved state from files and set following variables
    num_agents: int

    num_timesteps: int # add add_timesteps

    intervention: str
    current_timestep: int
    openai_model: str

    run_simulation(num_agents=num_agents, num_timesteps=num_timesteps, intervention=intervention, openai_model=openai_model, start_timestep=current_timestep+1, run_id=run_id)


if __name__ == "__main__":
    # Example and test code:
    
    num_agents = 5
    num_timesteps = 10
    agents_path = Path(__file__).parents[1].joinpath(f'generate_personas/test_personas.jsonl')
    news_path = Path(__file__).parents[1].joinpath(f'generate_personas/test_news.txt')
    intervention = 'none'
    
    # run_simulation(num_agents, num_timesteps, agents_path, news_path, intervention)
    print("FIX POST FEED AND PROFILE FEED!")
    print("SHOW POST_ID AND CONTENT + maybe more")
    
    pass
