import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime

class SoccerVisualizer:
    """Class for creating visualizations of soccer data"""
    
    def __init__(self):
        # Set style for all plots
        plt.style.use('fivethirtyeight')  # Using a built-in matplotlib style
        self.team_colors = {
            'Manchester United': '#DA291C',
            'Manchester City': '#6CABDD',
            'Liverpool': '#C8102E',
            'Chelsea': '#034694',
            'Arsenal': '#EF0107',
            'Tottenham': '#132257'
        }
        
    def plot_league_standings(self, standings_df):
        """Create a bar plot of current league standings"""
        plt.figure(figsize=(15, 8))
        
        # Create bar plot
        bars = plt.bar(standings_df['team_name'], standings_df['points'])
        
        # Color the bars for Big Six teams
        for i, team in enumerate(standings_df['team_name']):
            if team in self.team_colors:
                bars[i].set_color(self.team_colors[team])
        
        # Customize the plot
        plt.title('Premier League Standings', fontsize=14, pad=20)
        plt.xlabel('Teams', fontsize=12)
        plt.ylabel('Points', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, axis='y', alpha=0.3)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        return plt.gcf()
    
    def plot_big_six_comparison(self, big_six_data):
        """Create a radar plot comparing Big Six teams"""
        # Convert dictionary to DataFrame
        df = pd.DataFrame(big_six_data).T
        
        # Select metrics for comparison
        metrics = ['points', 'goals_for', 'goals_against', 'goal_difference', 'won']
        
        # Number of variables
        num_vars = len(metrics)
        
        # Compute angle for each axis
        angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
        angles += angles[:1]
        
        # Initialize the spider plot
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Plot data
        for team in big_six_data.keys():
            values = [big_six_data[team][metric] for metric in metrics]
            values += values[:1]
            
            # Plot data and fill area
            ax.plot(angles, values, linewidth=1, linestyle='solid', label=team.replace('_', ' ').title())
            ax.fill(angles, values, alpha=0.1)
        
        # Fix axis to go in the right order and start at 12 o'clock
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        
        # Draw axis lines for each angle and label
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        
        # Add legend
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        
        plt.title("Big Six Teams Comparison", pad=20)
        return plt.gcf()
    
    def plot_form_timeline(self, matches_df):
        """Create a timeline plot of match results"""
        plt.figure(figsize=(15, 6))
        
        # Convert date strings to datetime
        matches_df['date'] = pd.to_datetime(matches_df['date'])
        
        # Create result points (3 for win, 1 for draw, 0 for loss)
        matches_df['result_points'] = matches_df.apply(
            lambda x: 3 if x['winner'] == 'HOME_TEAM' else 
                     (1 if x['winner'] == 'DRAW' else 0), axis=1
        )
        
        # Plot the timeline
        plt.plot(matches_df['date'], matches_df['result_points'], 
                marker='o', linestyle='-', linewidth=2, markersize=8)
        
        # Add match labels
        for idx, row in matches_df.iterrows():
            plt.annotate(f"{row['home_team']} {row['home_score']}-{row['away_score']} {row['away_team']}", 
                        (row['date'], row['result_points']),
                        xytext=(10, 10), textcoords='offset points',
                        rotation=45, ha='left')
        
        plt.title('Match Results Timeline', fontsize=14, pad=20)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Points', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return plt.gcf()
    
    def plot_match_stats(self, match_data):
        """Create a comparison plot of match statistics"""
        if not match_data or 'statistics' not in match_data:
            return None
            
        stats = match_data['statistics']
        if not stats or isinstance(stats, dict) and 'basic_summary' in stats:
            return None
            
        # Prepare data
        stat_names = list(stats.keys())
        home_values = [float(stats[stat]['home']) if stats[stat]['home'] != 'N/A' else 0 for stat in stat_names]
        away_values = [float(stats[stat]['away']) if stats[stat]['away'] != 'N/A' else 0 for stat in stat_names]
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Set position of bars
        x = np.arange(len(stat_names))
        width = 0.35
        
        # Create bars
        plt.bar(x - width/2, home_values, width, label=match_data['basic_info']['home_team'])
        plt.bar(x + width/2, away_values, width, label=match_data['basic_info']['away_team'])
        
        # Customize plot
        plt.title('Match Statistics Comparison', fontsize=14, pad=20)
        plt.xlabel('Statistics', fontsize=12)
        plt.ylabel('Value', fontsize=12)
        plt.xticks(x, [stat.replace('_', ' ').title() for stat in stat_names], rotation=45)
        plt.legend()
        
        plt.tight_layout()
        return plt.gcf()
    
    def save_all_plots(self, output_dir, standings_df=None, big_six_data=None, 
                      matches_df=None, match_data=None):
        """Save all available plots to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if standings_df is not None:
            fig = self.plot_league_standings(standings_df)
            fig.savefig(f"{output_dir}/standings_{timestamp}.png")
            plt.close(fig)
            
        if big_six_data is not None:
            fig = self.plot_big_six_comparison(big_six_data)
            fig.savefig(f"{output_dir}/big_six_{timestamp}.png")
            plt.close(fig)
            
        if matches_df is not None:
            fig = self.plot_form_timeline(matches_df)
            fig.savefig(f"{output_dir}/form_timeline_{timestamp}.png")
            plt.close(fig)
            
        if match_data is not None:
            fig = self.plot_match_stats(match_data)
            if fig:
                fig.savefig(f"{output_dir}/match_stats_{timestamp}.png")
                plt.close(fig) 