from soc_platform import Platform
from agent import Agent, FeedAction, ProfileAction

from openai import OpenAI
from pathlib import Path

import time
import numpy as np
import json

class Simulation():

    def __init__(self, num_agents: int, num_timesteps: int, intervention: str, news_path: Path, openai_model: str = 'gpt-4o-mini', **kwargs):
        
        self.num_agents = num_agents
        self.num_timesteps = num_timesteps
        self.intervention = intervention
        self.openai_model = openai_model

        self.run_id = self.get_run_id(kwargs)
        self.agents_path = self.get_agents_path(kwargs)

        self.platform = Platform(intervention=self.intervention, agents=self.load_agents(), news_path=news_path)

        # Use same RNG seeds for corresponding runs for all interventions (blocking)
        self.agent_rng = np.random.default_rng([abs(self.run_id), 0]) # RNG generator for random agent selection
        self.news_rng = np.random.default_rng([abs(self.run_id), 1]) # RNG generator for random news feed creation
        
    def get_run_id(self, kwargs: dict[str, any]) -> int:
        '''Find highest run number in intervention and set run_id to next.'''
        r_id = kwargs.get('run_id', None)

        if r_id == None:
            data_dir = Path(__file__).parents[1].joinpath(f'data/{self.intervention}')
            files = [int(file.name.lstrip('run').rstrip('_timesteps.jsonl')) for file in data_dir.glob('*timesteps.jsonl') if file.is_file()]
            if files and max(files) > 0:
                r_id = max(files)+1
            else:
                r_id = 1

        return r_id
    
    def get_agents_path(self, kwargs: dict[str, any]) -> Path:
        '''Select agents for current run_id, or use provided Path.'''

        a_path = kwargs.get('agents_path', None)

        if a_path == None:
            a_path = Path(__file__).parents[1].joinpath(f'generate_agents/run{abs(self.run_id)}_agents.jsonl')

        assert a_path.is_file(), f'No file found at {a_path.name}. Please generate agents with agent_generator.py or provide file path explicitly.'
        return a_path

    def load_agents(self):
        with open(self.agents_path, 'r', encoding='utf-8', errors='ignore') as f:
            agent_list = [json.loads(line) for line in f]

        if len(agent_list) < self.num_agents:
            raise ValueError(f'agents_path includes {len(agent_list)} agents, num_agents is {self.num_agents}')
        
        return {agent_dict['agent_id']: Agent(agent_dict) for i, agent_dict in enumerate(agent_list) if i < self.num_agents}
        
    def pick_agent(self) -> Agent:
        '''Select random agent to act for the timestep. Using rng seed based on run_id.'''
        agent_ids = list(self.platform.agents.keys())
        return self.platform.agents[self.agent_rng.choice(agent_ids)]

    def log_timestep(self, agent_id: int,
                    action: str | None, post_id: int | None, post_content: str | None,
                    repost_target_id: int | None, liked_ids: list[int], disliked_ids: list[int],
                    followed_agent_id: int | None, shown_post_ids: list[int] | None):
        
        timestep_log = {'run_id': self.run_id, 'intervention': self.intervention, 'timestep': self.timestep, 'agent_id': agent_id, 'action': action, 'post_id': post_id, 'repost_target_id': repost_target_id,
                'liked_ids': liked_ids, 'disliked_ids': disliked_ids, 'followed_agent_id': followed_agent_id, 'shown_post_ids': shown_post_ids}
        log_path = Path(__file__).parents[1].joinpath(f'data/{self.intervention}/run{self.run_id}_timesteps.jsonl')

        log_path.parent.mkdir(exist_ok=True, parents=True) # create path
        with open (log_path, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(json.dumps(timestep_log, indent=None, ensure_ascii=False) + '\n')

        if action == 'WRITE_POST':
            self.log_post(post_id, post_content, agent_id)

    def log_post(self, post_id: int, content: str, author_id: int):
        post_data = {'run_id': self.run_id, 'intervention': self.intervention, 'timestep': self.timestep, 'agent_id': author_id, 'post_id': post_id, 'content': content}

        post_path = Path(__file__).parents[1].joinpath(f'data/{self.intervention}/run{self.run_id}_posts.jsonl')

        post_path.parent.mkdir(exist_ok=True, parents=True) # create path
        with open (post_path, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(json.dumps(post_data, indent=None, ensure_ascii=False) + '\n')
        

    def perform_timestep(self):
        # print('Timestep:', self.timestep)
        
        # # set default values for new timestep
            
        action = None
        post = None
        post_id = None
        post_content = None
        profile_action = None
        followed = None
        shown_post_ids = None
        
        # select one agent to perform actions
        agent: Agent = self.pick_agent()
        # print('Picked agent:', agent)

        # get feed, ask for action
        post_feed, shown_post_ids = self.platform.get_post_feed(agent)
        news_feed = self.platform.get_news_feed(self.news_rng)

        feed_action = agent.feed_action(post_feed=post_feed, news_feed=news_feed, shown_post_ids=shown_post_ids)
        action = feed_action.action
        repost_target_id = feed_action.repost_target_id

        if action == 'REPOST':
            
            post = self.platform.repost(timestep=self.timestep, author=agent, ref_post_id=repost_target_id)
            post_id = post.p_id
            self.platform.posts[repost_target_id].reposters.append(agent) # add agent to reposters
            
            # get profile of post author and ask to follow or not
            # only if agent is not already followed

            author = self.platform.get_author(post_id=repost_target_id)
            if author not in agent.following.values():
                profile = self.platform.get_profile(agent=author, viewer=agent)
                profile_action = agent.profile_action(profile=profile)

                if profile_action.action == 'FOLLOW':
                    followed = author.a_id
                    self.platform.register_follow(follower=agent, target=author)

        if action == 'WRITE_POST':
            # register post on platform and get Post object to log p_id and content
            post = self.platform.write_post(timestep=self.timestep, author=agent, content=feed_action.post_content)
            post_id = post.p_id
            post_content = post.content

        if action == 'OBSERVE':
            pass

        # only keep new likes and dislikes
        likes = list(set(feed_action.likes) - set(agent.liked_posts) - set(agent.disliked_posts))
        dislikes = list(set(feed_action.dislikes) - set(agent.liked_posts) - set(agent.disliked_posts))

        self.platform.register_likes(agent, likes)
        self.platform.register_dislikes(agent, dislikes)

        return (agent.a_id, action, post_id, post_content, repost_target_id, likes, dislikes, followed, shown_post_ids) # data to be logged

    def run(self, start_timestep: int = 1):
        '''Run a full simulation with given parameters.'''

        # Start timer
        start_time = time.time()
        
        # Init progress counter
        prev_progess = 0

        # Get timestep range
        timesteps = range(start_timestep, self.num_timesteps+1)

        # Initialize llm
        Agent.llm_client = OpenAI()
        Agent.llm_model = self.openai_model

        for timestep in timesteps:
            self.timestep = timestep

            # Print progress every 5% of timesteps
            progress = 100*timestep/timesteps[-1]
            if progress >= prev_progess + 5:
                bars = int(round(progress/5, 0))
                dashes = 20-bars
                progress_bar = '█'*bars + '-'*dashes

                elapsed_time = time.time()-start_time
                est_remain = int(round((elapsed_time/(progress/100) - elapsed_time), 0))
                est_time_str = f'{est_remain//3600}h : {est_remain%3600//60}m : {est_remain%60}s'
                        
                print(f'''
Progress: |{progress_bar}| {progress}% Complete
Estimated time remaining: {est_time_str}''')
                prev_progess += 5

            # Refresh client every 500 timesteps
            if timestep % 500 == 0:
                Agent.llm_client = OpenAI()
            
            finished_timestep = self.perform_timestep()
            self.log_timestep(*finished_timestep)
        
        ### After finished ###

        # Stop timer
        end_time = time.time()
        s = int(round((end_time-start_time), 0))
        finish_time_string = f'{s//3600}h : {s%3600//60}m : {s%60}s'

        # Get token usage and calculate cost
        total_input_tokens = sum(agent.used_tokens_input for agent in self.platform.agents.values())
        total_output_tokens = sum(agent.used_tokens_output for agent in self.platform.agents.values())
        total_cached_tokens = sum(agent.used_tokens_cached for agent in self.platform.agents.values())
        predicted_cost = round(((0.6 / 1000000) * total_output_tokens) + ((0.15 / 1000000) * (total_input_tokens - total_cached_tokens) + ((0.075 / 1000000) * total_cached_tokens)), 4)

        # Get request stats
        total_requests = sum(agent.requests for agent in self.platform.agents.values())
        total_responses = sum(agent.valid_responses for agent in self.platform.agents.values())
        total_refusals = sum(agent.req_refusals for agent in self.platform.agents.values())

        # Present info
        print(f'''
----------------------------------------------------------
Simulation finished!

Intervention: {self.intervention} | Run: {self.run_id}

Elapsed time: {finish_time_string}
Elapsed timesteps: {timesteps[-1]}

Total LLM requests: {total_requests}
Total LLM responses: {total_responses}
Total LLM refusals: {total_refusals}

Total input tokens: {total_input_tokens}
Total output tokens: {total_output_tokens}
Total cached tokens: {total_cached_tokens}
Predicted cost: ${predicted_cost} ≈ {round(predicted_cost*9.45, 2)} SEK
----------------------------------------------------------
''')

if __name__ == "__main__":
    # Example an test code:
    
    run_id = -110 # test id
    intervention = 'test'

    num_agents = 9
    num_timesteps = 100
    news_path = Path(__file__).parent.joinpath('News_Category_Dataset_v3.jsonl')
    agents_path = Path(__file__).parents[1].joinpath(f'generate_agents/test_agents.jsonl')

    simulation = Simulation(num_agents, num_timesteps, intervention, news_path, agents_path=agents_path, run_id=run_id)
    simulation.run()