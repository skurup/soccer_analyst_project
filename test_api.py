import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

def test_api_key():
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.environ.get("FOOTBALL_API_KEY")
    print(f"Testing API key: {api_key}")
    
    headers = {
        "X-Auth-Token": api_key
    }
    
    # Test 1: Check Premier League info
    pl_url = "https://api.football-data.org/v4/competitions/PL"
    try:
        response = requests.get(pl_url, headers=headers)
        print(f"\nTest 1 - Premier League Info Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Competition: {data.get('name')}")
            print(f"Current Season: {data.get('season', {}).get('startDate')} to {data.get('season', {}).get('endDate')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        
    # Test 2: Get recent matches
    matches_url = "https://api.football-data.org/v4/matches"
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    params = {
        "dateFrom": week_ago.strftime("%Y-%m-%d"),
        "dateTo": today.strftime("%Y-%m-%d"),
        "competitions": "PL"  # Premier League
    }
    
    try:
        response = requests.get(matches_url, headers=headers, params=params)
        print(f"\nTest 2 - Recent Matches Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"\nFound {len(matches)} matches in the last week:")
            
            for match in matches[:5]:  # Show first 5 matches
                home = match.get('homeTeam', {}).get('name', 'Unknown')
                away = match.get('awayTeam', {}).get('name', 'Unknown')
                match_id = match.get('id')
                status = match.get('status')
                print(f"Match ID: {match_id} - {home} vs {away} ({status})")
                
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_key() 