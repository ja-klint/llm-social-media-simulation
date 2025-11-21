from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional

from openai import OpenAI
import time

# Define the response structures for LLM-outputs
class Bio(BaseModel):
    '''Defines agent's response format for bio.'''

    bio: str = Field(description='A short bio based on your persona. (max 160)', max_length=160)

class FeedAction(BaseModel):
    '''Defines agent's response format for actions on the feed page.'''
    
    action: Literal['REPOST', 'WRITE_POST', 'OBSERVE'] = Field(description='The specific action you want to take.')

    repost_target_id: Optional[int] = Field(default=None, description='If action is REPOST, provide the corresponding Post ID here. Otherwise null.')
    post_content: Optional[str] = Field(default=None, description='If action is WRITE_POST, write your post text here (max 280 chars). Otherwise null.', max_length=280)

    likes: list[int] = Field(default=[], description='List of Post IDs to like.')
    dislikes: list[int] = Field(default=[], description='List of Post IDs to dislike.')

    # ^^ ask for short explanation?

    # Raise error if LLM output is incorrect
    @model_validator(mode='after')
    def check_feed_actions(self):
        if self.action == 'REPOST' and self.repost_target_id == None:
            raise ValueError('Action is REPOST but no repost_target_id provided')
        
        if self.action == 'WRITE_POST' and not self.post_content:
            raise ValueError("Action is WRITE_POST but no post_content provided.")
            
        if self.action == 'OBSERVE':
            self.repost_target_id = None
            self.post_content = None
            
        return self

class ProfileAction(BaseModel):
    '''Defines agent's response format for action on another users profile page.'''

    action: Literal['FOLLOW', 'LEAVE'] = Field(description='The decision to follow this user or not.')

class Agent():

    # Defining a few variables that are used across all agents.
    llm_client: OpenAI = None # Set from simulation.py
    llm_model: str = None # Set from main.py
    request_control:str = '' # require human input before sending LLM request. 'auto' to disable.

    def __init__(self, a_id: int, agent_dict: dict):
        
        self.a_id: int = agent_dict['a_id']
        self.party: str = agent_dict['party']
        self.bio: str = agent_dict['bio']

        self.persona: str = agent_dict['persona']

        self.followers: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.following: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.liked_posts: list[int] = [] # list of PostIDs

    def __str__(self):
        return f'ID: {self.a_id}, Bio: {self.bio}'
    
    def generate_bio(self): # will likely move to persona_generator.py
        '''Prompt agent to write bio based on persona.'''

        prompt = '''Write a short (max 150 words) bio for your profile page.
Your bio should be based on your persona.'''

        bio: Bio = self.get_llm_response(prompt=prompt, response_format=Bio)
        
        return bio.bio
    
    def feed_action(self, post_feed: str, news_feed: str):
        '''Take actions on the feed page.
        
        1. Repost, post, or observe.
        2. Like & dislike posts.'''

        prompt = f'''You are viewing your social media feed.
You will choose an action and base your 
        
Choose exactly ONE of the following actions:
1. Repost: Share an existing post from your POST FEED, only if FEED is not empty.
2. Post News: Write a short post about one news headline in your NEWS FEED.
3. Observe.

You may also choose to like or dislike any number of posts from your POST FEED.
        
POST FEED:
{post_feed}

NEWS FEED:
{news_feed}'''
        
        action: FeedAction = self.get_llm_response(prompt, FeedAction)
        return action

    def profile_action(self, profile: str):
        '''Decide whether to follow the owner of a profile page.'''

        # Make customizable for different interventions (show follower count, political stance, etc..)
        prompt = f'''You are viewing a user's profile page.
Choose one of the following actions:
1. Follow the user.
2. Leave the profile.

PROFILE PAGE:
{profile}'''
        
        action: ProfileAction = self.get_llm_response(prompt, ProfileAction)

        return action

    def sys_instructions(self):
        '''Generates instructions to define Agent's persona and more.'''

        sys_msg = f'''You are a user on a social media platform.
On the platform you can repost, post, like, dislike, and follow others or just observe.

You have a persona with a distinct political identity and personality.
You must act consistently with this persona at all times.

The following is your persona:
{self.persona}'''

        return sys_msg
            
    def get_llm_response(self, prompt, response_format):

        model = Agent.llm_model
        sys_msg = self.sys_instructions()

        messages = [
            {"role": "system", "content": [{
                "type": "text",
                "text": sys_msg}]},
            {"role": "user", "content": [{
                "type": "text",
                "text": prompt}]}
                ]

        if Agent.request_control != 'auto':
            Agent.request_control = input(f'Agent {self.a_id} is about to send LLM request. Press Enter to continue...').strip()

        response = Agent.llm_client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format
        )
        time.sleep(0.12) # respect api rate limit

        return response.choices[0].message.parsed