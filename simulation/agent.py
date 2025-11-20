from pydantic import BaseModel, Field
from openai import OpenAI

class FeedActions(BaseModel):
    '''Defines agent's response format on the feed page.'''
    
    primary: int = Field(description='The primary action chosen: 1 (Repost), 2 (Post News), or 3 (Observe).')
    content: str = Field(description='If option 1: the Post ID (example: P1. If option 2: the content of your new post. If option 3: an empty string.')
    # explanation: str = Field(description="A brief explanation for the primary action choice.")
    
    likes: list[int] = Field(description='A list of Post IDs from the timeline that you choose to "like". Can be an empty list [].')
    dislikes: list[int] = Field(description='A list of Post IDs (example: P4) from the timeline that you choose to "dislike". Can be an empty list [].')

class ProfileAction(BaseModel):
    '''Defines agent's response format on another users profile page.'''

    follow: bool = Field(description='True (Follow user) or False (Do not follow user)')
    # explanation: str = Field(description='A brief explanation for your choice')

class Agent():

    llm_client: OpenAI = OpenAI() # Later changed to None and set from main
    llm_model: str = 'gpt-4o-mini' # Later changed to None and set from main

    def __init__(self, id: int, persona: str):
        self.id: str = id # example: A123
        self.persona = ''
        self.followers: list[Agent] = []
        self.following: list[Agent] = []
        self.liked_posts: list[str] = [] # list of PostIDs

    def sys_instructions(self):
        '''Generates instructions to define Agent's persona and more.'''

        sys_msg = f'''You are a user on a social media platform.
On the platform you can repost, post, like, dislike, follow others or just observe.

You have a persona with a distinct political identity and personality. 
You must act consistently with this persona at all times. 

The following is your persona:
{self.persona['persona']}
'''

        return sys_msg
    
    def view_feed(self):

        prompt = f'''''' # Generate prompt with posts and news feed.
        # Make customizable for different interventions (show likes, dislikes, poster political stance, etc..)
        
        actions = self.get_llm_response(prompt, FeedActions)
        
    def get_llm_response(self, prompt, resp_form):

        model = Agent.llm_model
        sys_msg = self.sys_instructions()

        messages = [
            {"role": "system", "content": [{
                "type": "input_text",
                "text": sys_msg}]},
            {"role": "user", "content": [{
                "type": "input_text",
                "text": prompt}]}
                ]

        response = Agent.llm_client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=resp_form
        )

        return response.choices[0]