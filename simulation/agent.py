from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Literal, Optional

from openai import OpenAI
import time

# Define the response structures for LLM-outputs
class FeedAction(BaseModel):
    '''Defines agent's response format for actions on the feed page.'''
    
    action: Literal['REPOST', 'WRITE_POST', 'OBSERVE'] = Field(description='The specific action you want to take.')

    repost_target_id: Optional[int] = Field(default=None, description='If action is REPOST, provide the corresponding Post ID here. Otherwise null.')
    post_content: Optional[str] = Field(default=None, description='If action is WRITE_POST, write your post text here (MUST be 50–200 chars).', max_length=250)

    likes: list[int] = Field(default=[], description='List of Post IDs from POST FEED to like.')
    dislikes: list[int] = Field(default=[], description='List of Post IDs from POST FEED to dislike.')

    # Raise error if LLM output is incorrect
    @model_validator(mode='after')
    def check_feed_actions(self):
        if self.action == 'REPOST' and self.repost_target_id == None:
            raise ValueError('Action is REPOST but no repost_target_id provided')
        
        if self.action == 'WRITE_POST':
            if not self.post_content:
                raise ValueError('Action is WRITE_POST but no post_content provided.')
            
        if self.action == 'OBSERVE':
            self.repost_target_id = None
            self.post_content = None

        # ensure only unique values
        self.likes = list(set(self.likes))
        self.dislikes = list(set(self.dislikes))
        if (set(self.likes) & set(self.dislikes)):
            input('WARNING! Same post in likes and dislikes!')
            
        return self

class ProfileAction(BaseModel):
    '''Defines agent's response format for action on another users profile page.'''

    action: Literal['FOLLOW', 'LEAVE'] = Field(description='The decision to follow this user or not.')

class Agent():

    # Defining a few variables that are used across all agents.
    llm_client: OpenAI = None # Set from simulation.py
    llm_model: str = None # Set from main.py
    request_control:str = '' # require human input before sending LLM request. 'auto' to disable.

    def __init__(self, agent_dict: dict):
        
        self.a_id: int = agent_dict['agent_id']
        self.party: str = agent_dict['party']
        self.bio: str = agent_dict['bio']

        self.persona: str = agent_dict['persona']

        self.followers: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.following: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.liked_posts: list[int] = [] # list of PostIDs
        self.disliked_posts: list[int] = [] # list of PostIDs

    def __str__(self):
        return f'#{self.a_id}. {self.party}'
    
    def feed_action(self, post_feed: str, news_feed: str):
        '''Take actions on the feed page.
        
        1. Repost, post, or observe.
        2. Like & dislike posts.'''

        prompt = f'''You are viewing your social media feed.

Choose one action and which POST FEED IDs to like/dislike.

Output only the JSON required by the schema. No explanations.

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

Choose one:
1. FOLLOW the user.
2. LEAVE the profile.

Output only the JSON required by the schema. No explanations.

PROFILE PAGE:
{profile}'''
        
        action: ProfileAction = self.get_llm_response(prompt, ProfileAction)

        return action

    def sys_instructions(self):
        '''Generates instructions to define Agent's persona and more.'''

        sys_msg = f'''You are a user on a social media platform. Follow these rules exactly.
OUTPUT: Only a JSON object matching the schema. No extra text.

ACTIONS:
- Choose exactly one: REPOST, WRITE_POST, or OBSERVE.
- REPOST: set repost_target_id to an ID from POST FEED. NEVER invent IDs.
- WRITE_POST: base on exactly one NEWS_FEED headline; length 50–200 chars; do not repeat the headline verbatim; no hashtags.
- OBSERVE: post_content and repost_target_id must be null.

LIKES/DISLIKES:
- Like/dislike only IDs from POST FEED.
- Never like and dislike the same post.

PROFILE:
- Choose exactly one: FOLLOW or LEAVE.

PRIORITY: These rules override persona. After rules, act in character per persona.

FINAL CHECK (internal): verify all rules and that JSON matches schema.

PERSONA:
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
            response_format=response_format,
            max_completion_tokens=1000
        )
        time.sleep(0.12) # respect api rate limit

        return response.choices[0].message.parsed