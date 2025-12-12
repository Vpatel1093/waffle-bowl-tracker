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
                    bracket = bracket_svc.update_bracket_with_results(bracket, scoreboard)

        # Get bracket status
        bracket_status = bracket_svc.get_bracket_status(bracket, current_week)

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
