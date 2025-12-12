"""Waffle Bowl bracket logic for tracking the losers bracket."""
import os
from typing import List, Dict, Optional


class BracketService:
    """Service for managing Waffle Bowl bracket logic."""

    def __init__(self, num_teams: int = None):
        """Initialize bracket service.

        Args:
            num_teams: Number of teams in Waffle Bowl (default: 6 from env)
        """
        self.num_teams = num_teams or int(os.getenv('WAFFLE_BOWL_TEAMS', 6))

    def get_waffle_bowl_teams(self, standings: List[Dict]) -> List[Dict]:
        """Get bottom N teams for Waffle Bowl.

        Teams are sorted by record (worst first), with points as tiebreaker.

        Args:
            standings: List of team standings

        Returns:
            List of teams in Waffle Bowl (worst to best)
        """
        if not standings:
            return []

        # Sort teams by wins (ascending), then points_for (ascending for tiebreak)
        # Lower wins = worse record = higher seed in Waffle Bowl
        # For ties, LOWER points_for = worse team (since this is losers bracket)
        sorted_teams = sorted(
            standings,
            key=lambda t: (t['wins'], t['points_for'])
        )

        # Get bottom N teams (worst teams)
        waffle_teams = sorted_teams[:self.num_teams]

        # Add seed numbers (1 = worst team, 6 = best of worst)
        for idx, team in enumerate(waffle_teams):
            team['waffle_seed'] = idx + 1

        return waffle_teams

    def create_bracket_structure(self, teams: List[Dict], current_week: int) -> Dict:
        """Create Waffle Bowl bracket structure.

        6-team bracket with byes:
        - Seeds 1-2 (worst two teams) get BYES in week 1
        - Week 1 (Quarterfinals): 3v6, 4v5
        - Week 2 (Semifinals): Losers of QF vs bye teams
        - Week 3 (Finals): Semifinals losers compete for last place

        Args:
            teams: List of Waffle Bowl teams with seeds
            current_week: Current NFL week

        Returns:
            Dict with bracket structure
        """
        if len(teams) < self.num_teams:
            return {'error': f'Need {self.num_teams} teams, got {len(teams)}'}

        # Determine playoff weeks (usually weeks 15, 16, 17)
        qf_week = current_week if current_week >= 15 else 15
        sf_week = qf_week + 1
        final_week = sf_week + 1

        bracket = {
            'num_teams': self.num_teams,
            'teams': teams,
            'rounds': {
                'quarterfinals': {
                    'week': qf_week,
                    'name': 'Quarterfinals',
                    'matchups': [
                        {
                            'id': 'qf1',
                            'team1': teams[2],  # Seed 3
                            'team2': teams[5],  # Seed 6
                            'winner': None,
                            'loser': None
                        },
                        {
                            'id': 'qf2',
                            'team1': teams[3],  # Seed 4
                            'team2': teams[4],  # Seed 5
                            'winner': None,
                            'loser': None
                        }
                    ],
                    'byes': [teams[0], teams[1]]  # Seeds 1 & 2 get byes
                },
                'semifinals': {
                    'week': sf_week,
                    'name': 'Semifinals',
                    'matchups': [
                        {
                            'id': 'sf1',
                            'team1': None,  # Loser of QF1
                            'team2': teams[1],  # Seed 2 (bye)
                            'winner': None,
                            'loser': None
                        },
                        {
                            'id': 'sf2',
                            'team1': None,  # Loser of QF2
                            'team2': teams[0],  # Seed 1 (bye - worst team)
                            'winner': None,
                            'loser': None
                        }
                    ]
                },
                'finals': {
                    'week': final_week,
                    'name': 'Waffle Bowl Final',
                    'matchup': {
                        'id': 'final',
                        'team1': None,  # Loser of SF1
                        'team2': None,  # Loser of SF2
                        'loser': None  # LAST PLACE!
                    }
                }
            }
        }

        return bracket

    def update_bracket_with_results(
        self,
        bracket: Dict,
        scoreboard_data: Dict
    ) -> Dict:
        """Update bracket with actual game results.

        Args:
            bracket: Bracket structure from create_bracket_structure
            scoreboard_data: Scoreboard data from YahooService

        Returns:
            Updated bracket with winners/losers
        """
        if not scoreboard_data or 'matchups' not in scoreboard_data:
            return bracket

        week = scoreboard_data.get('week')
        print(f"📊 Updating bracket with scoreboard for Week {week}")

        # Create a lookup for scores by team_id
        scores_by_team = {}
        for matchup in scoreboard_data['matchups']:
            if len(matchup['teams']) == 2:
                for team in matchup['teams']:
                    scores_by_team[team['team_id']] = {
                        'name': team['name'],
                        'points': team['points'],
                        'team_id': team['team_id'],
                        'team_key': team['team_key']
                    }
                    print(f"  Team {team['team_id']}: {team['name']} - {team['points']} pts")

        # Helper to find matchup loser
        def determine_loser(team1_data, team2_data):
            if team1_data['points'] < team2_data['points']:
                return team1_data
            elif team2_data['points'] < team1_data['points']:
                return team2_data
            return None  # Tie

        # Update quarterfinals if this is QF week
        qf = bracket['rounds']['quarterfinals']
        if week == qf['week']:
            print(f"🏈 Updating QF for Week {week}")
            for i, matchup in enumerate(qf['matchups']):
                team1_id = matchup['team1']['team_id']
                team2_id = matchup['team2']['team_id']
                print(f"  QF Matchup {i+1}: Looking for teams {team1_id} vs {team2_id}")

                if team1_id in scores_by_team and team2_id in scores_by_team:
                    print(f"    ✓ Found both teams!")
                    # Add scores to teams
                    matchup['team1']['points'] = scores_by_team[team1_id]['points']
                    matchup['team2']['points'] = scores_by_team[team2_id]['points']

                    # Determine loser
                    loser = determine_loser(scores_by_team[team1_id], scores_by_team[team2_id])
                    if loser:
                        matchup['loser'] = loser
                else:
                    print(f"    ✗ Missing teams! {team1_id} found: {team1_id in scores_by_team}, {team2_id} found: {team2_id in scores_by_team}")

        # Advance QF losers to semifinals
        if qf['matchups'][0].get('loser') and qf['matchups'][1].get('loser'):
            sf = bracket['rounds']['semifinals']
            sf['matchups'][0]['team1'] = qf['matchups'][0]['loser']
            sf['matchups'][1]['team1'] = qf['matchups'][1]['loser']

        # Update semifinals if this is SF week
        sf = bracket['rounds']['semifinals']
        if week == sf['week']:
            for matchup in sf['matchups']:
                if matchup.get('team1') and matchup.get('team2'):
                    team1_id = matchup['team1']['team_id']
                    team2_id = matchup['team2']['team_id']

                    if team1_id in scores_by_team and team2_id in scores_by_team:
                        matchup['team1']['points'] = scores_by_team[team1_id]['points']
                        matchup['team2']['points'] = scores_by_team[team2_id]['points']

                        loser = determine_loser(scores_by_team[team1_id], scores_by_team[team2_id])
                        if loser:
                            matchup['loser'] = loser

        # Advance SF losers to finals
        if sf['matchups'][0].get('loser') and sf['matchups'][1].get('loser'):
            final = bracket['rounds']['finals']
            final['matchup']['team1'] = sf['matchups'][0]['loser']
            final['matchup']['team2'] = sf['matchups'][1]['loser']

        # Update finals if this is final week
        final = bracket['rounds']['finals']
        if week == final['week'] and final['matchup'].get('team1') and final['matchup'].get('team2'):
            team1_id = final['matchup']['team1']['team_id']
            team2_id = final['matchup']['team2']['team_id']

            if team1_id in scores_by_team and team2_id in scores_by_team:
                final['matchup']['team1']['points'] = scores_by_team[team1_id]['points']
                final['matchup']['team2']['points'] = scores_by_team[team2_id]['points']

                loser = determine_loser(scores_by_team[team1_id], scores_by_team[team2_id])
                if loser:
                    final['matchup']['loser'] = loser

        return bracket

    def get_bracket_status(self, bracket: Dict, current_week: int) -> Dict:
        """Get human-readable bracket status.

        Args:
            bracket: Bracket structure
            current_week: Current NFL week

        Returns:
            Dict with status information
        """
        qf_week = bracket['rounds']['quarterfinals']['week']
        sf_week = bracket['rounds']['semifinals']['week']
        final_week = bracket['rounds']['finals']['week']

        if current_week < qf_week:
            status = 'upcoming'
            message = f"Waffle Bowl starts Week {qf_week}"
            current_round = None
        elif current_week == qf_week:
            status = 'active'
            message = "Quarterfinals in progress"
            current_round = 'quarterfinals'
        elif current_week == sf_week:
            status = 'active'
            message = "Semifinals in progress"
            current_round = 'semifinals'
        elif current_week == final_week:
            status = 'active'
            message = "🧇 WAFFLE BOWL FINAL - Last place on the line!"
            current_round = 'finals'
        else:
            status = 'complete'
            message = "Waffle Bowl complete"
            current_round = 'finals'

            # Get last place team
            final = bracket['rounds']['finals']['matchup']
            if final.get('loser'):
                message = f"Last place: {final['loser']['name']} 🧇"

        return {
            'status': status,
            'message': message,
            'current_round': current_round,
            'current_week': current_week
        }
