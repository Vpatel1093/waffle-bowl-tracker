"""Yahoo Fantasy API service with caching."""
import os
from datetime import datetime
from typing import List, Dict, Optional
from yfpy.query import YahooFantasySportsQuery
from app import cache


class YahooService:
    """Wrapper around YFPY with caching and error handling."""

    def __init__(self, league_id: str = None):
        """Initialize Yahoo service with server-side OAuth tokens.

        Args:
            league_id: Yahoo Fantasy league ID (from env if not provided)
        """
        self.league_id = league_id or os.getenv('LEAGUE_ID')
        self.cache_live_scores = int(os.getenv('CACHE_LIVE_SCORES', 15))

        # Get current season (auto-detect or from env)
        self.season = int(os.getenv('NFL_SEASON', datetime.now().year))

        # Initialize YFPY query
        # YFPY will use tokens from ~/.yf_token_store/oauth2.json
        from pathlib import Path
        auth_dir = Path.home() / '.yf_token_store'

        try:
            self.yf_query = YahooFantasySportsQuery(
                auth_dir=str(auth_dir),
                league_id=self.league_id,
                game_code='nfl',
                offline=False
            )
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Yahoo API: {e}")
            print("Make sure you've run: python -m app.utils.oauth_setup")
            self.yf_query = None

    @cache.memoize(timeout=60)  # 1 minute
    def get_league_info(self) -> Optional[Dict]:
        """Get league metadata.

        Returns:
            Dict with league information or None if error
        """
        if not self.yf_query:
            return None

        try:
            # Helper function for byte strings
            def to_str(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8')
                return str(val) if val is not None else ''

            league = self.yf_query.get_league_metadata()
            return {
                'league_id': to_str(self.league_id),
                'name': to_str(league.name),
                'num_teams': int(league.num_teams) if hasattr(league, 'num_teams') else 0,
                'current_week': int(league.current_week) if hasattr(league, 'current_week') else 1,
                'start_week': int(league.start_week) if hasattr(league, 'start_week') else 1,
                'end_week': int(league.end_week) if hasattr(league, 'end_week') else 17
            }
        except Exception as e:
            print(f"Error fetching league info: {e}")
            return None

    @cache.memoize(timeout=60)  # 1 minute
    def get_league_standings(self) -> Optional[List[Dict]]:
        """Get current league standings.

        Returns:
            List of team standings sorted by rank
        """
        if not self.yf_query:
            return None

        try:
            standings = self.yf_query.get_league_standings()

            # YFPY returns teams in the 'teams' attribute
            if hasattr(standings, 'teams'):
                teams_data = standings.teams
            elif isinstance(standings, list):
                teams_data = standings
            else:
                print(f"Unexpected standings format: {type(standings)}")
                return None

            teams = []
            for team in teams_data:
                try:
                    # Handle byte strings from YFPY
                    def to_str(val):
                        if isinstance(val, bytes):
                            return val.decode('utf-8')
                        return str(val) if val is not None else ''

                    teams.append({
                        'team_id': to_str(team.team_id),
                        'team_key': to_str(team.team_key),
                        'name': to_str(team.name),
                        'manager': to_str(team.manager.nickname) if hasattr(team, 'manager') and team.manager else 'Unknown',
                        'wins': int(team.team_standings.outcome_totals.wins) if hasattr(team, 'team_standings') else 0,
                        'losses': int(team.team_standings.outcome_totals.losses) if hasattr(team, 'team_standings') else 0,
                        'ties': int(team.team_standings.outcome_totals.ties) if hasattr(team, 'team_standings') and hasattr(team.team_standings.outcome_totals, 'ties') else 0,
                        'points_for': float(team.team_points.total) if hasattr(team, 'team_points') else 0.0,
                        'points_against': float(team.team_projected_points.total) if hasattr(team, 'team_projected_points') else 0.0,
                        'rank': int(team.team_standings.rank) if hasattr(team, 'team_standings') else 0
                    })
                except Exception as team_error:
                    print(f"Error parsing team: {team_error}")
                    continue

            # Sort by rank
            teams.sort(key=lambda x: x['rank'])
            return teams

        except Exception as e:
            print(f"Error fetching standings: {e}")
            import traceback
            traceback.print_exc()
            return None

    @cache.memoize(timeout=15)  # 15 seconds for live scores
    def get_scoreboard(self, week: int = None) -> Optional[Dict]:
        """Get scoreboard for a specific week.

        Args:
            week: Week number (uses current week if not specified)

        Returns:
            Dict with matchups for the week
        """
        if not self.yf_query:
            return None

        try:
            # Helper function for byte strings
            def to_str(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8')
                return str(val) if val is not None else ''

            scoreboard = self.yf_query.get_league_scoreboard_by_week(week)

            # Get ALL teams from league to get their scores
            # (not just the matchup pairings)
            all_teams_scores = {}

            matchups = []
            for matchup in scoreboard.matchups:
                teams = []
                for team in matchup.teams:
                    teams.append({
                        'team_id': to_str(team.team_id),
                        'team_key': to_str(team.team_key),
                        'name': to_str(team.name),
                        'points': float(team.team_points.total) if hasattr(team, 'team_points') else 0.0,
                        'projected_points': float(team.team_projected_points.total) if hasattr(team, 'team_projected_points') else 0.0
                    })

                winner_team_key = matchup.winner_team_key if hasattr(matchup, 'winner_team_key') else None

                matchups.append({
                    'week': week,
                    'teams': teams,
                    'winner_team_key': winner_team_key,
                    'is_tied': matchup.is_tied if hasattr(matchup, 'is_tied') else False,
                    'status': matchup.status if hasattr(matchup, 'status') else 'unknown'
                })

            return {
                'week': week,
                'matchups': matchups
            }

        except Exception as e:
            print(f"Error fetching scoreboard for week {week}: {e}")
            return None

    @cache.memoize(timeout=900)  # 15 minutes
    def get_team_roster(self, team_id: str, week: int = None) -> Optional[Dict]:
        """Get team roster for a specific week.

        Args:
            team_id: Team ID
            week: Week number (uses current week if not specified)

        Returns:
            Dict with team roster information
        """
        if not self.yf_query:
            return None

        try:
            # Helper function for byte strings
            def to_str(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8')
                return str(val) if val is not None else ''

            roster_data = self.yf_query.get_team_roster_by_week(team_id, week)

            # YFPY might return just roster or a team object
            if hasattr(roster_data, 'roster'):
                # It's a team object with roster
                roster = roster_data.roster
                team_name = to_str(roster_data.name) if hasattr(roster_data, 'name') else f'Team {team_id}'
                manager_name = to_str(roster_data.manager.nickname) if hasattr(roster_data, 'manager') and roster_data.manager else 'Unknown'
            else:
                # It's just a roster object
                roster = roster_data
                team_name = f'Team {team_id}'
                manager_name = 'Unknown'

            players = []
            if roster and hasattr(roster, 'players'):
                for player in roster.players:
                    players.append({
                        'player_id': to_str(player.player_id),
                        'name': to_str(player.name.full) if hasattr(player.name, 'full') else to_str(player.name),
                        'position': to_str(player.display_position),
                        'team': to_str(player.editorial_team_abbr) if hasattr(player, 'editorial_team_abbr') else 'N/A',
                        'selected_position': to_str(player.selected_position.position) if hasattr(player, 'selected_position') else 'BN',
                        'points': float(player.player_points.total) if hasattr(player, 'player_points') else 0.0
                    })

            return {
                'team_id': to_str(team_id),
                'name': team_name,
                'manager': manager_name,
                'players': players,
                'week': week
            }

        except Exception as e:
            print(f"Error fetching roster for team {team_id}: {e}")
            return None

    def get_current_week(self) -> int:
        """Get current NFL week.

        Returns:
            Current week number
        """
        league_info = self.get_league_info()
        if league_info:
            return league_info.get('current_week', 1)
        return 1

    def refresh_cache(self):
        """Clear all cached data."""
        cache.clear()
        print("✓ Cache cleared")
