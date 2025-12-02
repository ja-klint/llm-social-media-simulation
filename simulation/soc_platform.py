from agent import Agent

from pathlib import Path
import json
import random

class Post():
    def __init__(self, timestep: int, p_id: int, author: Agent, content: str, is_repost: bool, ref_post_id: int | None = None):
        self.created_timestep: int = timestep
        self.p_id = p_id
        self.author = author
        self.content = content
        self.is_repost = is_repost
        self.ref_post_id = ref_post_id

        self.likes: list[Agent] = []
        self.dislikes: list[Agent] = []

class Platform():
    def __init__(self, agents: dict[int, Agent] = {}, posts: dict[int, Post] = {}):
        self.agents: dict[int, Agent] = agents # key: a_id, value: Agent object
        self.posts: dict[int, Post] = posts # key: p_id, value: Post object
        self.news_path: Path
    
    def get_post_feed(self, viewer: Agent, number: int = 8) -> str:
        '''Generate string representation of an agent's post feed.'''

        # TODO dont show same post twice,
        
        # Pick {number} posts from self.posts
        # Use if statements to customize what info is shown based on intervention
        post_list: list[Post] = []

        if True: # Change to if intervention == reverse chronological
            
            # select most recent posts that are not from the viewing agent
            all_p_ids = list(self.posts.keys())
            all_p_ids.sort(reverse=True)

            for i in all_p_ids:
                post = self.posts[i]
                if (post.author != viewer): # filter out feed viewers own posts
                    post_list.append(post)
                
                # break at desired number of posts
                if len(post_list) >= number:
                    break

        # add posts to feed string
        post_feed = ''
        for post in post_list:
            post_feed += f'Post ID: {post.p_id}'
            post_feed += f'\nLikes: {len(post.likes)}'
            post_feed += f'\nDislikes: {len(post.dislikes)}'
            post_feed += f'\nContent: {post.content}\n\n'
            

        if post_feed == '':
            post_feed = 'Empty'

        return post_feed.rstrip()
    
    def get_news_feed(self, number: int = 6) -> str:
        '''Generate string representation of the news feed.'''

        # load all news_articles
        with open(self.news_path, 'r', encoding='utf-8', errors='ignore') as f:
            news_data = [json.loads(line) for line in f]

        # select random (by category for intervention?)
        news_articles = random.sample(news_data, number)
        news_feed = ''
        for news_item in news_articles:
            news_feed += f'Headline: {news_item['headline']}\nDescription: {news_item['short_description']}\n\n'

        return news_feed.rstrip()
    
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
            if len(recent_posts) >= 3:
                break

        return recent_posts
    
    def get_mutual_follows(self, agent1: Agent, agent2: Agent):
        '''Return the number of '''
        pass # prob remove

    def get_profile(self, agent: Agent, viewer: Agent) -> str:
        '''Generate string representation of an agent's profile.'''

        agent_id = agent.a_id
        followers = len(agent.followers)
        party = agent.party

        bio = agent.bio
        recent_posts = self.get_profile_posts(agent=agent)

        # Construct profile page based on intervention
        profile = f'User ID: {agent_id}'
        
        if True:
            profile += f'\nPolitical party: {party}'
        
        if True:
            profile += f'\nFollowers: {followers}'
        
        profile += f'\nBio: {bio}'
        
        profile += '\n\nRecent posts and reposts:\n'
        for post in recent_posts:
            profile += f'Post ID: {post.p_id}'
            profile += f'\nLikes: {len(post.likes)}'
            profile += f'\nDislikes: {len(post.dislikes)}'
            profile += f'\nContent: {post.content}\n\n'

        return profile.rstrip()

    def write_post(self, timestep: int, author: Agent, content: str, is_repost: bool = False, ref_post_id: int | None = None) -> Post:
        # get next post_id and create Post object
        if self.posts:
            post_id = int(max(self.posts.keys())+1)
        else:
            post_id = 1

        new_post = Post(timestep, post_id, author, content, is_repost, ref_post_id)

        # add post to platform
        self.posts[post_id] = new_post
        return new_post
    
    def register_likes(self, agent: Agent, post_ids: list[int]):
        '''Add agent to likes list for Post objects'''

        for post_id in post_ids:
            if agent not in self.posts[post_id].likes:
                self.posts[post_id].likes.append(agent)
    
    def register_dislikes(self, agent: Agent, post_ids: list[int]):
        '''Add agent to dislikes list for Post objects'''

        for post_id in post_ids:
            if agent not in self.posts[post_id].dislikes:
                self.posts[post_id].dislikes.append(agent)