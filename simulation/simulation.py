from soc_platform import Platform
from agent import Agent, FeedAction, ProfileAction

from openai import OpenAI
from pathlib import Path

import random
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path='simulation/api_keys.env') # temp fix


class Simulation():

    def __init__(self, num_agents: int, num_timesteps: int, intervention: str, agents_path: Path, news_path: Path, openai_model: str = 'gpt-4o-mini', **kwargs):
        
        self.num_agents = num_agents
        self.num_timesteps = num_timesteps
        self.intervention = intervention
        self.agents_path = agents_path
        # self.news_path = news_path # OLD
        self.openai_model = openai_model
        self.kwargs = kwargs

        self.run_id = self.get_run_id()
        self.platform = Platform()
        self.platform.agents = self.load_agents()
        # self.platform.headlines = self.load_news() # OLD
        self.platform.news_path = news_path
        
    def get_run_id(self) -> int:
        r_id = self.kwargs.get('run_id', None)
        if r_id == None:
            # Get next run_id (take max from existing run files)
            r_id = 0 # TODO Set automatically

        return r_id

    def load_agents(self):
        with open(self.agents_path, 'r', encoding='utf-8', errors='ignore') as f:
            agent_list = [json.loads(line) for line in f]

        return {agent_dict['agent_id']: Agent(agent_dict) for i, agent_dict in enumerate(agent_list) if i < self.num_agents}
    
    # def load_news(self):
    #     with open(self.news_path, 'r', encoding='utf-8', errors='ignore') as f:
    #         return [hl.rstrip() for hl in f.readlines()]
        
    def pick_agent(self):
        return self.platform.agents[random.randint(1, len(self.platform.agents))]

    def log_timestep(self, agent_id: int,
                    action: str | None, post_id: int | None, post_content: str | None,
                    repost_target_id: int | None, liked_ids: list[int], disliked_ids: list[int],
                    followed_agent_id: int | None):
        
        timestep_log = {'run_id': self.run_id, 'intervention': self.intervention, 'timestep': self.timestep, 'agent_id': agent_id, 'action': action, 'post_id': post_id, 'repost_target_id': repost_target_id,
                'liked_ids': liked_ids, 'disliked_ids': disliked_ids, 'followed_agent_id': followed_agent_id}
        log_path = Path(__file__).parents[1].joinpath(f'data/{self.intervention}/run{self.run_id}_timesteps.jsonl')

        log_path.parent.mkdir(exist_ok=True, parents=True) # create path
        with open (log_path, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(json.dumps(timestep_log, indent=None, ensure_ascii=False) + '\n')

        if action == 'WRITE_POST':
            self.log_post(post_id, post_content, agent_id)

    def log_post(self, post_id: int, content: str, author_id: int):
        post_data = {'run_id': self.run_id, 'intervention': self.intervention, 'timestep': self.timestep, 'post_id': post_id, 'content': content, 'agent_id': author_id}

        post_path = Path(__file__).parents[1].joinpath(f'data/{self.intervention}/run{self.run_id}_posts.jsonl')

        post_path.parent.mkdir(exist_ok=True, parents=True) # create path
        with open (post_path, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(json.dumps(post_data, indent=None, ensure_ascii=False) + '\n')
        

    def perform_timestep(self):
        print('Timestep:', self.timestep)
        
        # # set default values for new timestep
            
        post = None
        post_id = None
        post_content = None
        
        profile_action = None
        followed = None
        
        # agent, feed_action, profile_action = [None]*3

        # select one agent to perform actions
        agent: Agent = self.pick_agent()
        print('Picked agent:', agent)

        # get feed, ask for action
        post_feed = self.platform.get_post_feed(agent)
        news_feed = self.platform.get_news_feed() # fix to not load file each time

        feed_action = agent.feed_action(post_feed=post_feed, news_feed=news_feed)
        repost_target_id = feed_action.repost_target_id
        print('---------------------------------------------------------------------')
        print(feed_action.action)
        print(feed_action.post_content)

        if feed_action.action == 'REPOST':
            
            # get profile of post author and ask to follow or not
            # only if agent is not already followed

            post = self.platform.repost(timestep=self.timestep, author=agent, ref_post_id=repost_target_id)
            post_id = post.p_id
            
            self.platform.posts[repost_target_id].reposters.append(agent) # add agent to reposters

            author = self.platform.get_author(post_id=repost_target_id)
            if author not in agent.following.values():
                profile = self.platform.get_profile(agent=author, viewer=agent)
                profile_action = agent.profile_action(profile=profile)
                print(profile_action.action)

                if profile_action.action == 'FOLLOW':
                    followed = author.a_id
                    self.platform.register_follow(follower=agent, target=author)

                else:
                    followed = None
        else:
            profile_action = None
            followed = None

        if feed_action.action == 'WRITE_POST':
            # register post on platform and get Post object to log
            post = self.platform.write_post(timestep=self.timestep, author=agent, content=feed_action.post_content)
            post_id = post.p_id
            post_content = post.content

        if feed_action.action == 'OBSERVE':
            action = None
        else:
            action = feed_action.action

        # only keep new likes and dislikes
        likes = list(set(feed_action.likes) - set(agent.liked_posts))
        dislikes = list(set(feed_action.dislikes) - set(agent.disliked_posts))

        self.platform.register_likes(agent, likes)
        self.platform.register_dislikes(agent, dislikes)

        return (agent.a_id, action, post_id, post_content, repost_target_id, likes, dislikes, followed) # data to be logged

    def run(self, start_timestep: int = 1):
        '''Run a full simulation with given parameters.'''

        # Get timestep queue
        timesteps = range(start_timestep, self.num_timesteps+1)

        # Initialize llm
        Agent.llm_client = OpenAI()
        Agent.llm_model = self.openai_model

        for timestep in timesteps:
            self.timestep = timestep
            
            finished_timestep = self.perform_timestep()
            self.log_timestep(*finished_timestep)

    def _WIP_continue_run(self, add_timesteps: int = 0):
        '''Continue a previously started simulation.

        :param int add_timesteps: Leave as 0 to continue unfinished simulations.
        '''

        # get saved state from files and set following variables
        
        
        num_agents: int
        num_timesteps: int # add add_timesteps
        intervention: str
        current_timestep: int
        openai_model: str

        self.run(start_timestep=current_timestep+1)


if __name__ == "__main__":
    # Example and test code:
    
    run_id = -9 # test id
    intervention = 'test'

    num_agents = 5
    num_timesteps = 25
    agents_path = Path(__file__).parents[1].joinpath(f'generate_agents/agents.jsonl')
    news_path = Path(__file__).parent.joinpath('News_Category_Dataset_v3.jsonl')

    simulation = Simulation(num_agents, num_timesteps, intervention, agents_path, news_path, run_id=run_id)
    simulation.run()

    print('-------------------\nSimulation finished!')