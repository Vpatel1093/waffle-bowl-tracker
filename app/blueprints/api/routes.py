"""API blueprint routes for HTMX endpoints."""
from flask import render_template, current_app
from app.blueprints.api import api
from app import limiter
from app.services.yahoo_service import YahooService
from app.services.bracket_service import BracketService


@api.route('/bracket/refresh')
@limiter.limit("60 per minute")
def refresh_bracket():
    """Return updated bracket HTML fragment."""
    try:
        # Initialize services
        yahoo = YahooService()
        bracket_svc = BracketService()

        # Get standings
        standings = yahoo.get_league_standings()
        if not standings:
            return render_template('components/bracket.html', bracket=None)

        # Get Waffle Bowl teams (bottom 6)
        waffle_teams = bracket_svc.get_waffle_bowl_teams(standings)

        # Get current week
        current_week = yahoo.get_current_week()

        # Create bracket structure
        bracket = bracket_svc.create_bracket_structure(waffle_teams, current_week)

        # Get scoreboard data for all relevant weeks
        qf_week = bracket['rounds']['quarterfinals']['week']
        sf_week = bracket['rounds']['semifinals']['week']
        final_week = bracket['rounds']['finals']['week']

        # Fetch scoreboards for completed/ongoing weeks
        for week in [qf_week, sf_week, final_week]:
            if week <= current_week:
                scoreboard = yahoo.get_scoreboard(week)
                if scoreboard:
                    bracket = bracket_svc.update_bracket_with_results(bracket, scoreboard, yahoo, current_week)

        # Get bracket status
        bracket_status = bracket_svc.get_bracket_status(bracket, current_week)

        # Debug output
        print(f"\n🔍 DEBUG - Current week: {current_week}")
        print(f"🔍 QF week: {qf_week}, SF week: {sf_week}, Final week: {final_week}")
        print(f"🔍 Fetching scoreboards for weeks <= {current_week}")

        return render_template(
            'components/bracket.html',
            bracket=bracket,
            bracket_status=bracket_status
        )

    except Exception as e:
        current_app.logger.error(f"Error refreshing bracket: {e}")
        return render_template('components/bracket.html', bracket=None)


@api.route('/bracket/status')
@limiter.limit("60 per minute")
def bracket_status():
    """Return bracket status HTML fragment."""
    try:
        yahoo = YahooService()
        bracket_svc = BracketService()

        standings = yahoo.get_league_standings()
        if not standings:
            return '<div class="text-center"><p class="text-lg">Unable to load bracket status</p></div>'

        waffle_teams = bracket_svc.get_waffle_bowl_teams(standings)
        current_week = yahoo.get_current_week()
        bracket = bracket_svc.create_bracket_structure(waffle_teams, current_week)
        status = bracket_svc.get_bracket_status(bracket, current_week)

        return f'''
        <div class="flex items-center justify-center">
            <div class="text-center">
                <h2 class="text-2xl font-bold mb-2">Current Status</h2>
                <p class="text-lg">{status['message']}</p>
            </div>
        </div>
        '''
    except Exception as e:
        current_app.logger.error(f"Error fetching bracket status: {e}")
        return '<div class="text-center"><p class="text-lg">Error loading status</p></div>'


@api.route('/team/<team_id>/details')
@limiter.limit("60 per minute")
def team_details(team_id):
    """Return team details modal HTML fragment."""
    try:
        yahoo = YahooService()
        bracket_svc = BracketService()

        # Get current week
        current_week = yahoo.get_current_week()

        # Get team roster
        roster = yahoo.get_team_roster(team_id, current_week)

        # Get standings to find this team's info
        standings = yahoo.get_league_standings()
        team = None
        if standings:
            # Get Waffle Bowl teams and find this one
            waffle_teams = bracket_svc.get_waffle_bowl_teams(standings)
            team = next((t for t in waffle_teams if t['team_id'] == team_id), None)

            # If not in Waffle Bowl, check all standings
            if not team:
                team = next((t for t in standings if t['team_id'] == team_id), None)

        return render_template(
            'components/team_details.html',
            team=team,
            roster=roster
        )

    except Exception as e:
        current_app.logger.error(f"Error fetching team details: {e}")
        return render_template('components/team_details.html', team=None)


