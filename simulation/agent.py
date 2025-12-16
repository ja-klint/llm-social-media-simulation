from pydantic import BaseModel, Field, model_validator
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from typing import Literal, Optional
import logging

from openai import OpenAI

# Define the response structures for LLM-outputs
class FeedAction(BaseModel):
    '''Defines agent's response format for actions on the feed page.'''
    
    action: Literal['REPOST', 'WRITE_POST', 'OBSERVE'] = Field(description='The specific action you want to take.')

    repost_target_id: Optional[int] = Field(default=None, description='If action is REPOST, provide the corresponding Post ID here. Otherwise null.')
    post_content: Optional[str] = Field(default=None, description='If action is WRITE_POST, write your post text here (MAX 200 chars).', max_length=250)

    likes: list[int] = Field(default=[], description='List of Post IDs from POST FEED to like.')
    dislikes: list[int] = Field(default=[], description='List of Post IDs from POST FEED to dislike.')

    # Raise error if LLM output is incorrect
    @model_validator(mode='after')
    def check_feed_actions(self):
        if self.action == 'REPOST':
            if self.repost_target_id == None:
                raise ValueError('Action is REPOST but no repost_target_id provided')
            self.post_content = None
        
        if self.action == 'WRITE_POST':
            if not self.post_content:
                raise ValueError('Action is WRITE_POST but no post_content provided.')
            self.repost_target_id = None
            
        if self.action == 'OBSERVE':
            self.repost_target_id = None
            self.post_content = None

        # ensure only unique values
        self.likes = list(set(self.likes))
        self.dislikes = list(set(self.dislikes))
        if (set(self.likes) & set(self.dislikes)):
            raise ValueError('Same post in likes and dislikes!')
            
        return self

class ProfileAction(BaseModel):
    '''Defines agent's response format for action on another users profile page.'''

    action: Literal['FOLLOW', 'LEAVE'] = Field(description='The decision to follow this user or not.')

class Agent():

    # Log errors
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.ERROR)

    # Defining a few variables that are used across all agents.
    llm_client: OpenAI = None # Set from simulation.py
    llm_model: str = None # Set from main.py
    request_control:str = 'auto' # require human input before sending LLM request. 'auto' to disable.

    def __init__(self, agent_dict: dict):
        
        self.a_id: int = agent_dict['agent_id']
        self.party: str = agent_dict['party']
        self.bio: str = agent_dict['bio']

        self.persona: str = agent_dict['persona']

        self.followers: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.following: dict[int, Agent] = {} # key: AgentID, value: Agent object
        self.liked_posts: list[int] = [] # list of PostIDs
        self.disliked_posts: list[int] = [] # list of PostIDs

        # For tracking simulation info
        self.used_tokens_input: int = 0
        self.used_tokens_output: int = 0
        self.used_tokens_cached: int = 0

        self.requests: int = 0
        self.valid_responses: int = 0
        self.req_refusals: int = 0

    def __str__(self):
        return f'#{self.a_id}. {self.party}'
    
    def feed_action(self, post_feed: str, news_feed: str, shown_post_ids: list[int]):
        '''Produce actions on the feed page.'''

        prompt = f'''You are viewing the MAIN PAGE.

Choose exactly one primary action and which posts from the POST FEED to like/dislike.

MAIN PAGE:

POST FEED:
{post_feed}

NEWS FEED:
{news_feed}'''
        # print(prompt)
        action: FeedAction = self.produce_request(prompt, FeedAction, shown_post_ids)
        return action

    def profile_action(self, profile: str):
        '''Produce action on a profile page.'''

        prompt = f'''You are viewing a user's PROFILE PAGE.

Choose exactly one action.

PROFILE PAGE:
{profile}'''
        # print(prompt)
        action: ProfileAction = self.produce_request(prompt, ProfileAction)

        return action

    def sys_instructions(self):
        '''Generates instructions to define Agent's persona and set rules.'''

        sys_msg = f'''You are a user on a social media platform.

Your task is to choose actions based on the given persona and the current page.
You are on exactly one page at a time, specified in the user message.
You must choose exactly one primary action per page.

MAIN PAGE:
Primary actions:
- REPOST: share an existing post from the POST FEED (must align with persona; use an ID from POST FEED; only if POST FEED is not empty)
- OBSERVE: just observe.
- WRITE_POST: write a post based on one NEWS FEED headline (must align with persona; max 200 chars; do not repeat headline verbatim; no quotes or hashtags)

Secondary actions:
LIKE and DISLIKE any number of posts.
Like/dislike only IDs from POST FEED.
Never like and dislike the same post.

PROFILE PAGE:
Primary actions:
- FOLLOW the user.
- LEAVE without following.

PERSONA:
{self.persona}

BEHAVIOUR:
Your behavior must be strongly consistent with the persona.'''

        return sys_msg

    def get_llm_response(self, **kwargs):
        self.requests += 1
        return Agent.llm_client.beta.chat.completions.parse(**kwargs)

    def produce_request(self, prompt, response_format, shown_post_ids: list[int] = None):
        try:
            return self._produce_request_with_retry(prompt, response_format, shown_post_ids)
        except Exception as e:
            print(f'WARNING: Agent {self.a_id} forced OBSERVE fallback. Error: {e}')
            self.req_refusals += 1
            return response_format(action='OBSERVE')

    # Handle errors with tenacity
    @retry(
            before_sleep=before_sleep_log(logger, logging.ERROR),
            wait=wait_exponential(min=1, max=20),
            stop=stop_after_attempt(12)
    )
    def _produce_request_with_retry(self, prompt, response_format, shown_post_ids: list[int] = None):

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

        # Request break for testing
        if Agent.request_control != 'auto':
            Agent.request_control = input(f'Agent {self.a_id} is about to send LLM request. Press Enter to continue...').strip()

        # Send request
        response = self.get_llm_response(
            model=model,
            messages=messages,
            response_format=response_format,
            max_completion_tokens=1000
        )

        # Track token data
        self.used_tokens_input += response.usage.prompt_tokens
        self.used_tokens_output += response.usage.completion_tokens
        self.used_tokens_cached += response.usage.prompt_tokens_details.cached_tokens

        message = response.choices[0].message

        if message.refusal:
            self.req_refusals += 1
            raise ValueError('LLM refused response.')
        
        # Check for invalid likes, dislikes and reposts
        if shown_post_ids is not None:
            shown_set = set(shown_post_ids)

            invalid_likes = set(message.parsed.likes) - shown_set
            invalid_dislikes = set(message.parsed.dislikes) - shown_set
            invalid_repost = (message.parsed.action == 'REPOST' and message.parsed.repost_target_id not in shown_set)

            if invalid_likes or invalid_dislikes or invalid_repost:
                raise ValueError(
                    f"Invalid feed action by agent {self.a_id}: "
                    f"invalid_likes={invalid_likes}, "
                    f"invalid_dislikes={invalid_dislikes}, "
                    f"repost_target_id={message.parsed.repost_target_id}, "
                    f"shown_post_ids={shown_post_ids}"
                )


        self.valid_responses += 1
        return message.parsed