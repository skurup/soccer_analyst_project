import streamlit as st
import pandas as pd
from soccer_analyst import SoccerAnalystSystem
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from typing import Dict, Any, Optional
from kafka_integration import SoccerAnalystKafkaManager, TOPICS
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    log_file = os.path.join('logs', 'soccer_analyst.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler with rotation (max 5MB per file, keep 5 backup files)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Stream handler for console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Streamlit logger configuration
    st_logger = logging.getLogger('streamlit')
    st_logger.setLevel(logging.DEBUG)
    
    return root_logger

# Initialize logging
logger = setup_logging()
logger.info("Starting Soccer Analyst Application")

# Cache configuration
CACHE_CONFIG = {
    'standings': {'ttl': 300, 'version': '1.0'},  # 5 minutes for standings
    'matches': {'ttl': 300, 'version': '1.0'},    # 5 minutes for matches
    'analysis': {'ttl': 300, 'version': '1.0'},   # 5 minutes for analysis
    'team_data': {'ttl': 300, 'version': '1.0'}   # 5 minutes for team data
}

# Cache monitoring
class CacheMonitor:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.api_calls = 0
        logger.info("Initialized CacheMonitor")
        
    def record_hit(self):
        self.hits += 1
        logger.debug(f"Cache hit recorded. Total hits: {self.hits}")
        
    def record_miss(self):
        self.misses += 1
        logger.debug(f"Cache miss recorded. Total misses: {self.misses}")
        
    def record_api_call(self):
        self.api_calls += 1
        logger.debug(f"API call recorded. Total API calls: {self.api_calls}")
        
    def get_stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        stats = {
            'hits': self.hits,
            'misses': self.misses,
            'api_calls': self.api_calls,
            'hit_rate': f"{hit_rate:.1f}%"
        }
        logger.info(f"Cache stats: {stats}")
        return stats

# Initialize cache monitor
@st.cache_resource
def get_cache_monitor():
    logger.info("Initializing cache monitor")
    return CacheMonitor()

# Initialize the soccer analyst system
@st.cache_resource
def get_soccer_analyst():
    logger.info("Initializing soccer analyst system")
    return SoccerAnalystSystem()

# Initialize Kafka manager
@st.cache_resource
def get_kafka_manager():
    logger.info("Initializing Kafka manager")
    return SoccerAnalystKafkaManager()

def is_data_valid(data: Dict[str, Any], data_type: str) -> bool:
    """Check if cached data is valid and not expired"""
    if not data or 'timestamp' not in data or 'version' not in data:
        logger.warning(f"Invalid data format for {data_type}")
        return False
    
    timestamp = datetime.fromisoformat(data['timestamp'])
    ttl = CACHE_CONFIG[data_type]['ttl']
    version = CACHE_CONFIG[data_type]['version']
    
    is_valid = (datetime.now() - timestamp).total_seconds() < ttl and data['version'] == version
    if not is_valid:
        logger.debug(f"Data {data_type} expired or version mismatch. TTL: {ttl}, Version: {version}")
    return is_valid

# Modified fetch_and_store_standings to use Kafka
@st.cache_data(ttl=300)
def fetch_and_store_standings(_soccer_analyst):
    """Fetch standings data, store in ChromaDB and Kafka, and cache locally"""
    logger.info("Fetching standings data")
    cache_monitor = get_cache_monitor()
    kafka_manager = get_kafka_manager()
    
    # First, try to get from ChromaDB
    logger.debug("Attempting to fetch standings from ChromaDB")
    db_results = _soccer_analyst.db.query_collection(
        collection_name="epl_teams",
        query_text=f"current league standings {datetime.now().strftime('%Y-%m-%d')}",
        n_results=1
    )
    
    if db_results and len(db_results) > 0:
        try:
            data = json.loads(db_results[0]['metadata'].get('standings_data', '{}'))
            if is_data_valid(data, 'standings'):
                cache_monitor.record_hit()
                logger.info("Successfully retrieved standings from cache")
                return data['data']
        except Exception as e:
            logger.error(f"Error parsing cached standings data: {str(e)}")
    
    # If not in DB or invalid, fetch from API
    logger.info("Fetching standings from API")
    cache_monitor.record_miss()
    cache_monitor.record_api_call()
    _soccer_analyst.collect_and_process_data()
    standings = _soccer_analyst.api.get_standings()
    
    if standings and 'standings' in standings:
        logger.info("Successfully fetched standings from API")
        # Prepare data with versioning and timestamp
        versioned_data = {
            'data': standings,
            'version': CACHE_CONFIG['standings']['version'],
            'timestamp': datetime.now().isoformat(),
        }
        
        try:
            # Store in ChromaDB for persistence
            logger.debug("Storing standings in ChromaDB")
            standings_text = f"Premier League Standings as of {datetime.now().strftime('%Y-%m-%d')}"
            _soccer_analyst.db.add_documents(
                collection_name="epl_teams",
                documents=[standings_text],
                metadatas=[{
                    "type": "standings",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "standings_data": json.dumps(versioned_data)
                }],
                ids=[f"standings_{datetime.now().strftime('%Y%m%d')}"]
            )
            
            # Publish to Kafka
            logger.debug("Publishing standings update to Kafka")
            kafka_manager.publish_standings_update(versioned_data)
            
            return standings
        except Exception as e:
            logger.error(f"Error storing standings data: {str(e)}")
    else:
        logger.warning("No standings data received from API")
    
    return None

@st.cache_data(ttl=300)
def fetch_and_store_matches(_soccer_analyst, days_back, days_forward):
    """Fetch matches data, store in ChromaDB, and cache locally"""
    logger.info(f"Fetching matches for range: -{days_back} to +{days_forward} days")
    cache_monitor = get_cache_monitor()
    date_range = f"{(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {(datetime.now() + timedelta(days=days_forward)).strftime('%Y-%m-%d')}"
    
    # Try to get from ChromaDB first
    logger.debug("Attempting to fetch matches from ChromaDB")
    db_results = _soccer_analyst.db.query_collection(
        collection_name="match_reports",
        query_text=f"matches between {date_range}",
        n_results=1
    )
    
    if db_results and len(db_results) > 0:
        try:
            data = json.loads(db_results[0]['metadata'].get('matches_data', '{}'))
            if is_data_valid(data, 'matches'):
                cache_monitor.record_hit()
                logger.info("Successfully retrieved matches from cache")
                return data['data']
        except Exception as e:
            logger.error(f"Error parsing cached matches data: {str(e)}")
    
    # If not in DB or invalid, fetch from API
    logger.info("Fetching matches from API")
    cache_monitor.record_miss()
    cache_monitor.record_api_call()
    matches = _soccer_analyst.api.get_valid_match_ids(days_back=days_back, days_forward=days_forward)
    
    if matches:
        logger.info(f"Successfully fetched {len(matches)} matches from API")
        # Prepare data with versioning and timestamp
        versioned_data = {
            'data': matches,
            'version': CACHE_CONFIG['matches']['version'],
            'timestamp': datetime.now().isoformat(),
        }
        
        try:
            # Store in ChromaDB
            logger.debug("Storing matches in ChromaDB")
            matches_text = f"Match list for {date_range}"
            _soccer_analyst.db.add_documents(
                collection_name="match_reports",
                documents=[matches_text],
                metadatas=[{
                    "type": "match_list",
                    "date_range": date_range,
                    "matches_data": json.dumps(versioned_data)
                }],
                ids=[f"matches_{datetime.now().strftime('%Y%m%d')}"]
            )
            return matches
        except Exception as e:
            logger.error(f"Error storing matches data: {str(e)}")
    else:
        logger.warning("No matches data received from API")
    
    return None

@st.cache_data(ttl=300)
def fetch_and_store_match_analysis(_soccer_analyst, match_id):
    """Fetch match analysis, store in ChromaDB, and cache locally"""
    logger.info(f"Fetching analysis for match ID: {match_id}")
    
    # Try to get from ChromaDB first
    logger.debug("Attempting to fetch match analysis from ChromaDB")
    db_results = _soccer_analyst.db.query_collection(
        collection_name="match_reports",
        query_text=f"match analysis {match_id}",
        n_results=1
    )
    
    if db_results and len(db_results) > 0:
        try:
            analysis_data = json.loads(db_results[0]['metadata'].get('analysis_data', '{}'))
            logger.info("Successfully retrieved match analysis from cache")
            return analysis_data
        except Exception as e:
            logger.error(f"Error parsing cached match analysis data: {str(e)}")
    
    # If not in DB or invalid, fetch from API
    logger.info("Analyzing match from API data")
    analysis = _soccer_analyst.analyze_match(match_id)
    
    if analysis:
        try:
            # Store in ChromaDB
            logger.debug("Storing match analysis in ChromaDB")
            _soccer_analyst.db.add_documents(
                collection_name="match_reports",
                documents=[analysis],
                metadatas=[{
                    "type": "match_analysis",
                    "match_id": str(match_id),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "analysis_data": json.dumps(analysis)
                }],
                ids=[f"analysis_{match_id}_{datetime.now().strftime('%Y%m%d')}"]
            )
            logger.info("Successfully stored match analysis")
            return analysis
        except Exception as e:
            logger.error(f"Error storing match analysis data: {str(e)}")
    else:
        logger.warning(f"No analysis data generated for match {match_id}")
    
    return None

def get_full_team_name(team_name):
    """Map common team names to their full names"""
    team_mapping = {
        "Liverpool": "Liverpool FC",
        "Manchester United": "Manchester United FC",
        "Manchester City": "Manchester City FC",
        "Chelsea": "Chelsea FC",
        "Arsenal": "Arsenal FC",
        "Tottenham": "Tottenham Hotspur FC",
        "Newcastle": "Newcastle United FC",
        "West Ham": "West Ham United FC",
        "Brighton": "Brighton & Hove Albion FC",
        "Aston Villa": "Aston Villa FC",
        "Wolves": "Wolverhampton Wanderers FC",
        "Bournemouth": "AFC Bournemouth",
        "Crystal Palace": "Crystal Palace FC",
        "Brentford": "Brentford FC",
        "Everton": "Everton FC",
        "Fulham": "Fulham FC",
        "Southampton": "Southampton FC",
        "Leicester": "Leicester City FC",
        "Nottingham": "Nottingham Forest FC",
        "Ipswich": "Ipswich Town FC"
    }
    return team_mapping.get(team_name, team_name)

# Modified fetch_and_store_team_data to use Kafka
@st.cache_data(ttl=300)
def fetch_and_store_team_data(_soccer_analyst, team_name):
    """Fetch team data, store in ChromaDB and Kafka, and cache locally"""
    kafka_manager = get_kafka_manager()
    
    # Get the full team name
    full_team_name = get_full_team_name(team_name)
    
    # Try to get from ChromaDB first
    db_results = _soccer_analyst.db.query_collection(
        collection_name="epl_teams",
        query_text=f"{full_team_name} current season statistics {datetime.now().strftime('%Y-%m-%d')}",
        n_results=1
    )
    
    if db_results and len(db_results) > 0:
        try:
            return json.loads(db_results[0]['metadata'].get('team_data', '{}'))
        except:
            pass
    
    # If not in DB or invalid, get from standings
    standings = fetch_and_store_standings(_soccer_analyst)
    if standings and 'standings' in standings:
        # Try exact match first
        team_data = None
        for team in standings['standings'][0]['table']:
            if team['team']['name'] == full_team_name:
                team_data = team
                break
        
        # If no exact match, try partial match
        if not team_data:
            for team in standings['standings'][0]['table']:
                if full_team_name in team['team']['name'] or team['team']['name'] in full_team_name:
                    team_data = team
                    break
        
        if team_data:
            # Store in ChromaDB
            team_text = f"{full_team_name} statistics as of {datetime.now().strftime('%Y-%m-%d')}"
            _soccer_analyst.db.add_documents(
                collection_name="epl_teams",
                documents=[team_text],
                metadatas=[{
                    "type": "team_data",
                    "team_name": full_team_name,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "team_data": json.dumps(team_data)
                }],
                ids=[f"team_{team_data['team']['id']}_{datetime.now().strftime('%Y%m%d')}"]
            )
            
            # Publish to Kafka
            kafka_manager.publish_team_stats(str(team_data['team']['id']), team_data)
            
            return team_data
    
    return None

def get_latest_visualizations(plots_dir: str, prefix: str) -> Optional[str]:
    """
    Get the most recent visualization file with the given prefix from the plots directory.
    
    Args:
        plots_dir: Directory containing the plot files
        prefix: Prefix of the plot files to search for
        
    Returns:
        The filename of the most recent visualization, or None if no matching files found
    """
    try:
        if not os.path.exists(plots_dir):
            return None
            
        # Get all files with the given prefix
        matching_files = [f for f in os.listdir(plots_dir) if f.startswith(prefix)]
        
        if not matching_files:
            return None
            
        # Sort by modification time and get the most recent
        return max(
            matching_files,
            key=lambda f: os.path.getmtime(os.path.join(plots_dir, f))
        )
    except Exception:
        return None

# Add real-time data processing
def start_real_time_processors():
    """Start background tasks for real-time data processing"""
    executor = ThreadPoolExecutor(max_workers=2)
    
    async def run_processors():
        from kafka_integration import RealTimeDataProcessor
        processor = RealTimeDataProcessor()
        
        # Start processors in separate threads
        executor.submit(processor.process_match_updates)
        executor.submit(processor.process_standings_updates)
    
    # Run the async function
    asyncio.run(run_processors())

# Modified main function to include real-time processing
def main():
    st.set_page_config(
        page_title="Soccer Analyst Dashboard",
        page_icon="⚽",
        layout="wide"
    )

    # Initialize the system
    soccer_analyst = get_soccer_analyst()
    
    # Start real-time processors in the background
    if 'processors_started' not in st.session_state:
        start_real_time_processors()
        st.session_state.processors_started = True

    # Sidebar
    st.sidebar.title("Soccer Analyst")
    analysis_type = st.sidebar.selectbox(
        "Select Analysis Type",
        ["League Overview", "Team Analysis", "Match Analysis", "Big Six Comparison"]
    )

    # Main content area
    st.title(f"⚽ {analysis_type}")

    if analysis_type == "League Overview":
        show_league_overview(soccer_analyst)
    elif analysis_type == "Team Analysis":
        show_team_analysis(soccer_analyst)
    elif analysis_type == "Match Analysis":
        show_match_analysis(soccer_analyst)
    else:  # Big Six Comparison
        show_big_six_comparison(soccer_analyst)

    st.rerun()

def show_league_overview(soccer_analyst):
    try:
        with st.spinner("Loading league data..."):
            # Use cached standings data with ChromaDB integration
            standings = fetch_and_store_standings(soccer_analyst)
            if not standings or 'standings' not in standings:
                st.error("Unable to fetch current standings data")
                return
                
            standings_table = standings['standings'][0]['table']
            
            # Calculate league statistics
            total_matches = sum(team['playedGames'] for team in standings_table)
            total_goals = sum(team['goalsFor'] for team in standings_table)
            avg_goals = round(total_goals / total_matches, 2) if total_matches > 0 else 0
            
            # Create columns for layout
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Current League Standings")
                
                # Create a DataFrame for better display
                df = pd.DataFrame([
                    {
                        'Position': team['position'],
                        'Team': team['team']['name'],
                        'Played': team['playedGames'],
                        'Won': team['won'],
                        'Drawn': team['draw'],
                        'Lost': team['lost'],
                        'GF': team['goalsFor'],
                        'GA': team['goalsAgainst'],
                        'GD': team['goalDifference'],
                        'Points': team['points']
                    }
                    for team in standings_table
                ])
                
                # Display standings as a styled table
                st.dataframe(
                    df.style.highlight_max(subset=['Points', 'GF', 'GD'], color='lightgreen')
                           .highlight_min(subset=['Points', 'GA'], color='lightpink'),
                    hide_index=True,
                    use_container_width=True
                )
                
                # Display the standings visualization using cached data
                latest_standings = get_latest_visualizations(soccer_analyst.plots_dir, "standings_")
                if latest_standings:
                    st.image(f"{soccer_analyst.plots_dir}/{latest_standings}")
                else:
                    st.info("Standings visualization not available. Please wait for the next data update.")

            with col2:
                st.subheader("League Statistics")
                
                # Add refresh button
                if st.button("🔄 Refresh Data"):
                    st.cache_data.clear()
                    st.rerun()
                
                # Season Progress
                matches_per_team = 38
                total_matches_possible = (20 * matches_per_team) // 2
                progress = (total_matches / total_matches_possible) * 100
                
                # Display metrics
                st.metric("Season Progress", f"{round(progress, 1)}%")
                st.metric("Matches Played", f"{total_matches}/{total_matches_possible}")
                st.metric("Total Goals", str(total_goals))
                st.metric("Average Goals per Match", str(avg_goals))
                
                # Top Scorers Section
                st.subheader("Top Scoring Teams")
                top_scorers = sorted(standings_table, key=lambda x: x['goalsFor'], reverse=True)[:5]
                for team in top_scorers:
                    st.metric(
                        team['team']['name'],
                        f"{team['goalsFor']} goals",
                        f"{round(team['goalsFor']/team['playedGames'], 2)} per game"
                    )
                
                # Best Defense Section
                st.subheader("Best Defenses")
                best_defense = sorted(standings_table, key=lambda x: x['goalsAgainst'])[:5]
                for team in best_defense:
                    st.metric(
                        team['team']['name'],
                        f"{team['goalsAgainst']} conceded",
                        f"{round(team['goalsAgainst']/team['playedGames'], 2)} per game"
                    )
                
    except Exception as e:
        st.error(f"An error occurred while loading the league overview: {str(e)}")
        st.info("Please try refreshing the page. If the error persists, check your API connection.")

def show_team_analysis(soccer_analyst):
    # Team selection
    col1, col2 = st.columns(2)
    
    with col1:
        team1_name = st.selectbox(
            "Select First Team",
            ["Manchester United", "Manchester City", "Liverpool", 
             "Chelsea", "Arsenal", "Tottenham", "Other Teams"],
            key="team1"
        )

        if team1_name == "Other Teams":
            team1_name = st.text_input("Enter first team name:", key="team1_input")

    with col2:
        team2_name = st.selectbox(
            "Select Second Team for Comparison",
            ["Manchester United", "Manchester City", "Liverpool", 
             "Chelsea", "Arsenal", "Tottenham", "Other Teams"],
            key="team2"
        )

        if team2_name == "Other Teams":
            team2_name = st.text_input("Enter second team name:", key="team2_input")

    if team1_name and team2_name and team1_name != team2_name:
        try:
            # Fetch team data for both teams
            with st.spinner("Loading team data..."):
                team1_data = fetch_and_store_team_data(soccer_analyst, team1_name)
                team2_data = fetch_and_store_team_data(soccer_analyst, team2_name)
                
                if not team1_data:
                    st.warning(f"No data found for {team1_name}")
                    return
                if not team2_data:
                    st.warning(f"No data found for {team2_name}")
                    return

            # Create tabs for different analyses
            tab1, tab2, tab3 = st.tabs(["Overview", "Form Analysis", "Statistics"])

            with tab1:
                st.subheader("Team Comparison Overview")
                
                # Display team info side by side
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    ### {team1_name}
                    - **Position**: {team1_data['position']}
                    - **Points**: {team1_data['points']}
                    - **Matches Played**: {team1_data['playedGames']}
                    - **Record**: {team1_data['won']}W - {team1_data['draw']}D - {team1_data['lost']}L
                    - **Goals**: {team1_data['goalsFor']} scored, {team1_data['goalsAgainst']} conceded
                    - **Goal Difference**: {team1_data['goalDifference']}
                    """)
                
                with col2:
                    st.markdown(f"""
                    ### {team2_name}
                    - **Position**: {team2_data['position']}
                    - **Points**: {team2_data['points']}
                    - **Matches Played**: {team2_data['playedGames']}
                    - **Record**: {team2_data['won']}W - {team2_data['draw']}D - {team2_data['lost']}L
                    - **Goals**: {team2_data['goalsFor']} scored, {team2_data['goalsAgainst']} conceded
                    - **Goal Difference**: {team2_data['goalDifference']}
                    """)

            with tab2:
                st.subheader("Recent Form Comparison")
                # Use cached visualization data
                latest_form = get_latest_visualizations(soccer_analyst.plots_dir, "form_timeline_")
                if latest_form:
                    st.image(f"{soccer_analyst.plots_dir}/{latest_form}")
                else:
                    st.info("Form timeline visualization not available. Please run data collection first.")

            with tab3:
                st.subheader("Detailed Statistics Comparison")
                
                # Create comparison metrics
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(team1_name)
                    st.metric("Points per Game", 
                            round(team1_data['points'] / team1_data['playedGames'], 2))
                    st.metric("Win Rate", 
                            f"{round(team1_data['won'] / team1_data['playedGames'] * 100, 1)}%")
                    st.metric("Goals per Game", 
                            round(team1_data['goalsFor'] / team1_data['playedGames'], 2))
                    st.metric("Goals Conceded per Game", 
                            round(team1_data['goalsAgainst'] / team1_data['playedGames'], 2))
                    
                with col2:
                    st.subheader(team2_name)
                    st.metric("Points per Game", 
                            round(team2_data['points'] / team2_data['playedGames'], 2))
                    st.metric("Win Rate", 
                            f"{round(team2_data['won'] / team2_data['playedGames'] * 100, 1)}%")
                    st.metric("Goals per Game", 
                            round(team2_data['goalsFor'] / team2_data['playedGames'], 2))
                    st.metric("Goals Conceded per Game", 
                            round(team2_data['goalsAgainst'] / team2_data['playedGames'], 2))
                
                # Add head-to-head comparison visualization
                st.subheader("Head-to-Head Comparison")
                
                # Create radar chart data
                categories = ['Points', 'Wins', 'Goals Scored', 'Goals Conceded', 'Goal Difference']
                team1_stats = [
                    team1_data['points'],
                    team1_data['won'],
                    team1_data['goalsFor'],
                    team1_data['goalsAgainst'],
                    team1_data['goalDifference']
                ]
                team2_stats = [
                    team2_data['points'],
                    team2_data['won'],
                    team2_data['goalsFor'],
                    team2_data['goalsAgainst'],
                    team2_data['goalDifference']
                ]
                
                # Create radar chart using plotly
                fig = go.Figure()
                
                fig.add_trace(go.Scatterpolar(
                    r=team1_stats,
                    theta=categories,
                    fill='toself',
                    name=team1_name
                ))
                
                fig.add_trace(go.Scatterpolar(
                    r=team2_stats,
                    theta=categories,
                    fill='toself',
                    name=team2_name
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, max(max(team1_stats), max(team2_stats))]
                        )),
                    showlegend=True,
                    title="Team Performance Comparison"
                )
                
                st.plotly_chart(fig)

        except Exception as e:
            st.error(f"An error occurred while loading the team analysis: {str(e)}")
    elif team1_name == team2_name:
        st.warning("Please select two different teams for comparison.")

def show_match_analysis(soccer_analyst):
    # Use cached match data with ChromaDB integration
    valid_matches = fetch_and_store_matches(soccer_analyst, days_back=5, days_forward=5)

    if valid_matches:
        # Create match selection options
        match_options = {
            f"{info['home_team']} vs {info['away_team']} ({info['date']})": match_id
            for match_id, info in valid_matches.items()
        }

        selected_match = st.selectbox(
            "Select Match",
            options=list(match_options.keys())
        )

        if selected_match:
            match_id = match_options[selected_match]
            # Use cached match analysis with ChromaDB integration
            match_analysis = fetch_and_store_match_analysis(soccer_analyst, match_id)

            if match_analysis:
                # Display match analysis in an organized way
                st.write(match_analysis)

                # Use cached visualization data
                latest_match_stats = get_latest_visualizations(
                    soccer_analyst.plots_dir,
                    f"match_stats_{match_id}"
                )
                if latest_match_stats:
                    st.image(f"{soccer_analyst.plots_dir}/{latest_match_stats}")
            else:
                st.warning("Match analysis not available.")
    else:
        st.warning("No matches available for analysis in the current date range.")

def show_big_six_comparison(soccer_analyst):
    st.subheader("Big Six Teams Comparison")
    
    # Use cached standings data with ChromaDB integration
    standings = fetch_and_store_standings(soccer_analyst)
    if standings and 'standings' in standings:
        standings_table = standings['standings'][0]['table']
        
        st.subheader("Detailed Comparison")
        
        # Create columns for each team
        cols = st.columns(6)
        
        # Define the Big Six teams with their exact API names
        big_six = {
            "Liverpool FC": "Liverpool",
            "Arsenal FC": "Arsenal",
            "Manchester City FC": "Man City",
            "Manchester United FC": "Man United",
            "Chelsea FC": "Chelsea",
            "Tottenham Hotspur FC": "Tottenham"
        }
        
        # Display data for each team
        for (api_name, display_name), col in zip(big_six.items(), cols):
            with col:
                team_data = next((team for team in standings_table 
                                if team['team']['name'] == api_name), None)
                if team_data:
                    st.markdown(f"**{display_name}**")
                    st.metric("Position", str(team_data['position']))
                    st.metric("Points", str(team_data['points']))
                    st.metric("Goals For", str(team_data['goalsFor']))
                    st.metric("Goals Against", str(team_data['goalsAgainst']))
                    st.metric("Win Rate", 
                            f"{round(team_data['won']/team_data['playedGames']*100, 1)}%")
    else:
        st.warning("Unable to load detailed comparison data.")

if __name__ == "__main__":
    main() 