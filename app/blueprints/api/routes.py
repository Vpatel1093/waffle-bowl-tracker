"""API blueprint routes for HTMX endpoints."""
from flask import render_template, current_app, g
from app.blueprints.api import api
from app import limiter, cache
from app.services.yahoo_service import YahooService
from app.services.bracket_service import BracketService
from concurrent.futures import ThreadPoolExecutor, as_completed


@cache.memoize(timeout=30)  # Match CACHE_LIVE_SCORES
def get_complete_bracket():
    """Get complete bracket with all data - cached for 30 seconds.

    Optimized to only fetch ACTIVE week data (not all 3 weeks).
    Pre-fetches rosters for active week only (6 rosters vs 18).

    Caching strategy:
    - This function: 30 seconds (aligned with live scores)
    - Scoreboards: 30s for active week, 24h for completed weeks (smart caching)
    - Rosters: 15 minutes (don't change during games)
    - Standings: 60 seconds

    Returns:
        Dict with bracket, current_week, bracket_status, standings, and rosters
    """
    try:
        yahoo = g.yahoo_service  # Use cached service instance
        bracket_svc = BracketService()

        # Parallelize initial data fetching
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Fetch standings and current week in parallel
            standings_future = executor.submit(yahoo.get_league_standings)
            current_week_future = executor.submit(yahoo.get_current_week)

            standings = standings_future.result()
            current_week = current_week_future.result()

        if not standings:
            return None

        # Get Waffle Bowl teams (bottom 6)
        waffle_teams = bracket_svc.get_waffle_bowl_teams(standings)

        # Create bracket structure
        bracket = bracket_svc.create_bracket_structure(waffle_teams, current_week)

        # Get all relevant weeks
        qf_week = bracket['rounds']['quarterfinals']['week']
        sf_week = bracket['rounds']['semifinals']['week']
        final_week = bracket['rounds']['finals']['week']

        # Determine active week (only fetch scores for week in progress)
        if current_week == qf_week:
            active_week = qf_week
        elif current_week == sf_week:
            active_week = sf_week
        elif current_week == final_week:
            active_week = final_week
        elif current_week > qf_week:
            # Between rounds, use most recent
            active_week = min(current_week, final_week)
        else:
            active_week = None

        # Pre-fetch rosters ONLY for active week (not all 3 weeks) - PARALLELIZED
        rosters = {}
        team_points_by_week = {}

        if active_week:
            # Fetch all team rosters in parallel
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit all roster fetch tasks
                roster_futures = {
                    executor.submit(yahoo.get_team_roster, team['team_id'], active_week): team['team_id']
                    for team in waffle_teams
                }

                # Collect results as they complete
                for future in as_completed(roster_futures):
                    team_id = roster_futures[future]
                    rosters[team_id] = {}
                    team_points_by_week[team_id] = {}

                    try:
                        roster = future.result()
                        if roster:
                            rosters[team_id][active_week] = roster

                            # Calculate points from roster (starters only)
                            points = sum(
                                p['points'] for p in roster.get('players', [])
                                if p.get('selected_position') != 'BN'
                            )
                            team_points_by_week[team_id][active_week] = points
                    except Exception as e:
                        current_app.logger.error(f"Error fetching roster for team {team_id}: {e}")
        else:
            # No active week, initialize empty dicts
            for team in waffle_teams:
                team_id = team['team_id']
                rosters[team_id] = {}
                team_points_by_week[team_id] = {}

        # Fetch scoreboard ONLY for active week
        if active_week and active_week <= current_week:
            scoreboard = yahoo.get_scoreboard(active_week)
            if scoreboard:
                # Merge roster-calculated points for missing teams
                if 'team_scores' not in scoreboard:
                    scoreboard['team_scores'] = {}

                for team_id, weeks in team_points_by_week.items():
                    if active_week in weeks and team_id not in scoreboard['team_scores']:
                        scoreboard['team_scores'][team_id] = {
                            'team_id': team_id,
                            'points': weeks[active_week],
                            'week': active_week
                        }

                # Update bracket with active week results
                bracket = bracket_svc.update_bracket_with_results(
                    bracket, scoreboard, yahoo_service=None, current_week=current_week
                )

        # Get bracket status
        bracket_status = bracket_svc.get_bracket_status(bracket, current_week)

        return {
            'bracket': bracket,
            'current_week': current_week,
            'bracket_status': bracket_status,
            'standings': standings,
            'rosters': rosters  # All rosters pre-fetched
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
        # Get cached bracket data (has pre-fetched rosters!)
        data = get_complete_bracket()
        if not data:
            return render_template('components/team_details.html', team=None, roster=None)

        current_week = data['current_week']
        standings = data['standings']
        rosters = data['rosters']

        # Get roster from pre-fetched data (no API call!)
        roster = rosters.get(team_id, {}).get(current_week)

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
        # Get cached bracket (has all scoreboard data AND pre-fetched rosters!)
        data = get_complete_bracket()
        if not data:
            return render_template('components/matchup_details.html', matchup=None)

        bracket = data['bracket']
        rosters = data['rosters']

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

        # Get rosters from pre-fetched data (no API calls!)
        team1_roster = rosters.get(team1_id, {}).get(week)
        team2_roster = rosters.get(team2_id, {}).get(week)

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
