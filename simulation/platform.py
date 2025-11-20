from agent import Agent

class Post():
    def __init__(self, id: str, author: Agent, content: str, timestep: int):
        self.id = id # example: P67
        self.author = author
        self.content = ''
        self.created_timestep: int = timestep

        self.likes: int = 0
        self.dislikes: int = 0

class Platform():
    def __init__(self):
        pass 