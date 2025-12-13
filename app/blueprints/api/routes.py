"""API blueprint routes for HTMX endpoints."""
from flask import render_template, current_app
from app.blueprints.api import api
from app import limiter, cache
from app.services.yahoo_service import YahooService
from app.services.bracket_service import BracketService


@cache.memoize(timeout=15)
def get_complete_bracket():
    """Get complete bracket with all data - cached for 15 seconds.

    Returns:
        Dict with bracket, current_week, and bracket_status, or None if error
    """
    try:
        yahoo = YahooService()
        bracket_svc = BracketService()

        # Get standings
        standings = yahoo.get_league_standings()
        if not standings:
            return None

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

        return {
            'bracket': bracket,
            'current_week': current_week,
            'bracket_status': bracket_status,
            'standings': standings
        }

    except Exception as e:
        current_app.logger.error(f"Error building complete bracket: {e}")
        return None


@api.route('/bracket/refresh')
@limiter.limit("60 per minute")
def refresh_bracket():
    """Return updated bracket HTML fragment with status."""
    try:
        data = get_complete_bracket()
        if not data:
            return render_template('components/bracket.html', bracket=None, bracket_status=None)

        return render_template(
            'components/bracket.html',
            bracket=data['bracket'],
            bracket_status=data['bracket_status']
        )

    except Exception as e:
        current_app.logger.error(f"Error refreshing bracket: {e}")
        return render_template('components/bracket.html', bracket=None, bracket_status=None)


@api.route('/bracket/status')
@limiter.limit("60 per minute")
def bracket_status():
    """Return bracket status HTML fragment."""
    try:
        data = get_complete_bracket()
        if not data:
            return '<div class="text-center"><p class="text-lg">Unable to load bracket status</p></div>'

        status = data['bracket_status']
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

        # Get cached bracket data (has standings and current week)
        data = get_complete_bracket()
        if not data:
            return render_template('components/team_details.html', team=None, roster=None)

        current_week = data['current_week']
        standings = data['standings']

        # Get team roster
        roster = yahoo.get_team_roster(team_id, current_week)

        # Find team in standings
        team = next((t for t in standings if t['team_id'] == team_id), None)

        return render_template(
            'components/team_details.html',
            team=team,
            roster=roster
        )

    except Exception as e:
        current_app.logger.error(f"Error fetching team details: {e}")
        return render_template('components/team_details.html', team=None, roster=None)


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

        # Get cached bracket (already has all scoreboard data!)
        data = get_complete_bracket()
        if not data:
            return render_template('components/matchup_details.html', matchup=None)

        bracket = data['bracket']

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
                return '<div class="text-center py-8"><p class="text-gray-600">Matchup not yet determined</p></div>'
            team1_id = matchup['team1']['team_id']
            team2_id = matchup['team2']['team_id']
            week = bracket['rounds']['semifinals']['week']
            round_display = 'Semifinals'
        elif round_name == 'final':
            matchup = bracket['rounds']['finals']['matchup']
            if not matchup.get('team1') or not matchup.get('team2'):
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