@api.route('/matchup/<round_name>/<int:matchup_index>/details')
@limiter.limit("60 per minute")
def matchup_details(round_name, matchup_index):
    """Return head-to-head matchup modal HTML fragment.

    Args:
        round_name: 'qf', 'sf', or 'final'
        matchup_index: 0 or 1 (for qf/sf), ignored for final
    """
    try:
        yahoo = YahooService()
        bracket_svc = BracketService()

        # Get standings and build bracket
        standings = yahoo.get_league_standings()
        if not standings:
            return render_template('components/matchup_details.html', matchup=None)

        waffle_teams = bracket_svc.get_waffle_bowl_teams(standings)
        current_week = yahoo.get_current_week()
        bracket = bracket_svc.create_bracket_structure(waffle_teams, current_week)

        # Fetch scoreboard data for all relevant weeks
        qf_week = bracket['rounds']['quarterfinals']['week']
        sf_week = bracket['rounds']['semifinals']['week']
        final_week = bracket['rounds']['finals']['week']

        for week in [qf_week, sf_week, final_week]:
            if week <= current_week:
                scoreboard = yahoo.get_scoreboard(week)
                if scoreboard:
                    bracket = bracket_svc.update_bracket_with_results(bracket, scoreboard, yahoo, current_week)

        # Extract the matchup based on round_name
        matchup = None
        team1_id = None
        team2_id = None
        week = None

        if round_name == 'qf':
            matchup = bracket['rounds']['quarterfinals']['matchups'][matchup_index]
            team1_id = matchup['team1']['team_id']
            team2_id = matchup['team2']['team_id']
            week = bracket['rounds']['quarterfinals']['week']
            round_display = 'Quarterfinals'
        elif round_name == 'sf':
            matchup = bracket['rounds']['semifinals']['matchups'][matchup_index]
            if not matchup.get('team1') or not matchup.get('team2'):
                # Teams not yet determined
                return '<div class="text-center py-8"><p class="text-gray-600">Matchup not yet determined</p></div>'
            team1_id = matchup['team1']['team_id']
            team2_id = matchup['team2']['team_id']
            week = bracket['rounds']['semifinals']['week']
            round_display = 'Semifinals'
        elif round_name == 'final':
            matchup = bracket['rounds']['finals']['matchup']
            if not matchup.get('team1') or not matchup.get('team2'):
                # Teams not yet determined
                return '<div class="text-center py-8"><p class="text-gray-600">Matchup not yet determined</p></div>'
            team1_id = matchup['team1']['team_id']
            team2_id = matchup['team2']['team_id']
            week = bracket['rounds']['finals']['week']
            round_display = 'Waffle Bowl Final'
        else:
            return '<div class="text-center py-8"><p class="text-gray-600">Invalid round</p></div>'

        # Fetch rosters for both teams for the specific week
        team1_roster = yahoo.get_team_roster(team1_id, week)
        team2_roster = yahoo.get_team_roster(team2_id, week)

        # Override roster names with actual team names from matchup
        if team1_roster:
            team1_roster['name'] = matchup['team1']['name']
        if team2_roster:
            team2_roster['name'] = matchup['team2']['name']

        # Calculate total points (starters only) from rosters
        def calculate_total(roster):
            if not roster or 'players' not in roster:
                return 0.0
            return sum(p['points'] for p in roster['players'] if p['selected_position'] != 'BN')

        team1_points = calculate_total(team1_roster)
        team2_points = calculate_total(team2_roster)

        # Prepare matchup data
        matchup_data = {
            'round_name': round_display,
            'week': week,
            'team1_points': team1_points,
            'team2_points': team2_points
        }

        return render_template(
            'components/matchup_details.html',
            matchup=matchup_data,
            team1_roster=team1_roster,
            team2_roster=team2_roster
        )

    except Exception as e:
        current_app.logger.error(f"Error fetching matchup details: {e}")
        import traceback
        traceback.print_exc()
        return '<div class="text-center py-8"><p class="text-gray-600">Error loading matchup</p></div>'
