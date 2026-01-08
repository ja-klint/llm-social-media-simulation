import pandas as pd
import numpy as np
import networkx as nx
from collections import defaultdict
from pathlib import Path
import ast

import matplotlib.pyplot as plt
import seaborn as sns

def load_df(path: Path):
    '''Load dataframe'''
    
    df = pd.read_excel(path)

    # Convert strings to lists
    list_cols = ['follows', 'followers', 'written_post_ids', 'reposted_post_ids', 'liked_post_ids', 'disliked_post_ids']
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(ast.literal_eval)
    
    return df

def gini_coefficient(data):
    # https://www.statsdirect.com/help/nonparametric_methods/gini.htm

    n = len(data)

    if n == 0:
        return 0
    
    sum_distances = 0
    for i in range(n):
        for j in range(n):
            sum_distances += abs(data[i] - data[j])

    gini = sum_distances / (2 * n * np.sum(data))

    return gini

def engagement_metrics(df: pd.DataFrame, column: str) -> dict:
    
    # get stats for each post
    metric = df[column].values

    tenth_percentile = max(1, int(0.1 * len(metric)))
    
    # share of total likes, reposts, follows etc.. on the top 10% in that metric
    top10p_metric_share = np.sort(metric)[-tenth_percentile:].sum() / metric.sum()

    return {
        f'gini_{column[4:]}': gini_coefficient(metric),
        f'top10p_{column[4:]}_share': top10p_metric_share,
    }

def agent_activity_metrics(df_a: pd.DataFrame):
    return {
        'mean_likes_per_agent': df_a['liked_post_ids'].apply(len).mean(),
        'mean_reposts_per_agent': df_a['reposted_post_ids'].apply(len).mean(),
        'mean_posts_written_per_agent': df_a['written_post_ids'].apply(len).mean()
    }

def action_percentages(df_a: pd.DataFrame) -> dict:
    """
    Calculates the % of actions that are write_post, repost, and observe
    summed across all agents in a single run.
    """
    # Sum the raw counts for the entire run
    total_posts = df_a['num_post_action'].sum()
    total_reposts = df_a['num_repost_action'].sum()
    total_observes = df_a['num_observe_action'].sum()
    
    total_actions = total_posts + total_reposts + total_observes
    
    # Handle edge case where no actions occurred to avoid division by zero
    if total_actions == 0:
        return {
            'pct_write_post': 0.0,
            'pct_repost': 0.0,
            'pct_observe': 0.0
        }
    
    return {
        'pct_write_post': total_posts / total_actions,
        'pct_repost': total_reposts / total_actions,
        'pct_observe': total_observes / total_actions
    }

def get_interaction_df(df_a: pd.DataFrame, df_p: pd.DataFrame, interaction_column: str) -> pd.DataFrame:

    agent_party = df_a.set_index('agent_id')['party'] # for easy access to an agents party, by agent_id
    post_author = df_p.set_index('post_id')['agent_id'] # for easy access to the author id of post, by post_id
    interactions = []

    if interaction_column == 'follows':

        for i, a_row in df_a.iterrows():
            src_agent = a_row['agent_id']
            src_party = a_row['party']

            for tgt_agent in a_row['follows']:
                tgt_party = agent_party.get(tgt_agent)

                row = {
                    'src_agent': src_agent,
                    'src_party': src_party,
                    'tgt_agent': tgt_agent,
                    'tgt_party': tgt_party
                }

                interactions.append(row)

    else: # for interaction columns with post interactions

        for i, a_row in df_a.iterrows():
            src_agent = a_row['agent_id']
            src_party = a_row['party']

            for post_id in a_row[interaction_column]:
                # if post_id not in post_author:
                #     continue

                tgt_agent = post_author[post_id]
                tgt_party = agent_party.get(tgt_agent)

                row = {
                    'src_agent': src_agent,
                    'src_party': src_party,
                    'tgt_agent': tgt_agent,
                    'tgt_party': tgt_party
                }
                interactions.append(row)
    return pd.DataFrame(interactions)

