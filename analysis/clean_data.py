import os
import pandas as pd
import numpy as np
from pathlib import Path

def load_data(data_path: Path, agents_path: Path, interventions: list[str], runs: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    
    all_timesteps = []
    all_posts = []
    all_agents = []

    for inv in interventions:
        for run in range(runs+1):

            # Load Timesteps
            t_file = data_path.joinpath(f"{inv}/run{run}_timesteps.jsonl")
            if os.path.exists(t_file):
                df_t = pd.read_json(t_file, lines=True)
                all_timesteps.append(df_t)
                
            # Load Posts
            p_file = data_path.joinpath(f"{inv}/run{run}_posts.jsonl")
            if os.path.exists(p_file):
                df_p = pd.read_json(p_file, lines=True)
                all_posts.append(df_p)

            # Load agents
            a_file = agents_path.joinpath(f'run{run}_agents.jsonl')
            if os.path.exists(a_file):
                df_a = pd.read_json(a_file, lines=True)
                df_a.insert(0, "intervention", inv)
                df_a.insert(0, "run_id", run)
                all_agents.append(df_a)
    
    df_agents: pd.DataFrame = pd.concat(all_agents, ignore_index=True)
    df_timesteps: pd.DataFrame = pd.concat(all_timesteps, ignore_index=True)
    df_posts: pd.DataFrame = pd.concat(all_posts, ignore_index=True)
    
    return (df_timesteps, df_posts, df_agents)

def prepare_t(df_t: pd.DataFrame) -> pd.DataFrame:
    '''
    Add is_follow (0|1) and changed some floats to Int64 for each timestep.
    
    :param df_t: Timesteps dataframe
    :type df_t: DataFrame
    :return: Timesteps dataframe with added metrics and some changed datatypes. Columns: ['run_id', 'intervention', 'timestep', 'agent_id', 'action', 'post_id', 'repost_target_id', 'liked_ids', 'disliked_ids', 'followed_agent_id', 'shown_post_ids', 'is_follow']
    :rtype: DataFrame
    '''

    # Change datatype to Int64 for post_id and followed_agent_id, count likes and dislikes and add binary is_follow
    df_t['post_id'] = df_t['post_id'].astype('Int64')
    df_t['repost_target_id'] = df_t['repost_target_id'].astype('Int64')
    df_t['is_follow'] = df_t['followed_agent_id'].notna().astype(int)
    df_t['followed_agent_id'] = df_t['followed_agent_id'].astype('Int64')

    return df_t

def prepare_p(df_t: pd.DataFrame, df_p: pd.DataFrame) -> pd.DataFrame:
    '''
    Add num_likes (int), num_dislikes (int), num_reposts (int), and times_shown (int) for each post.
    
    :param df_t: Timesteps dataframe
    :type df_t: DataFrame
    :param df_t: Posts dataframe
    :type df_t: DataFrame
    :return: Posts dataframe with added metrics. Columns: ['run_id', 'intervention', 'timestep', 'agent_id', 'post_id', 'content', 'num_likes', 'num_dislikes', 'num_reposts', 'times_shown']
    :rtype: DataFrame
    '''

    # count and add LIKES
    likes = df_t[['run_id', 'intervention', 'liked_ids']]
    likes = likes.explode('liked_ids').dropna().rename(columns={'liked_ids': 'post_id'})
    likes = likes.groupby(['run_id', 'intervention', 'post_id']).size().reset_index(name='num_likes')
    df_p = df_p.merge(likes, on=['run_id', 'intervention', 'post_id'], how='left')
    # print(likes.groupby(['run_id', 'intervention']).describe())
    
    # count and add DISLIKES
    dislikes = df_t[['run_id', 'intervention', 'disliked_ids']]
    dislikes = dislikes.explode('disliked_ids').dropna().rename(columns={'disliked_ids': 'post_id'})
    dislikes = dislikes.groupby(['run_id', 'intervention', 'post_id']).size().reset_index(name='num_dislikes')
    df_p = df_p.merge(dislikes, on=['run_id', 'intervention', 'post_id'], how='left')
    # print(dislikes.groupby(['run_id', 'intervention']).describe())
    
    # count and add REPOSTS
    reposts = df_t[['run_id', 'intervention', 'repost_target_id']]
    reposts = reposts.dropna().rename(columns={'repost_target_id': 'post_id'})
    reposts = reposts.groupby(['run_id', 'intervention', 'post_id']).size().reset_index(name='num_reposts')
    df_p = df_p.merge(reposts, on=['run_id', 'intervention', 'post_id'], how='left')
    # print(reposts.groupby(['run_id', 'intervention']).describe())

    # count and add TIMES SHOWN
    times_shown = df_t[['run_id', 'intervention', 'shown_post_ids']]
    times_shown = times_shown.explode('shown_post_ids').dropna().rename(columns={'shown_post_ids': 'post_id'})
    times_shown = times_shown.groupby(['run_id', 'intervention', 'post_id']).size().reset_index(name='times_shown')
    df_p = df_p.merge(times_shown, on=['run_id', 'intervention', 'post_id'], how='left')
    # print(times_shown.groupby(['run_id', 'intervention']).describe())

    # change NaN to 0 for like, dislike and repost counts
    df_p[['num_likes', 'num_dislikes', 'num_reposts', 'times_shown']] = df_p[['num_likes', 'num_dislikes', 'num_reposts', 'times_shown']].fillna(0)

    return df_p

def prepare_a(df_t: pd.DataFrame, df_a: pd.DataFrame) -> pd.DataFrame:
    '''
    Add following (list), followers (list), written_post_ids (list), reposted_post_ids (list), liked_post_ids (list), and disliked_post_ids (list) for each agent.
    
    :param df_t: Timesteps dataframe
    :type df_t: DataFrame
    :param df_t: Posts dataframe
    :type df_t: DataFrame
    :return: Agents dataframe with added metrics. Columns: ['run_id', 'intervention', 'agent_id', 'party', 'bio', 'persona', 'followed', 'followers', 'written_post_ids', 'reposted_post_ids', 'liked_post_ids', 'disliked_post_ids']
    :rtype: DataFrame
    '''
    
    # count and add FOLLOWS and FOLLOWERS
    follows = df_t[df_t['is_follow'] == 1][['run_id', 'intervention', 'agent_id', 'followed_agent_id']]

    # add followed
    followed = follows.groupby(['run_id', 'intervention', 'agent_id'])['followed_agent_id']
    followed = followed.aggregate(func=list).reset_index().rename(columns={'followed_agent_id': 'followed'})

    df_a = df_a.merge(followed, on=['run_id', 'intervention', 'agent_id'], how='left')
    df_a['followed'] = df_a['followed'].apply(lambda x: x if isinstance(x, list) else [])

    # add followers
    followers = follows.groupby(['run_id', 'intervention', 'followed_agent_id'])['agent_id']
    followers = followers.aggregate(func=list).reset_index().rename(columns={'agent_id': 'followers', 'followed_agent_id': 'agent_id'})

    df_a = df_a.merge(followers, on=['run_id', 'intervention', 'agent_id'], how='left')
    df_a['followers'] = df_a['followers'].apply(lambda x: x if isinstance(x, list) else [])

    # Add written_post_ids
    written_posts = df_t[df_t['action'] == 'WRITE_POST'][['run_id', 'intervention', 'agent_id', 'post_id']]
    
    written_posts = written_posts.groupby(['run_id', 'intervention', 'agent_id'])['post_id']
    written_posts = written_posts.aggregate(func=list).reset_index().rename(columns={'post_id': 'written_post_ids'})

    df_a = df_a.merge(written_posts, on=['run_id', 'intervention', 'agent_id'], how='left')
    
    df_a['written_post_ids'] = df_a['written_post_ids'].apply(lambda x: x if isinstance(x, list) else [])
    
    # Add reposted_post_ids
    reposted_posts = df_t[df_t['action'] == 'REPOST'][['run_id', 'intervention', 'agent_id', 'repost_target_id']]
    
    reposted_posts = reposted_posts.groupby(['run_id', 'intervention', 'agent_id'])['repost_target_id']
    reposted_posts = reposted_posts.aggregate(func=list).reset_index().rename(columns={'repost_target_id': 'reposted_post_ids'})

    df_a = df_a.merge(reposted_posts, on=['run_id', 'intervention', 'agent_id'], how='left')
    
    df_a['reposted_post_ids'] = df_a['reposted_post_ids'].apply(lambda x: x if isinstance(x, list) else [])

    # Add liked_post_ids
    liked_posts = df_t[['run_id', 'intervention', 'agent_id', 'liked_ids']].explode('liked_ids').dropna()
    
    liked_posts = liked_posts.groupby(['run_id', 'intervention', 'agent_id'])['liked_ids']
    liked_posts = liked_posts.aggregate(func=list).reset_index().rename(columns={'liked_ids': 'liked_post_ids'})

    df_a = df_a.merge(liked_posts, on=['run_id', 'intervention', 'agent_id'], how='left')
    df_a['liked_post_ids'] = df_a['liked_post_ids'].apply(lambda x: x if isinstance(x, list) else [])

    # Add disliked_post_ids
    disliked_posts = df_t[['run_id', 'intervention', 'agent_id', 'disliked_ids']].explode('disliked_ids').dropna()
    
    disliked_posts = disliked_posts.groupby(['run_id', 'intervention', 'agent_id'])['disliked_ids']
    disliked_posts = disliked_posts.aggregate(func=list).reset_index().rename(columns={'disliked_ids': 'disliked_post_ids'})

    df_a = df_a.merge(disliked_posts, on=['run_id', 'intervention', 'agent_id'], how='left')
    df_a['disliked_post_ids'] = df_a['disliked_post_ids'].apply(lambda x: x if isinstance(x, list) else [])

    return df_a

if __name__ == '__main__':

    interventions = ["CONTROL", "SOCIAL_PROOF", "IDENTITY"]
    runs = 3
    max_timesteps = 2000
    num_agents = 50

    data_path = Path(__file__).parents[1].joinpath('data')
    agents_path = Path(__file__).parents[1].joinpath('generate_agents')

    df_t, df_p, df_a = load_data(data_path, agents_path, interventions, runs)

    df_t = prepare_t(df_t)
    df_p = prepare_p(df_t, df_p)
    df_a = prepare_a(df_t, df_a)

    # print("Columns:", df_t.columns, "\n")
    # print(df_t.head(25))
    # print("Columns:", df_p.columns, "\n")
    # print(df_p.head(25))
    # print("Columns:", df_a.columns, "\n")
    # print(df_a.head(25))

