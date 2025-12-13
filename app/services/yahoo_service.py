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

            matchups = []
            # Also collect all team scores in a flat dict for easy lookup
            team_scores = {}

            for matchup in scoreboard.matchups:
                teams = []
                for team in matchup.teams:
                    team_data = {
                        'team_id': to_str(team.team_id),
                        'team_key': to_str(team.team_key),
                        'name': to_str(team.name),
                        'points': float(team.team_points.total) if hasattr(team, 'team_points') else 0.0,
                        'projected_points': float(team.team_projected_points.total) if hasattr(team, 'team_projected_points') else 0.0
                    }
                    teams.append(team_data)
                    # Store in lookup dict
                    team_scores[team_data['team_id']] = team_data

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
                'matchups': matchups,
                'team_scores': team_scores  # Flat lookup for all teams
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

            # Use get_team_roster_player_stats_by_week to get stats
            roster_data = self.yf_query.get_team_roster_player_stats_by_week(team_id, week)

            team_name = f'Team {team_id}'
            manager_name = 'Unknown'

            # YFPY returns a list of players directly
            players = []
            if isinstance(roster_data, list):
                for player in roster_data:
                    player_points = 0.0
                    if hasattr(player, 'player_points') and hasattr(player.player_points, 'total'):
                        player_points = float(player.player_points.total)

                    player_name = 'Unknown'
                    if hasattr(player, 'name'):
                        if hasattr(player.name, 'full'):
                            player_name = to_str(player.name.full)
                        else:
                            player_name = to_str(player.name)

                    selected_position = 'BN'
                    if hasattr(player, 'selected_position'):
                        if hasattr(player.selected_position, 'position'):
                            selected_position = to_str(player.selected_position.position)
                        else:
                            selected_position = to_str(player.selected_position)

                    players.append({
                        'player_id': to_str(player.player_id) if hasattr(player, 'player_id') else '',
                        'name': player_name,
                        'position': to_str(player.display_position) if hasattr(player, 'display_position') else 'N/A',
                        'team': to_str(player.editorial_team_abbr) if hasattr(player, 'editorial_team_abbr') else 'N/A',
                        'selected_position': selected_position,
                        'points': player_points
                    })

            # Sort players: starters in lineup order, then bench
            # Lineup order: QB, WR, WR, RB, RB, TE, W/R/T, K, DEF, BN
            position_order = {
                'QB': 0,
                'WR': 1,
                'RB': 3,
                'TE': 5,
                'W/R/T': 6,
                'FLEX': 6,  # Some leagues use FLEX instead of W/R/T
                'K': 7,
                'DEF': 8,
                'BN': 9,
                'IR': 10  # Injured reserve at the end
            }

            def sort_key(p):
                pos = p['selected_position']
                # Get position order, default to 99 for unknown positions
                order = position_order.get(pos, 99)
                # Secondary sort by name for same positions (e.g., multiple WRs)
                return (order, p['name'])

            players.sort(key=sort_key)

            return {
                'team_id': to_str(team_id),
                'name': team_name,
                'manager': manager_name,
                'players': players,
                'week': week
            }

        except Exception as e:
            print(f"Error fetching roster for team {team_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @cache.memoize(timeout=15)  # 15 seconds for live scores
    def get_team_points(self, team_id: str, week: int) -> Optional[Dict]:
        """Get team's total points for a specific week.

        This is useful for teams not in the scoreboard (eliminated from playoffs).

        Args:
            team_id: Team ID
            week: Week number

        Returns:
            Dict with team points info or None if error
        """
        if not self.yf_query:
            return None

        try:
            # Helper function for byte strings
            def to_str(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8')
                return str(val) if val is not None else ''

            # Get roster with player stats for the week
            roster_stats = self.yf_query.get_team_roster_player_stats_by_week(team_id, week)

            if not roster_stats:
                return None

            # Extract team name and sum player points
            team_points = 0.0
            team_name = f'Team {team_id}'

            # Check if roster_stats is a list (YFPY returns list of players)
            if isinstance(roster_stats, list):
                for player in roster_stats:
                    player_points = 0.0

                    # Check if player is a starter (not on bench)
                    selected_position = 'BN'
                    if hasattr(player, 'selected_position'):
                        if hasattr(player.selected_position, 'position'):
                            selected_position = to_str(player.selected_position.position)
                        else:
                            selected_position = to_str(player.selected_position)

                    # Try to get player points
                    if hasattr(player, 'player_points'):
                        if hasattr(player.player_points, 'total'):
                            player_points = float(player.player_points.total)

                    # Only count starters (not bench players)
                    if selected_position != 'BN':
                        team_points += player_points

            # Handle if it's an object with roster
            elif hasattr(roster_stats, 'name'):
                team_name = to_str(roster_stats.name)

            return {
                'team_id': to_str(team_id),
                'name': team_name,
                'points': team_points,
                'week': week
            }
        except Exception as e:
            print(f"Error fetching points for team {team_id}, week {week}: {e}")
            import traceback
            traceback.print_exc()
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