def ei_index(df_a: pd.DataFrame, df_p: pd.DataFrame, column: str) -> float:
    """
    Calculate E–I index given src and tgt party labels
    """

    interactions_df = get_interaction_df(df_a, df_p, column)

    if interactions_df.empty:
        return np.nan

    E = (interactions_df['src_party'] != interactions_df['tgt_party']).sum()
    I = (interactions_df['src_party'] == interactions_df['tgt_party']).sum()

    ei = (E - I) / (E + I) if (E + I) > 0 else np.nan
    return ei

def follower_network_metrics(df_a: pd.DataFrame):
    G = nx.DiGraph()

    for i, row in df_a.iterrows():
        G.add_node(row['agent_id'], party=row['party'])
        for tgt in row['follows']:
            G.add_edge(row['agent_id'], tgt)

    # get followers gini
    followers = [count for node, count in G.in_degree()]
    gini_followers = gini_coefficient(np.array(followers))

    # get assortativity
    G_u = G.to_undirected()
    assortativity = nx.attribute_assortativity_coefficient(G_u, 'party')

    # get modularity
    communities = defaultdict(list)
    for node, data in G_u.nodes(data=True):
        communities[data['party']].append(node)

    modularity = nx.algorithms.community.modularity(
        G_u, communities.values()
    )

    return {
        'gini_followers': gini_followers,
        'party_assortativity': assortativity,
        'party_modularity': modularity
    }

