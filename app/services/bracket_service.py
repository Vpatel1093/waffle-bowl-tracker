"""Waffle Bowl bracket logic for tracking the losers bracket."""
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


class BracketService:
    """Service for managing Waffle Bowl bracket logic."""

    def __init__(self, num_teams: int = None):
        """Initialize bracket service.

        Args:
            num_teams: Number of teams in Waffle Bowl (default: 6 from env)
        """
        self.num_teams = num_teams or int(os.getenv('WAFFLE_BOWL_TEAMS', 6))

    def is_week_complete(self, week: int, current_week: int, scoreboard_data: Dict = None) -> bool:
        """Check if a given week is complete (after Monday night).

        Args:
            week: The week to check
            current_week: The current NFL week
            scoreboard_data: Optional scoreboard data to check matchup status

        Returns:
            True if the week is complete (games finished)
        """
        # If we're past this week, it's definitely complete
        if current_week > week:
            return True

        # If we're before this week, it's not complete
        if current_week < week:
            return False

        # We're in the current week - check scoreboard status
        # If scoreboard shows 'postevent', week is complete
        # If scoreboard shows 'midevent' or 'preevent', week is not complete
        if scoreboard_data and 'matchups' in scoreboard_data:
            for matchup in scoreboard_data['matchups']:
                status = matchup.get('status', '')
                if status == 'midevent' or status == 'preevent':
                    # Games still in progress or haven't started
                    return False
            # All matchups are postevent
            return True

        # Fallback: if no scoreboard data, assume not complete
        return False

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

        # Determine playoff weeks (static assignments)
        qf_week = 15      # Quarterfinals always week 15
        sf_week = 16      # Semifinals always week 16
        final_week = 17   # Finals always week 17

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
        scoreboard_data: Dict,
        yahoo_service=None,
        current_week: int = None
    ) -> Dict:
        """Update bracket with actual game results.

        Args:
            bracket: Bracket structure from create_bracket_structure
            scoreboard_data: Scoreboard data from YahooService
            yahoo_service: YahooService instance to fetch missing team scores
            current_week: Current NFL week number

        Returns:
            Updated bracket with winners/losers
        """
        if not scoreboard_data or 'matchups' not in scoreboard_data:
            return bracket

        week = scoreboard_data.get('week')

        # Use the flat team_scores lookup from scoreboard
        scores_by_team = scoreboard_data.get('team_scores', {})

        # Collect all Waffle Bowl team IDs that we need (as strings for consistency)
        waffle_team_ids = set()
        for team in bracket['teams']:
            waffle_team_ids.add(str(team['team_id']))

        # Fetch missing team scores (teams not in playoff scoreboard)
        if yahoo_service:
            missing_teams = waffle_team_ids - set(str(k) for k in scores_by_team.keys())

            for team_id in missing_teams:
                team_points = yahoo_service.get_team_points(team_id, week)
                if team_points:
                    scores_by_team[str(team_id)] = team_points

        # Check if this week is complete (all games finished)
        week_is_complete = False
        if current_week is not None:
            week_is_complete = self.is_week_complete(week, current_week, scoreboard_data)
        else:
            # If current_week not provided, assume we can determine winners
            week_is_complete = True

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
            for i, matchup in enumerate(qf['matchups']):
                team1_id = str(matchup['team1']['team_id'])  # Ensure string
                team2_id = str(matchup['team2']['team_id'])  # Ensure string

                # Initialize points_by_week if not exists
                if 'points_by_week' not in matchup['team1']:
                    matchup['team1']['points_by_week'] = {}
                if 'points_by_week' not in matchup['team2']:
                    matchup['team2']['points_by_week'] = {}

                # Add scores for each team independently, keyed by week
                if team1_id in scores_by_team:
                    matchup['team1']['points_by_week'][week] = scores_by_team[team1_id]['points']
                else:
                    matchup['team1']['points_by_week'][week] = 0.0
                if team2_id in scores_by_team:
                    matchup['team2']['points_by_week'][week] = scores_by_team[team2_id]['points']
                else:
                    matchup['team2']['points_by_week'][week] = 0.0

                # Only determine loser if week is complete AND both teams have scores
                team1_points = matchup['team1']['points_by_week'].get(week, 0.0)
                team2_points = matchup['team2']['points_by_week'].get(week, 0.0)
                if week_is_complete and team1_points is not None and team2_points is not None:
                    # Compare scores and assign the loser (using matchup team objects to preserve waffle_seed)
                    if team1_points < team2_points:
                        matchup['loser'] = matchup['team1']  # team1 loses
                    elif team2_points < team1_points:
                        matchup['loser'] = matchup['team2']  # team2 loses

        # Advance QF losers to semifinals (only if QF week is complete)
        # Use scoreboard data if we're processing the QF week, otherwise just compare week numbers
        qf_scoreboard = scoreboard_data if week == qf['week'] else None
        qf_week_complete = self.is_week_complete(qf['week'], current_week, qf_scoreboard) if current_week else True
        if qf_week_complete and qf['matchups'][0].get('loser') and qf['matchups'][1].get('loser'):
            sf = bracket['rounds']['semifinals']

            # Get both QF losers
            qf1_loser = qf['matchups'][0]['loser']
            qf2_loser = qf['matchups'][1]['loser']

            # Reward better season performance: higher waffle_seed = better regular season
            # Better QF loser gets easier matchup (Seed 2), worse loser gets Seed 1
            if qf1_loser['waffle_seed'] > qf2_loser['waffle_seed']:
                # QF1 loser had better season, gets Seed 2
                better_loser = qf1_loser
                worse_loser = qf2_loser
            else:
                # QF2 loser had better season, gets Seed 2
                better_loser = qf2_loser
                worse_loser = qf1_loser

            # Assign matchups based on season performance:
            # Better season performer plays Seed 1 (SF2) - easiest matchup in losers bracket
            # Worse season performer plays Seed 2 (SF1) - harder matchup
            sf['matchups'][0]['team1'] = worse_loser   # vs Seed 2 (harder)
            sf['matchups'][1]['team1'] = better_loser  # vs Seed 1 (easiest - worst team)

        # Update semifinals if this is SF week
        sf = bracket['rounds']['semifinals']
        if week == sf['week']:
            for i, matchup in enumerate(sf['matchups']):
                if matchup.get('team1') and matchup.get('team2'):
                    team1_id = str(matchup['team1']['team_id'])  # Ensure string
                    team2_id = str(matchup['team2']['team_id'])  # Ensure string

                    # Initialize points_by_week if not exists
                    if 'points_by_week' not in matchup['team1']:
                        matchup['team1']['points_by_week'] = {}
                    if 'points_by_week' not in matchup['team2']:
                        matchup['team2']['points_by_week'] = {}

                    # Add scores for each team independently, keyed by week
                    if team1_id in scores_by_team:
                        matchup['team1']['points_by_week'][week] = scores_by_team[team1_id]['points']
                    else:
                        matchup['team1']['points_by_week'][week] = 0.0
                    if team2_id in scores_by_team:
                        matchup['team2']['points_by_week'][week] = scores_by_team[team2_id]['points']
                    else:
                        matchup['team2']['points_by_week'][week] = 0.0

                    # Only determine loser if week is complete AND both teams have scores
                    team1_points = matchup['team1']['points_by_week'].get(week, 0.0)
                    team2_points = matchup['team2']['points_by_week'].get(week, 0.0)
                    if week_is_complete and team1_points is not None and team2_points is not None:
                        # Compare scores and assign the loser (using matchup team objects)
                        if team1_points < team2_points:
                            matchup['loser'] = matchup['team1']
                        elif team2_points < team1_points:
                            matchup['loser'] = matchup['team2']

        # Advance SF losers to finals (only if SF week is complete)
        # Use scoreboard data if we're processing the SF week, otherwise just compare week numbers
        sf_scoreboard = scoreboard_data if week == sf['week'] else None
        sf_week_complete = self.is_week_complete(sf['week'], current_week, sf_scoreboard) if current_week else True
        if sf_week_complete and sf['matchups'][0].get('loser') and sf['matchups'][1].get('loser'):
            final = bracket['rounds']['finals']
            final['matchup']['team1'] = sf['matchups'][0]['loser']
            final['matchup']['team2'] = sf['matchups'][1]['loser']

        # Update finals if this is final week
        final = bracket['rounds']['finals']
        if week == final['week'] and final['matchup'].get('team1') and final['matchup'].get('team2'):
            team1_id = str(final['matchup']['team1']['team_id'])  # Ensure string
            team2_id = str(final['matchup']['team2']['team_id'])  # Ensure string

            # Initialize points_by_week if not exists
            if 'points_by_week' not in final['matchup']['team1']:
                final['matchup']['team1']['points_by_week'] = {}
            if 'points_by_week' not in final['matchup']['team2']:
                final['matchup']['team2']['points_by_week'] = {}

            # Add scores for each team independently, keyed by week
            if team1_id in scores_by_team:
                final['matchup']['team1']['points_by_week'][week] = scores_by_team[team1_id]['points']
            else:
                final['matchup']['team1']['points_by_week'][week] = 0.0
            if team2_id in scores_by_team:
                final['matchup']['team2']['points_by_week'][week] = scores_by_team[team2_id]['points']
            else:
                final['matchup']['team2']['points_by_week'][week] = 0.0

            # Only determine loser if week is complete AND both teams have scores
            team1_points = final['matchup']['team1']['points_by_week'].get(week, 0.0)
            team2_points = final['matchup']['team2']['points_by_week'].get(week, 0.0)
            if week_is_complete and team1_points is not None and team2_points is not None:
                # Compare scores and assign the loser (using matchup team objects)
                if team1_points < team2_points:
                    final['matchup']['loser'] = final['matchup']['team1']
                elif team2_points < team1_points:
                    final['matchup']['loser'] = final['matchup']['team2']

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
