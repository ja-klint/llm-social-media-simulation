import os
import pandas as pd
import numpy as np
from pathlib import Path

def load_data(data_path: Path, agents_path: Path, interventions: list[str], runs: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    
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

def add_metrics_t(df_t: pd.DataFrame, df_p: pd.DataFrame) -> pd.DataFrame:
    '''
    Add num_likes (int), num_dislikes (int) and is_follow (0|1) for each timestep.
    
    :param df_t: Timesteps dataframe
    :type df_t: DataFrame
    :param df_p: Posts dataframe
    :type df_p: DataFrame
    :return: Timesteps dataframe with added metrics
    :rtype: DataFrame
    '''

    # For timestep dataframe
    # Count likes and dislikes and add binary is_follow
    df_t['num_likes'] = df_t['liked_ids'].apply(len)
    df_t['num_dislikes'] = df_t['disliked_ids'].apply(len)
    df_t['is_follow'] = df_t['followed_agent_id'].notna().astype(int)

    return df_t

def add_metrics_p(df_t: pd.DataFrame, df_p: pd.DataFrame) -> pd.DataFrame:
    # For posts dataframe

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

def add_metrics_a(df_t: pd.DataFrame, df_p: pd.DataFrame, df_a: pd.DataFrame) -> pd.DataFrame:
    # For agents dataframe
    # columns for agents dataframe: ['run_id', 'agent_id', 'party', 'bio', 'persona', 'following', 'followers', 'written_post_ids', 'liked_post_ids', 'dislikes_post_ids', 'reposted_post_ids']
    
    # count and add LIKES
    follows = df_t[['run_id', 'intervention', 'agent_id', 'followed_agent_id']]
    follows = follows.dropna()
    
    ##
    ## Add column 'followed', with values list[agent_id, agent_id, ..]
    ## Add column 'followers', with values list[agent_id, agent_id, ..]
    ##
    # likes = follows.rename(columns={'liked_ids': 'post_id'})    


    # likes = follows.groupby(['run_id', 'intervention', 'post_id']).size().reset_index(name='num_likes')
    # df_p = df_p.merge(likes, on=['run_id', 'intervention', 'post_id'], how='left')
    # print(likes.groupby(['run_id', 'intervention']).describe())

    return df_a

if __name__ == '__main__':

    interventions = ["CONTROL", "SOCIAL_PROOF", "IDENTITY"]
    runs = 3
    max_timesteps = 2000
    num_agents = 50

    data_path = Path(__file__).parents[1].joinpath('data')
    agents_path = Path(__file__).parents[1].joinpath('generate_agents')

    df_t, df_p, df_a = load_data(data_path, agents_path, interventions, runs)

    df_t = add_metrics_t(df_t, df_p)
    df_p = add_metrics_p(df_t, df_p)
    df_a = add_metrics_a(df_t, df_p, df_a)

    # print("Columns:", df_t.columns, "\n")
    # print(df_t.head(25))
    # print("Columns:", df_p.columns, "\n")
    # print(df_p.head(25))
    print("Columns:", df_a.columns, "\n")
    print(df_a.head(25))