def analyze_simulation(posts_path: Path, agents_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_p = load_df(posts_path)
    df_a = load_df(agents_path)

    run_results = []

    grouped = df_p.groupby(['run_id', 'intervention'])

    # analyze one run at a time
    for (run_id, intervention), df_p_run in grouped:
        df_a_run = df_a[(df_a['run_id'] == run_id) & (df_a['intervention'] == intervention)]

        metrics = {
            'run_id': run_id,
            'intervention': intervention
        }

        
        metrics.update(engagement_metrics(df_p_run, 'num_likes'))
        metrics.update(engagement_metrics(df_p_run, 'num_dislikes'))
        metrics.update(engagement_metrics(df_p_run, 'num_reposts'))
        metrics.update(engagement_metrics(df_a_run, 'num_followers'))
        metrics.update(agent_activity_metrics(df_a_run))

        metrics.update(action_percentages(df_a_run))

        metrics['ei_likes'] = ei_index(df_a_run, df_p_run, 'liked_post_ids')
        metrics['ei_dislikes'] = ei_index(df_a_run, df_p_run, 'disliked_post_ids')
        metrics['ei_reposts'] = ei_index(df_a_run, df_p_run, 'reposted_post_ids')
        metrics['ei_followers'] = ei_index(df_a_run, df_p_run, 'follows')

        metrics.update(follower_network_metrics(df_a_run))

        run_results.append(metrics)

    run_df = pd.DataFrame(run_results).sort_values('intervention')

    condition_summary = run_df.groupby('intervention').agg(('mean', 'std')).reset_index()

    return run_df, condition_summary

def plot_ei_grouped(run_df: pd.DataFrame, connect_runs: bool = False):

    ei_columns = ['ei_likes', 'ei_dislikes', 'ei_reposts']
    titles = ['Likes', 'Dislikes', 'Reposts']

    intervention_order = ['CONTROL', 'IDENTITY', 'SOCIAL_PROOF']
    intervention_labels = {
        'CONTROL': 'Control',
        'IDENTITY': 'Identity\ncues',
        'SOCIAL_PROOF': 'Popularity\ncues'
    }

    run_df = run_df.copy()
    run_df['intervention'] = pd.Categorical(
        run_df['intervention'],
        categories=intervention_order,
        ordered=True
    )

    fig, axes = plt.subplots(1, 3, figsize=(10, 5), sharey=True)

    for ax, ei_col, title in zip(axes, ei_columns, titles):

        sns.stripplot(
            data=run_df,
            x='intervention',
            y=ei_col,
            hue='intervention',
            order=intervention_order,
            jitter=0.15,
            size=8,
            alpha=0.8,
            dodge=False,
            legend=False,
            ax=ax
        )

        means = (
            run_df
            .groupby('intervention', observed=True)[ei_col]
            .mean()
            .reset_index()
        )

        ax.scatter(
            means['intervention'],
            means[ei_col],
            s=180,
            marker='_',
            color='black',
            linewidth=3,
            zorder=3
        )

        if connect_runs:
            for i, run_data in run_df.groupby('run_id'):
                ax.plot(
                    run_data['intervention'],
                    run_data[ei_col],
                    color='gray',
                    alpha=0.4,
                    linewidth=1,
                    zorder=1
                )

        ax.axhline(0, linestyle='--', color='black', alpha=0.6)
        ax.set_title(title)
        ax.set_xlabel('')

        ax.set_xticks(range(len(intervention_order)))
        ax.set_xticklabels([intervention_labels[i] for i in intervention_order])

        ax.grid(True, axis='y', alpha=0.3)
        sns.despine(ax=ax, top=True, right=True)

    axes[0].set_ylabel('E–I Index')
    axes[0].set_ylim(-1.05, 1.05)

    fig.tight_layout(rect=[0, 0, 1, 0.93])

    plt.savefig("ei_grouped_dotplot.png", dpi=300, bbox_inches="tight")
    plt.show()

def plot_gini_grouped(run_df: pd.DataFrame, connect_runs: bool = False):

    gini_columns = ['gini_likes', 'gini_dislikes', 'gini_reposts']
    titles = ['Likes', 'Dislikes', 'Reposts']

    intervention_order = ['CONTROL', 'IDENTITY', 'SOCIAL_PROOF']
    intervention_labels = {
        'CONTROL': 'Control',
        'IDENTITY': 'Identity\ncues',
        'SOCIAL_PROOF': 'Popularity\ncues'
    }

    run_df = run_df.copy()
    run_df['intervention'] = pd.Categorical(
        run_df['intervention'],
        categories=intervention_order,
        ordered=True
    )

    fig, axes = plt.subplots(1, 3, figsize=(10, 5), sharey=True)

    for ax, gini_col, title in zip(axes, gini_columns, titles):

        sns.stripplot(
            data=run_df,
            x='intervention',
            y=gini_col,
            hue='intervention',
            order=intervention_order,
            jitter=0.15,
            size=8,
            alpha=0.8,
            dodge=False,
            legend=False,
            ax=ax
        )

        means = (
            run_df
            .groupby('intervention', observed=True)[gini_col]
            .mean()
            .reset_index()
        )

        ax.scatter(
            means['intervention'],
            means[gini_col],
            s=180,
            marker='_',
            color='black',
            linewidth=3,
            zorder=3
        )

        if connect_runs:
            for i, run_data in run_df.groupby('run_id'):
                ax.plot(
                    run_data['intervention'],
                    run_data[gini_col],
                    color='gray',
                    alpha=0.4,
                    linewidth=1,
                    zorder=1
                )

        ax.set_title(title)
        ax.set_xlabel('')
        ax.set_xticks(range(len(intervention_order)))
        ax.set_xticklabels([intervention_labels[i] for i in intervention_order])

        ax.grid(True, axis='y', alpha=0.3)
        sns.despine(ax=ax, top=True, right=True)

    axes[0].set_ylabel('Gini coefficient')
    axes[0].set_ylim(-0.05, 1.05)

    fig.tight_layout(rect=[0, 0, 1, 0.93])

    plt.savefig("gini_grouped_dotplot.png", dpi=300, bbox_inches="tight")

if __name__ == '__main__':

    data_path = Path(__file__).parent.joinpath('processed_data')
    posts_path = data_path / 'posts_data.xlsx'
    agents_path = data_path / 'agents_data.xlsx'

    # run analysis
    run_level_df, condition_summary_df = analyze_simulation(posts_path, agents_path)

    plot_ei_grouped(run_level_df)
    plot_gini_grouped(run_level_df)

    # print results
#     for col in condition_summary_df.columns:
#         if 'mean' in col:
#             vals = condition_summary_df[col].values
#             print(f'''{col[0]}:
#       Control: {round(vals[0],3)}
# Identity cues: {round(vals[1],3)}
#  Social proof: {round(vals[2],3)}
# ''')

    # print(run_level_df[run_level_df['intervention']=='CONTROL'])


    save_path = data_path / 'run_level_data.xlsx'
    data_path.mkdir(exist_ok=True, parents=True)
    
    run_level_df.to_excel(save_path, index=False)
    
    save_path = data_path / 'condition_summary_data.xlsx'
    data_path.mkdir(exist_ok=True, parents=True)
    
    condition_summary_df.to_excel(save_path, index=True)