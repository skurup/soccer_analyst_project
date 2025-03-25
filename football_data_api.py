import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class FootballDataAPI:
    """Client for interacting with the Football-Data.org API"""
    
    BASE_URL = "https://api.football-data.org/v4"
    
    # Common team IDs
    TEAM_IDS = {
        "manchester_united": 66,
        "manchester_city": 65,
        "liverpool": 64,
        "chelsea": 61,
        "arsenal": 57,
        "tottenham": 73
    }
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"X-Auth-Token": api_key}
        self.last_request_time = 0
        self.min_request_interval = 6  # Minimum 6 seconds between requests
        
    def _make_request(self, endpoint, params=None):
        """Make a request to the API with rate limiting"""
        # Implement rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        self.last_request_time = time.time()
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print(f"Rate limit exceeded. Waiting {self.min_request_interval} seconds...")
            time.sleep(self.min_request_interval)
            return self._make_request(endpoint, params)  # Retry the request
        else:
            print(f"API request failed with status code {response.status_code}")
            return None
            
    def get_standings(self, competition_id="PL"):
        """Get current standings for a competition"""
        return self._make_request(f"competitions/{competition_id}/standings")
        
    def get_team(self, team_id):
        """Get team information"""
        return self._make_request(f"teams/{team_id}")
        
    def get_match(self, match_id):
        """Get match information"""
        return self._make_request(f"matches/{match_id}")
        
    def get_recent_manchester_united_matches(self, days=90):
        """Get recent Manchester United matches"""
        team_id = self.TEAM_IDS["manchester_united"]
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }
        
        return self._make_request(f"teams/{team_id}/matches", params=params)
        
    def get_upcoming_manchester_united_matches(self, days=30):
        """Get upcoming Manchester United matches"""
        team_id = self.TEAM_IDS["manchester_united"]
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }
        
        return self._make_request(f"teams/{team_id}/matches", params=params)
        
    def get_big_six_comparison(self):
        """Get comparison data for the 'Big Six' teams"""
        standings = self.get_standings()
        print("API Response:", standings)  # Debug print
        if "error" in standings:
            return standings
            
        big_six_data = {}
        standings_table = standings["standings"][0]["table"]
        
        for team_name, team_id in self.TEAM_IDS.items():
            for team in standings_table:
                if team["team"]["id"] == team_id:
                    big_six_data[team_name] = {
                        "position": team["position"],
                        "points": team["points"],
                        "played": team["playedGames"],
                        "won": team["won"],
                        "draw": team["draw"],
                        "lost": team["lost"],
                        "goals_for": team["goalsFor"],
                        "goals_against": team["goalsAgainst"],
                        "goal_difference": team["goalDifference"],
                        "form": team.get("form", "")
                    }
                    break
        
        print("Big Six Data:", big_six_data)  # Debug print
        return big_six_data
        
    def get_match_data(self, match_id):
        """Get data for a specific match"""
        if not isinstance(match_id, int):
            print(f"Invalid match ID format: {match_id}. Match ID must be an integer.")
            return None
        
        url = f"{self.BASE_URL}/matches/{match_id}"
        headers = {
            'X-Auth-Token': self.api_key
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"API authentication failed. Please check your API key: {self.api_key}")
                return None
            elif response.status_code == 404:
                print(f"Match ID {match_id} not found. Please check if this is a valid match ID.")
                return None
            elif response.status_code == 429:
                print("Rate limit exceeded. Please wait before making more requests.")
                time.sleep(self.min_request_interval)
                return self.get_match_data(match_id)  # Retry after waiting
            else:
                print(f"API request failed with status code {response.status_code}")
                if response.text:
                    print(f"Error details: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None

    def get_valid_match_ids(self, days_back=7, days_forward=7):
        """Get valid match IDs for a date range
        
        Args:
            days_back: Number of days to look back
            days_forward: Number of days to look forward
            
        Returns:
            Dictionary of match IDs mapped to basic match info
        """
        valid_matches = {}
        
        # Split the date range into 10-day chunks
        current_date = datetime.now() - timedelta(days=days_back)
        end_target = datetime.now() + timedelta(days=days_forward)
        
        while current_date <= end_target:
            # Calculate end date for this chunk (maximum 10 days)
            chunk_end = min(current_date + timedelta(days=9), end_target)
            
            url = f"{self.BASE_URL}/matches"
            params = {
                "dateFrom": current_date.strftime("%Y-%m-%d"),
                "dateTo": chunk_end.strftime("%Y-%m-%d"),
                "competitions": "PL",  # Premier League
                "status": "SCHEDULED,LIVE,IN_PLAY,PAUSED,FINISHED"  # Comma-separated status list
            }
            
            try:
                print(f"\nFetching matches from {current_date.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
                response = requests.get(url, headers=self.headers, params=params)
                print(f"Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    matches = data.get('matches', [])
                    
                    for match in matches:
                        match_id = match.get('id')
                        if match_id:
                            valid_matches[match_id] = {
                                'home_team': match.get('homeTeam', {}).get('name', 'Unknown'),
                                'away_team': match.get('awayTeam', {}).get('name', 'Unknown'),
                                'date': match.get('utcDate', 'Unknown'),
                                'status': match.get('status', 'Unknown'),
                                'competition': match.get('competition', {}).get('name', 'Unknown')
                            }
                elif response.status_code == 403:
                    print("API authentication failed. Please check your API key.")
                    return {}
                elif response.status_code == 429:
                    print("Rate limit exceeded. Please wait before making more requests.")
                    time.sleep(self.min_request_interval)
                    continue  # Retry this chunk after waiting
                else:
                    print(f"Failed to get matches. Status code: {response.status_code}")
                    if response.text:
                        print(f"Error details: {response.text}")
                
            except requests.exceptions.RequestException as e:
                print(f"Error getting matches: {e}")
            
            # Move to next chunk
            current_date = chunk_end + timedelta(days=1)
            
            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)
        
        if not valid_matches:
            print(f"No matches found in the specified date range")
        
        return valid_matches

    def get_detailed_match_analysis(self, match_id):
        """Get detailed match analysis with enhanced free tier handling"""
        # First check if this is a valid match ID
        valid_matches = self.get_valid_match_ids()
        if match_id not in valid_matches:
            print(f"Match ID {match_id} is not in the current valid range.")
            print("Available matches:")
            for mid, info in valid_matches.items():
                print(f"ID: {mid} - {info['home_team']} vs {info['away_team']} ({info['date']}) - {info['status']}")
            return None
        
        match_data = self.get_match(match_id)
        if not match_data:
            print(f"Failed to get match data for match {match_id}")
            return None
        
        try:
            # Extract basic information with better error handling
            basic_info = {
                "home_team": match_data.get("homeTeam", {}).get("name", "Unknown"),
                "away_team": match_data.get("awayTeam", {}).get("name", "Unknown"),
                "competition": match_data.get("competition", {}).get("name", "Unknown"),
                "date": match_data.get("utcDate", "Unknown"),
                "venue": match_data.get("venue", "Unknown"),
                "status": match_data.get("status", "Unknown")
            }
            
            # Extract scoring information
            score = match_data.get("score", {})
            scoring = {
                "final_score": "TBD" if basic_info["status"] != "FINISHED" else 
                              f"{score.get('fullTime', {}).get('home', 0)} - {score.get('fullTime', {}).get('away', 0)}",
                "half_time": "TBD" if basic_info["status"] != "FINISHED" else 
                            f"{score.get('halfTime', {}).get('home', 0)} - {score.get('halfTime', {}).get('away', 0)}",
                "goals": []
            }
            
            # Extract goals if available
            for goal in match_data.get("goals", []):
                goal_info = {
                    "minute": goal.get("minute", 0),
                    "team": goal.get("team", {}).get("name", "Unknown"),
                    "scorer": goal.get("scorer", {}).get("name", "Unknown"),
                    "assist": goal.get("assist", {}).get("name", None)
                }
                scoring["goals"].append(goal_info)
            
            # Extract available statistics (handling free tier limitations)
            home_stats = match_data.get("homeTeam", {}).get("statistics", {})
            away_stats = match_data.get("awayTeam", {}).get("statistics", {})
            statistics = {}
            
            # Basic stats available in free tier
            for stat in ["possession", "shots", "shotsOnTarget"]:
                home_val = home_stats.get(stat, "N/A")
                away_val = away_stats.get(stat, "N/A")
                if home_val != "N/A" or away_val != "N/A":  # Only include if at least one team has data
                    statistics[stat] = {
                        "home": home_val,
                        "away": away_val
                    }
            
            # Add basic match events if available
            if not statistics and basic_info["status"] == "FINISHED":
                statistics["basic_summary"] = {
                    "home": f"Goals: {score.get('fullTime', {}).get('home', 0)}",
                    "away": f"Goals: {score.get('fullTime', {}).get('away', 0)}"
                }
            
            # Extract Manchester United specific analysis
            manutd_analysis = None
            if basic_info["home_team"] == "Manchester United" or basic_info["away_team"] == "Manchester United":
                is_home = basic_info["home_team"] == "Manchester United"
                opponent = basic_info["away_team"] if is_home else basic_info["home_team"]
                
                if basic_info["status"] == "FINISHED":
                    manutd_score = score.get("fullTime", {}).get("home" if is_home else "away", 0)
                    opponent_score = score.get("fullTime", {}).get("away" if is_home else "home", 0)
                    
                    manutd_analysis = {
                        "playing_at": "home" if is_home else "away",
                        "opponent": opponent,
                        "result": "win" if manutd_score > opponent_score else "loss" if manutd_score < opponent_score else "draw",
                        "score": f"{manutd_score} - {opponent_score}",
                        "goals_scored": manutd_score,
                        "goals_conceded": opponent_score,
                        "stats": {
                            stat: home_stats.get(stat, "N/A") if is_home else away_stats.get(stat, "N/A")
                            for stat in ["possession", "shots", "shotsOnTarget"]
                            if home_stats.get(stat, "N/A") != "N/A" or away_stats.get(stat, "N/A") != "N/A"
                        }
                    }
                else:
                    manutd_analysis = {
                        "playing_at": "home" if is_home else "away",
                        "opponent": opponent,
                        "status": basic_info["status"]
                    }
                
            return {
                "basic_info": basic_info,
                "scoring": scoring,
                "statistics": statistics,
                "manchester_united": manutd_analysis
            }
            
        except Exception as e:
            print(f"Error processing match data: {e}")
            return None
        
    def create_standings_dataframe(self, standings_data):
        """Convert standings data to pandas DataFrame"""
        if "error" in standings_data:
            return pd.DataFrame()
            
        standings_list = []
        for team in standings_data["standings"][0]["table"]:
            standings_list.append({
                "position": team["position"],
                "team_name": team["team"]["name"],
                "team_id": team["team"]["id"],
                "played": team["playedGames"],
                "won": team["won"],
                "draw": team["draw"],
                "lost": team["lost"],
                "points": team["points"],
                "goals_for": team["goalsFor"],
                "goals_against": team["goalsAgainst"],
                "goal_difference": team["goalDifference"],
                "form": team.get("form", "")
            })
            
        return pd.DataFrame(standings_list)
        
    def create_match_dataframe(self, matches_data):
        """Convert matches data to pandas DataFrame"""
        if "error" in matches_data:
            return pd.DataFrame()
            
        matches_list = []
        for match in matches_data["matches"]:
            matches_list.append({
                "id": match["id"],
                "competition": match["competition"]["name"],
                "matchday": match.get("matchday"),
                "status": match["status"],
                "date": match["utcDate"],
                "home_team": match["homeTeam"]["name"],
                "away_team": match["awayTeam"]["name"],
                "home_team_id": match["homeTeam"]["id"],
                "away_team_id": match["awayTeam"]["id"],
                "home_score": match["score"]["fullTime"]["home"],
                "away_score": match["score"]["fullTime"]["away"],
                "home_half_time": match["score"]["halfTime"]["home"],
                "away_half_time": match["score"]["halfTime"]["away"],
                "winner": "HOME_TEAM" if match["score"]["winner"] == "HOME_TEAM" else \
                         "AWAY_TEAM" if match["score"]["winner"] == "AWAY_TEAM" else \
                         "DRAW" if match["score"]["winner"] == "DRAW" else None
            })
            
        return pd.DataFrame(matches_list) 