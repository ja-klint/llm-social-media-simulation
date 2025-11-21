from agent import Agent
import random

class Post():
    def __init__(self, p_id: int, author: Agent, content: str, timestep: int):
        self.p_id = p_id
        self.author = author
        self.content = content
        self.created_timestep: int = timestep

        self.likes: int = 0
        self.dislikes: int = 0

class Platform():
    def __init__(self, agents: dict[int, Agent] = {}, posts: dict[int, Post] = {}):
        self.agents: dict[int, Agent] = agents # key: AgentID, value: Agent object
        self.posts: dict[int, Post] = posts # key: PostID, value: Post object
        self.headlines: list[str] = []
    
    def get_post_feed(self, viewer: Agent, number: int = 8) -> str:
        '''Generate string representation of an agent's post feed.'''
        
        # Pick {number} posts from self.posts
        # Use if statements to customize what info is shown based on intervention
        post_feed = ''
        post_list = []

        if True: # Change to if intervention == reverse chronological
            all_p_ids = list(self.posts.keys())
            all_p_ids.sort(reverse=True)

            for i in all_p_ids:
                post = self.posts[i]
                if (post.author != viewer):
                    post_list.append(post)
                
                # break at desired number
                if len(post_list) >= number:
                    break


        for post in post_list:
            profile += f'''\n\n{post}'''

        if post_feed == '':
            post_feed = 'Empty'

        return post_feed

    def get_news_feed(self, number: int = 6) -> str:
        '''Generate string representation of the news feed.'''

        # Pick {number} random news stories from self.headlines
        news_feed = ''
        headlines = random.sample(self.headlines, number) # Maybe remove already presented or posted news?
        for i, hl in enumerate(headlines):
            news_feed += f'\n{i}. {hl}'

        return news_feed
    
    def get_author(self, post: Post | None = None, post_id: int | None = None) -> Agent:
        '''Get author from Post object or post_id.'''

        if post:
            return post.author
        if post_id:
            return self.posts[post_id].author
    
    def get_profile_posts(self, agent: Agent) -> list[Post]:
        '''Get the most recent posts from agent.'''

        recent_posts = []
        all_p_ids = list(self.posts.keys())
        all_p_ids.sort(reverse=True)


        for i in all_p_ids:
            post = self.posts[i]
            if post.author == agent:
                recent_posts.append(post)

            # break at desired number
            if len(recent_posts) >= 5:
                break

        return recent_posts
    
    def get_mutual_follows(self, agent1: Agent, agent2: Agent):
        '''Return the number of '''

    def get_profile(self, agent: Agent, viewer: Agent) -> str:
        '''Generate string representation of an agent's profile.'''

        agent_id = agent.a_id
        followers = agent.followers
        party = agent.party

        bio = agent.bio
        recent_posts = self.get_profile_posts(agent=agent)

        # Construct profile page based on intervention
        profile = f'AgentID: {agent_id}'
        
        if True:
            profile += f'\nFollowers: {followers}'
        profile += f'\n\nBio: {bio}'
        
        if True:
            profile += f'\nPolitical party: {party}'
        
        profile += f'\n\nBio: {bio}'

        profile += '\n\nRecent posts:'
        for post in recent_posts:
            profile += f'''\n\n{post}'''

        return profile

    def write_post(self, author: Agent, content: str, timestep: int) -> Post:
        # get next post_id and create Post object
        if self.posts:
            post_id = int(max(self.posts.keys())+1)
        else:
            post_id = 1

        new_post = Post(post_id, author, content, timestep)

        # add post to platform
        self.posts[post_id] = new_post
        return new_post
    
    def register_likes(self, post_ids: list[int]):
        '''Increment likes attribute for Post objects'''

        for post_id in post_ids:
            self.posts[post_id].likes += 1
    
    def register_dislikes(self, post_ids: list[int]):
        '''Increment dislikes attribute for Post objects'''

        for post_id in post_ids:
            self.posts[post_id].dislikes += 1