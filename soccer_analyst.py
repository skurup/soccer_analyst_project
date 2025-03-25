from football_data_api import FootballDataAPI
from vector_db import SoccerAnalystVectorDB
from visualizer import SoccerVisualizer
from crewai import Agent, Task, Crew, Process
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

class SoccerAnalystSystem:
    """
    Main system class that integrates Football-Data.org API with CrewAI and ChromaDB
    """
    
    def __init__(self):
        # Initialize API client
        api_key = os.environ.get("FOOTBALL_API_KEY")
        print(f"Using API key: {api_key}")  # Debug print
        self.api = FootballDataAPI(api_key=api_key)
        
        # Initialize vector database
        self.db = SoccerAnalystVectorDB()
        
        # Initialize visualizer
        self.visualizer = SoccerVisualizer()
        
        # Initialize CrewAI components
        self.agents = self._create_agents()
        self.tasks = []  # Will be populated based on specific operations
        
        # Create plots directory if it doesn't exist
        self.plots_dir = "/Users/skurup/soccer_analyst_project/plots"
        os.makedirs(self.plots_dir, exist_ok=True)
        
    def _create_agents(self):
        """Create the CrewAI agents"""
        
        # Data Collection Agent
        data_collector = Agent(
            role="EPL Data Collector",
            goal="Collect comprehensive match and statistical data from the English Premier League",
            backstory="""You are an expert at gathering soccer data from various sources.
            Your job is to collect match results, team statistics, and player performance data
            from the English Premier League, with a focus on Manchester United.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Data Processing Agent
        data_processor = Agent(
            role="Soccer Data Processor",
            goal="Transform and organize raw soccer data into structured formats for analysis",
            backstory="""You are a data engineering specialist with expertise in soccer analytics.
            You transform raw EPL data into well-structured formats, calculate advanced metrics,
            and ensure data quality for subsequent analysis.""",
            verbose=True,
            allow_delegation=True
        )
        
        # Manchester United Specialist
        man_utd_specialist = Agent(
            role="Manchester United Analyst",
            goal="Provide deep analytical insights into Manchester United's performance",
            backstory="""You are a dedicated Manchester United analyst with deep knowledge
            of the club's tactics, players, and historical performance patterns. You specialize
            in analyzing United's strengths, weaknesses, and tactical approaches in the context
            of each match.""",
            verbose=True,
            allow_delegation=True
        )
        
        # League Comparison Analyst
        league_analyst = Agent(
            role="EPL Comparison Analyst",
            goal="Compare team performances across the Premier League for contextual insights",
            backstory="""You specialize in comparative analysis across Premier League teams.
            Your expertise lies in contextualizing a team's performance relative to others,
            identifying trends, and highlighting where teams rank in various statistical categories.""",
            verbose=True,
            allow_delegation=True
        )
        
        # Tactical Insights Specialist
        tactical_analyst = Agent(
            role="Soccer Tactical Analyst",
            goal="Interpret statistical data to reveal tactical patterns and strategic insights",
            backstory="""You are an expert in soccer tactics who can translate raw statistics
            into meaningful tactical insights. You understand how numbers reflect playing styles,
            strategic approaches, and coaching philosophies.""",
            verbose=True,
            allow_delegation=True
        )
        
        return {
            "data_collector": data_collector,
            "data_processor": data_processor,
            "man_utd_specialist": man_utd_specialist,
            "league_analyst": league_analyst,
            "tactical_analyst": tactical_analyst
        }
    
    def initialize_system(self, days_back=90):
        """
        Initialize the system by collecting data and building the vector database
        
        Args:
            days_back: Number of days of historical data to collect
        """
        # Create tasks for system initialization
        
        # Task 1: Collect league data
        collect_league_data_task = Task(
            description=f"""
            Collect the current English Premier League standings and tournament information.
            
            This should include:
            1. Current standings table for all EPL teams
            2. Basic information about the current EPL season
            3. Current matchday and schedule information
            """,
            agent=self.agents["data_collector"],
            expected_output="EPL league data as JSON"
        )
        
        # Task 2: Collect Manchester United matches
        collect_manutd_matches_task = Task(
            description=f"""
            Collect Manchester United match data for the past {days_back} days.
            
            This should include:
            1. All matches played by Manchester United in this timeframe
            2. Basic match information (opponent, date, result, etc.)
            3. Match statistics if available
            """,
            agent=self.agents["data_collector"],
            expected_output="Manchester United match data as JSON"
        )
        
        # Task 3: Collect Big Six team data
        collect_big_six_task = Task(
            description="""
            Collect data for the 'Big Six' Premier League teams:
            - Manchester United
            - Manchester City
            - Liverpool
            - Chelsea
            - Arsenal
            - Tottenham
            
            This should include:
            1. Current season statistics
            2. League position and points
            3. Goals for and against
            """,
            agent=self.agents["data_collector"],
            expected_output="Big Six team data as JSON"
        )
        
        # Task 4: Process and structure data
        process_data_task = Task(
            description="""
            Process all collected data into structured formats for vector database storage.
            
            This should include:
            1. Data cleaning and normalization
            2. Calculating additional metrics
            3. Formatting data for embedding
            """,
            agent=self.agents["data_processor"],
            expected_output="Processed data files ready for database",
            context=[collect_league_data_task, collect_manutd_matches_task, collect_big_six_task]
        )
        
        # Task 5: Build vector database
        build_vector_db_task = Task(
            description="""
            Build the vector database with all processed data.
            
            This should include:
            1. Creating embeddings for all data
            2. Storing in appropriate collections
            3. Creating indices for efficient retrieval
            """,
            agent=self.agents["data_processor"],
            expected_output="Vector database populated and ready for queries",
            context=[process_data_task]
        )
        
        # Create the initialization crew
        init_crew = Crew(
            agents=list(self.agents.values()),
            tasks=[
                collect_league_data_task,
                collect_manutd_matches_task,
                collect_big_six_task,
                process_data_task,
                build_vector_db_task
            ],
            verbose=2,
            process=Process.sequential
        )
        
        # Execute the initialization
        result = init_crew.kickoff()
        
        # Verify database was populated
        db_stats = self.db.get_statistics_summary()
        print("Database initialized with the following document counts:")
        for collection, count in db_stats.items():
            print(f"- {collection}: {count} documents")
            
        return result
    
    def collect_and_process_data(self):
        """
        Collect and process data from Football-Data.org API and store in vector database
        """
        print("Collecting data from Football-Data.org API...")
        
        # Step 1: Collect EPL standings
        standings = self.api.get_standings()
        standings_df = self.api.create_standings_dataframe(standings)
        
        # Get Big Six comparison data
        big_six = self.api.get_big_six_comparison()
        
        # Step 2: Collect recent Manchester United matches
        recent_matches = self.api.get_recent_manchester_united_matches(days=90)
        matches_df = self.api.create_match_dataframe(recent_matches)
        
        # Step 3: Collect upcoming Manchester United matches
        upcoming_matches = self.api.get_upcoming_manchester_united_matches(days=30)
        
        print("Processing and storing data in vector database...")
        
        # Process and store standings
        self._process_standings(standings_df)
        
        # Process and store matches
        match_ids = self._process_matches(matches_df)
        
        # Process match details for each match
        for match_id in match_ids:
            self._process_match_details(match_id)
            
        # Process Big Six comparison
        self._process_big_six_comparison(big_six)
        
        print("Creating visualizations...")
        self.visualizer.save_all_plots(
            self.plots_dir,
            standings_df=standings_df,
            big_six_data=big_six,
            matches_df=matches_df
        )
        
        print("Data collection, processing, and visualization complete!")
        
    def _process_standings(self, standings_df):
        """Process and store standings data"""
        # Convert standings to text format for embedding
        standings_text = f"English Premier League Standings\n\n"
        
        for _, row in standings_df.iterrows():
            standings_text += f"{row['position']}. {row['team_name']} - {row['points']} pts ({row['won']}-{row['draw']}-{row['lost']}), GD: {row['goal_difference']}\n"
            
        # Add to vector database
        self.db.add_documents(
            collection_name="epl_teams",
            documents=[standings_text],
            metadatas=[{
                "type": "standings",
                "season": datetime.now().year,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": "football-data.org"
            }],
            ids=[f"standings_{datetime.now().strftime('%Y%m%d')}"]
        )
        
        # Also store each team's standing individually
        for _, row in standings_df.iterrows():
            team_text = f"""
            Team: {row['team_name']}
            Position: {row['position']}
            Points: {row['points']}
            Played: {row['played']}
            Record: {row['won']}-{row['draw']}-{row['lost']}
            Goals For: {row['goals_for']}
            Goals Against: {row['goals_against']}
            Goal Difference: {row['goal_difference']}
            Form: {row['form']}
            """
            
            # Add to vector database
            self.db.add_documents(
                collection_name="epl_teams",
                documents=[team_text],
                metadatas=[{
                    "type": "team_standing",
                    "team_id": row['team_id'],
                    "team_name": row['team_name'],
                    "position": row['position'],
                    "points": row['points'],
                    "season": datetime.now().year,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "football-data.org"
                }],
                ids=[f"team_standing_{row['team_id']}_{datetime.now().strftime('%Y%m%d')}"]
            )
            
            # If this is Manchester United, also add to the United-specific collection
            if row['team_name'] == "Manchester United":
                self.db.add_documents(
                    collection_name="manchester_united",
                    documents=[team_text],
                    metadatas=[{
                        "type": "team_standing",
                        "team_id": row['team_id'],
                        "team_name": row['team_name'],
                        "position": row['position'],
                        "points": row['points'],
                        "season": datetime.now().year,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "football-data.org"
                    }],
                    ids=[f"manutd_standing_{datetime.now().strftime('%Y%m%d')}"]
                )
    
    def _process_matches(self, matches_df):
        """Process and store match data"""
        match_ids = []
        
        for _, row in matches_df.iterrows():
            match_id = row['id']
            match_ids.append(match_id)
            
            # Create match text
            match_text = f"""
            Match: {row['home_team']} vs {row['away_team']}
            Competition: {row['competition']}
            Date: {row['date']}
            """
            
            if row['status'] in ["FINISHED", "AWARDED"]:
                match_text += f"""
                Result: {row['home_team']} {row['home_score']} - {row['away_score']} {row['away_team']}
                Half-time: {row['home_half_time']} - {row['away_half_time']}
                Winner: {row['winner'] if row['winner'] else 'Draw'}
                """
            else:
                match_text += f"Status: {row['status']}\n"
                
            # Create metadata
            metadata = {
                "type": "match",
                "match_id": match_id,
                "competition": row['competition'],
                "matchday": row['matchday'],
                "date": row['date'],
                "status": row['status'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "home_team_id": row['home_team_id'],
                "away_team_id": row['away_team_id'],
                "source": "football-data.org"
            }
            
            if row['status'] in ["FINISHED", "AWARDED"]:
                metadata.update({
                    "home_score": row['home_score'],
                    "away_score": row['away_score'],
                    "winner": row['winner']
                })
                
            # Check if Manchester United was involved
            is_manutd_match = row['home_team'] == "Manchester United" or row['away_team'] == "Manchester United"
            
            # Add to match_reports collection
            self.db.add_documents(
                collection_name="match_reports",
                documents=[match_text],
                metadatas=[metadata],
                ids=[f"match_{match_id}"]
            )
            
            # If this is a Manchester United match, also add to the United-specific collection
            if is_manutd_match:
                manutd_position = "home" if row['home_team'] == "Manchester United" else "away"
                opponent = row['away_team'] if manutd_position == "home" else row['home_team']
                
                manutd_metadata = metadata.copy()
                manutd_metadata.update({
                    "manutd_position": manutd_position,
                    "opponent": opponent
                })
                
                if row['status'] in ["FINISHED", "AWARDED"]:
                    manutd_score = row['home_score'] if manutd_position == "home" else row['away_score']
                    opponent_score = row['away_score'] if manutd_position == "home" else row['home_score']
                    
                    result = "win" if (manutd_position == "home" and row['winner'] == "HOME_TEAM") or \
                                     (manutd_position == "away" and row['winner'] == "AWAY_TEAM") else \
                             "loss" if (manutd_position == "home" and row['winner'] == "AWAY_TEAM") or \
                                      (manutd_position == "away" and row['winner'] == "HOME_TEAM") else "draw"
                                      
                    manutd_metadata.update({
                        "manutd_score": manutd_score,
                        "opponent_score": opponent_score,
                        "result": result
                    })
                
                self.db.add_documents(
                    collection_name="manchester_united",
                    documents=[match_text],
                    metadatas=[manutd_metadata],
                    ids=[f"manutd_match_{match_id}"]
                )
                
        return match_ids
    
    def _process_match_details(self, match_id):
        """Process and store match details"""
        try:
            match_details = self.api.get_match(match_id)
            if not match_details or "error" in match_details:
                print(f"Error retrieving match details for match {match_id}")
                return
            
            # Extract relevant match information
            match_info = {
                "id": match_id,
                "competition": match_details.get("competition", {}).get("name", "Unknown"),
                "home_team": match_details.get("homeTeam", {}).get("name", "Unknown"),
                "away_team": match_details.get("awayTeam", {}).get("name", "Unknown"),
                "score": f"{match_details.get('score', {}).get('fullTime', {}).get('home', 0)}-{match_details.get('score', {}).get('fullTime', {}).get('away', 0)}",
                "status": match_details.get("status", "Unknown"),
                "date": match_details.get("utcDate", "Unknown")
            }
            
            # Convert match details to text format for embedding
            match_text = f"Match Details: {match_info['home_team']} vs {match_info['away_team']}\n"
            match_text += f"Competition: {match_info['competition']}\n"
            match_text += f"Date: {match_info['date']}\n"
            match_text += f"Score: {match_info['score']}\n"
            match_text += f"Status: {match_info['status']}\n"
            
            # Add match statistics if available
            if "score" in match_details and match_details["score"].get("fullTime"):
                match_text += "\nMatch Statistics:\n"
                match_text += f"Possession: Home {match_details.get('homeTeam', {}).get('statistics', {}).get('possession', 'N/A')}% - Away {match_details.get('awayTeam', {}).get('statistics', {}).get('possession', 'N/A')}%\n"
                match_text += f"Shots: Home {match_details.get('homeTeam', {}).get('statistics', {}).get('shots', 'N/A')} - Away {match_details.get('awayTeam', {}).get('statistics', {}).get('shots', 'N/A')}\n"
                match_text += f"Shots on Target: Home {match_details.get('homeTeam', {}).get('statistics', {}).get('shotsOnTarget', 'N/A')} - Away {match_details.get('awayTeam', {}).get('statistics', {}).get('shotsOnTarget', 'N/A')}\n"
            
            # Store in vector database
            metadata = {
                "type": "match_details",
                "match_id": match_id,
                "home_team": match_info["home_team"],
                "away_team": match_info["away_team"],
                "date": match_info["date"]
            }
            
            self.db.add_document(match_text, metadata)
            
        except Exception as e:
            print(f"Error processing match details for match {match_id}: {str(e)}")
    
    def _process_big_six_comparison(self, big_six_data):
        """Process and store Big Six comparison data"""
        # Create comparison text
        comparison_text = "Premier League 'Big Six' Comparison\n\n"
        
        # Table header
        comparison_text += "Team            | Pos | Pts | P | W | D | L | GF | GA | GD\n"
        comparison_text += "----------------|-----|-----|---|---|---|---|----|----|-----------\n"
        
        # Add each team's data
        for team_name, stats in big_six_data.items():
            team_display = team_name.replace("_", " ").title().ljust(16)
            comparison_text += f"{team_display}| {stats['position']} | {stats['points']} | {stats['played']} | {stats['won']} | {stats['draw']} | {stats['lost']} | {stats['goals_for']} | {stats['goals_against']} | {stats['goal_difference']}\n"
            
        # Add narrative analysis
        comparison_text += "\nNarrative Analysis:\n"
        
        # Get Manchester United's position among the Big Six
        big_six_sorted = sorted(big_six_data.items(), key=lambda x: x[1]['position'])
        manutd_rank_in_big_six = 1
        
        for i, (team_name, _) in enumerate(big_six_sorted):
            if team_name == "manchester_united":
                manutd_rank_in_big_six = i + 1
                break
                
        # Add Manchester United specific analysis
        manutd_stats = big_six_data.get("manchester_united", {})
        if manutd_stats:
            comparison_text += f"\nManchester United Analysis:\n"
            comparison_text += f"- Current position: {manutd_stats['position']} in the Premier League\n"
            comparison_text += f"- Rank among 'Big Six': {manutd_rank_in_big_six}/6\n"
            comparison_text += f"- Points: {manutd_stats['points']} from {manutd_stats['played']} games\n"
            comparison_text += f"- Goal difference: {manutd_stats['goal_difference']} ({manutd_stats['goals_for']} scored, {manutd_stats['goals_against']} conceded)\n"
            
            # Form analysis
            if "form" in manutd_stats and manutd_stats["form"]:  # Check if form exists and is not None
                form = manutd_stats["form"]
                form_text = ""
                
                for char in form:
                    if char == "W":
                        form_text += "Win, "
                    elif char == "D":
                        form_text += "Draw, "
                    elif char == "L":
                        form_text += "Loss, "
                        
                if form_text:
                    form_text = form_text[:-2]  # Remove trailing comma and space
                    comparison_text += f"\nRecent Form: {form_text}"
            else:
                comparison_text += "\nRecent Form: Not available"
            
        # Create metadata
        metadata = {
            "type": "big_six_comparison",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "season": datetime.now().year,
            "source": "football-data.org",
            "teams": ", ".join(big_six_data.keys())  # Convert list to comma-separated string
        }
        
        # Add to team_stats collection
        self.db.add_documents(
            collection_name="team_stats",
            documents=[comparison_text],
            metadatas=[metadata],
            ids=[f"big_six_comparison_{datetime.now().strftime('%Y%m%d')}"]
        )
        
        # Also add to manchester_united collection
        if "manchester_united" in big_six_data:
            manutd_metadata = metadata.copy()
            manutd_metadata.update({
                "manutd_position": big_six_data["manchester_united"]["position"],
                "manutd_points": big_six_data["manchester_united"]["points"]
            })
            
            self.db.add_documents(
                collection_name="manchester_united",
                documents=[comparison_text],
                metadatas=[manutd_metadata],
                ids=[f"manutd_big_six_{datetime.now().strftime('%Y%m%d')}"]
            )
    
    def analyze_team_performance(self, team_id=None, team_name=None):
        """
        Create a comprehensive team performance analysis
        
        Args:
            team_id: Team ID (default: Manchester United)
            team_name: Team name (alternative to team_id)
            
        Returns:
            Team performance analysis
        """
        if team_id is None and team_name is None:
            # Default to Manchester United
            team_id = self.api.TEAM_IDS["manchester_united"]
            team_name = "Manchester United"
        elif team_id is not None:
            # Get team name from ID
            team_info = self.api.get_team(team_id)
            team_name = team_info.get("name", "Unknown Team")
        elif team_name is not None:
            # Get team ID from name (if needed)
            for name, id_value in self.api.TEAM_IDS.items():
                if name.replace("_", " ").lower() == team_name.lower():
                    team_id = id_value
                    break
                    
        # Create agent tasks for team analysis
        
        # Task 1: Analyze team statistics
        analyze_stats_task = Task(
            description=f"""
            Analyze the statistics and performance of {team_name} in the current EPL season.
            
            This should include:
            1. League position and points analysis
            2. Goals scored and conceded
            3. Form analysis
            4. Statistical strengths and weaknesses
            """,
            agent=self.agents["data_processor"],
            expected_output="Team statistical analysis"
        )
        
        # Task 2: Analyze recent matches
        analyze_matches_task = Task(
            description=f"""
            Analyze the recent matches of {team_name}.
            
            This should include:
            1. Results of last 5 matches
            2. Performance patterns
            3. Key match statistics
            4. Notable performances
            """,
            agent=self.agents["tactical_analyst"],
            expected_output="Recent match analysis"
        )
        
        # Task 3: Compare with rivals (mainly for Manchester United)
        compare_rivals_task = None
        if team_name == "Manchester United":
            compare_rivals_task = Task(
                description="""
                Compare Manchester United's performance with other 'Big Six' teams.
                
                This should include:
                1. Position among the Big Six
                2. Statistical comparison in key areas
                3. Head-to-head results
                4. Performance trends relative to rivals
                """,
                agent=self.agents["league_analyst"],
                expected_output="Rivals comparison analysis"
            )
            
        # Task 4: Provide tactical insights
        tactical_insights_task = Task(
            description=f"""
            Provide tactical insights about {team_name} based on available data.
            
            This should include:
            1. Playing style and formation analysis
            2. Attacking and defensive patterns
            3. Key player contributions
            4. Tactical strengths and vulnerabilities
            """,
            agent=self.agents["tactical_analyst"],
            expected_output="Tactical insights analysis",
            context=[analyze_stats_task, analyze_matches_task]
        )
        
        # Task 5: Generate comprehensive report
        tasks_for_context = [analyze_stats_task, analyze_matches_task, tactical_insights_task]
        if compare_rivals_task:
            tasks_for_context.append(compare_rivals_task)
            
        generate_report_task = Task(
            description=f"""
            Generate a comprehensive performance report for {team_name}.
            
            This should include:
            1. Executive summary
            2. Statistical breakdown
            3. Match analysis
            4. Tactical assessment
            5. Comparative analysis (if applicable)
            6. Conclusions and outlook
            """,
            agent=self.agents["man_utd_specialist"] if team_name == "Manchester United" else self.agents["league_analyst"],
            expected_output="Comprehensive team performance report",
            context=tasks_for_context
        )
        
        # Create the crew tasks
        tasks = [analyze_stats_task, analyze_matches_task, tactical_insights_task, generate_report_task]
        if compare_rivals_task:
            tasks.insert(2, compare_rivals_task)
            
        # Create and run the crew
        analysis_crew = Crew(
            agents=[
                self.agents["data_processor"], 
                self.agents["tactical_analyst"], 
                self.agents["league_analyst"],
                self.agents["man_utd_specialist"]
            ],
            tasks=tasks,
            verbose=2,
            process=Process.sequential
        )
        
        # Execute analysis
        result = analysis_crew.kickoff()
        return result
    
    def query_system(self, query: str, collection: str = "manchester_united", n_results: int = 3):
        """
        Query the vector database for information
        
        Args:
            query: Query string
            collection: Collection to query (default: manchester_united)
            n_results: Number of results to return
            
        Returns:
            Query results
        """
        results = self.db.query_collection(
            collection_name=collection,
            query_text=query,
            n_results=n_results
        )
        
        return results
    
    def analyze_match(self, match_id):
        """Analyze a specific match"""
        match_data = self.api.get_detailed_match_analysis(match_id)
        if not match_data:
            print(f"Failed to analyze match {match_id}")
            return None
            
        # Create match analysis text
        analysis_text = f"""Match Analysis: {match_data['basic_info']['home_team']} vs {match_data['basic_info']['away_team']}
Competition: {match_data['basic_info']['competition']}
Date: {match_data['basic_info']['date']}
Venue: {match_data['basic_info']['venue']}

Result: {match_data['scoring']['final_score']}
Half-time: {match_data['scoring']['half_time']}

Goals:"""
        
        # Add goals
        for goal in match_data['scoring']['goals']:
            assist_text = f", Assist: {goal['assist']}" if goal['assist'] else ""
            analysis_text += f"\n- {goal['minute']}' {goal['scorer']}{assist_text} ({goal['team']})"
            
        # Add statistics
        analysis_text += "\n\nMatch Statistics:"
        for stat_name, values in match_data['statistics'].items():
            analysis_text += f"\n- {stat_name.replace('_', ' ').title()}: {values['home']} (home) vs {values['away']} (away)"
            
        # Add Manchester United specific analysis if available
        if match_data['manchester_united']:
            analysis_text += "\n\nManchester United Analysis:"
            manutd = match_data['manchester_united']
            analysis_text += f"\n- Playing at: {manutd['playing_at']}"
            analysis_text += f"\n- Opponent: {manutd['opponent']}"
            analysis_text += f"\n- Result: {manutd['result']} ({manutd['score']})"
            analysis_text += f"\n- Goals scored: {manutd['goals_scored']}"
            analysis_text += f"\n- Goals conceded: {manutd['goals_conceded']}"
            
            # Add United-specific stats
            analysis_text += "\n- Key statistics:"
            for stat_name, value in manutd['stats'].items():
                analysis_text += f"\n  * {stat_name.replace('_', ' ').title()}: {value}"
        
        # Create match statistics visualization
        print("\nGenerating match statistics visualization...")
        fig = self.visualizer.plot_match_stats(match_data)
        if fig:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fig.savefig(f"{self.plots_dir}/match_stats_{match_id}_{timestamp}.png")
            plt.close(fig)
            print(f"Match statistics visualization saved to plots/match_stats_{match_id}_{timestamp}.png")
                
        return analysis_text
    
    def _store_match_analysis(self, match_id, analysis):
        """Store match analysis in vector database"""
        # Get match info
        match_data = self.api.get_match(match_id)
        
        home_team = match_data.get("homeTeam", {}).get("name", "Unknown")
        away_team = match_data.get("awayTeam", {}).get("name", "Unknown")
        date = match_data.get("utcDate", "Unknown date")
        
        # Create metadata
        metadata = {
            "type": "match_analysis",
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "date": date,
            "source": "crewai_analysis",
            "analysis_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Add to tactical_analysis collection
        self.db.add_documents(
            collection_name="tactical_analysis",
            documents=[analysis],
            metadatas=[metadata],
            ids=[f"crewai_match_analysis_{match_id}"]
        )
        
        # If this is a Manchester United match, also add to the United-specific collection
        if home_team == "Manchester United" or away_team == "Manchester United":
            is_home = home_team == "Manchester United"
            opponent = away_team if is_home else home_team
            
            manutd_metadata = metadata.copy()
            manutd_metadata.update({
                "is_home": is_home,
                "opponent": opponent
            })
            
            self.db.add_documents(
                collection_name="manchester_united",
                documents=[analysis],
                metadatas=[manutd_metadata],
                ids=[f"crewai_manutd_match_{match_id}"]
            )

def main():
    # Initialize the soccer analyst system
    soccer_analyst = SoccerAnalystSystem()
    
    # Get and process current Premier League standings
    soccer_analyst.collect_and_process_data()
    
    # Get valid match IDs (look back 5 days and forward 5 days)
    valid_matches = soccer_analyst.api.get_valid_match_ids(days_back=5, days_forward=5)
    
    if valid_matches:
        print("\nAvailable matches for analysis:")
        for match_id, info in valid_matches.items():
            print(f"ID: {match_id} - {info['home_team']} vs {info['away_team']}")
            print(f"Date: {info['date']}")
            print(f"Status: {info['status']}")
            print("-" * 50)
        
        # Find a Manchester United match if available
        manutd_match = None
        for match_id, info in valid_matches.items():
            if "Manchester United" in [info['home_team'], info['away_team']]:
                manutd_match = match_id
                break
        
        # Analyze either a Manchester United match or the first available match
        match_to_analyze = manutd_match or next(iter(valid_matches))
        match_info = valid_matches[match_to_analyze]
        
        print(f"\nAnalyzing match: {match_info['home_team']} vs {match_info['away_team']}")
        match_analysis = soccer_analyst.analyze_match(match_to_analyze)
        
        if match_analysis:
            print("\nMatch Analysis:")
            print(match_analysis)
        else:
            print("\nNo match analysis available - please check the match status and available data")
    else:
        print("\nNo valid matches found in the current date range")

if __name__ == "__main__":
    main()