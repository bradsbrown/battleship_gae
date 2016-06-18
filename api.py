import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Board
from models import (
    StringMessage,
    BoardForm,
    NewGameForm,
    InsertShipForm,
    MakeGuessForm,
    CoordsForm,
    PlayerStatsForm,
    PlayersStatsForm,
    GetCoordsForm,
    ActiveGamesForm,
    GameForm,
    GameHistoryForm)

from utils import get_by_urlsafe, get_by_players

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)

URLSAFE_GAME_REQUEST = endpoints.ResourceContainer(
                        urlsafe_game_key=messages.StringField(1),)

MAKE_GUESS_REQUEST = endpoints.ResourceContainer(
                        MakeGuessForm,
                        urlsafe_game_key=messages.StringField(1),)

INSERT_SHIP_REQUEST = endpoints.ResourceContainer(
                        InsertShipForm,)

NEW_USER = endpoints.ResourceContainer(name=messages.StringField(1),
                                       email=messages.StringField(2))

PLAYER_REQUEST = endpoints.ResourceContainer(
                        user_name=messages.StringField(1))

SHIP_COORDS_REQUEST = endpoints.ResourceContainer(
                        player_name=messages.StringField(1),
                        opponent_name=messages.StringField(2))

GRID_SIZE = 10


@endpoints.api(name='battleship', version='v1')
class BattleshipApi(remote.Service):
    '''Game API'''

    @endpoints.method(response_message=ActiveGamesForm,
                      path='game/list',
                      name='list_active_games',
                      http_method='GET')
    def list_active_games(self, request):
        '''Returns a list of data for all in-progress games'''
        games = Game.query(Game.game_over == False).fetch()
        return ActiveGamesForm(items=[game.to_form() for game in games])

    @endpoints.method(request_message=NEW_USER,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        '''Create a user. Requires unique username'''
        test = User.query(User.user_name == request.name).get()
        if test:
            raise endpoints.ConflictException(
                'A user with that name already exists!')
        user = User(user_name=request.name, email=request.email)
        user.put()
        return StringMessage(message='Welcome, {}'.format(request.name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/new',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        '''Creates new game'''
        p1 = User.query(User.user_name == request.p1_username).get()
        p2 = User.query(User.user_name == request.p2_username).get()

        # check to verify players aren't already in ongoing game
        check = Game.query(ndb.OR(Game.player_1 == p1.key,
                                  Game.player_2 == p1.key))
        check = check.filter(ndb.OR(Game.player_1 == p2.key,
                                    Game.player_2 == p2.key))
        check = check.filter(Game.game_over == False).get()
        if check:
            raise endpoints.BadRequestException('These players already have \
                                          an active game!')

        try:
            game = Game.new_game(p1.key, p2.key)

        except ValueError:
            raise endpoints.BadRequestException('Both players must be \
                                                 valid users!')

        urlsafe_game_key = game.key.urlsafe()

        p1_board = Board(player=p1.key,
                         opponent=p2.key,
                         urlsafe_game_key=urlsafe_game_key,
                         hit_coord=[],
                         ship_coord=[],
                         miss_coord=[])
        p1_board.put()

        p2_board = Board(player=p2.key,
                         opponent=p1.key,
                         urlsafe_game_key=urlsafe_game_key,
                         hit_coord=[],
                         ship_coord=[],
                         miss_coord=[])
        p2_board.put()

        taskqueue.add(url='/tasks/updateactivegames')
        return game.to_form(message='The game is afoot!')

    @endpoints.method(request_message=URLSAFE_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        '''Allows cancellation of a game before it has been won'''
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        game.game_over = True
        game.winner = 'CANCELED'
        game.put()
        return StringMessage(message="Game "
                             "{} is canceled".format(request.urlsafe_game_key))

    @endpoints.method(request_message=MAKE_GUESS_REQUEST,
                      response_message=BoardForm,
                      path='game/{urlsafe_game_key}',
                      name='make_guess',
                      http_method='PUT')
    def make_guess(self, request):
        '''Makes a guess, returns board state with message'''
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        player = User.query(User.user_name == request.player_name).get()
        if player.key == game.player_1:
            opponent = User.query(User.key == game.player_2).get()
        if player.key == game.player_2:
            opponent = User.query(User.key == game.player_1).get()

        board = get_by_players(player.key, opponent.key, 'Board')

        if player.key != game.next_player:
            return board.to_form(message="It's not your turn yet!")

        if game.game_over:
            winner = game.winner
            return board.to_form(message='Game already over,'
                                 '{} won!'.format(winner))

        ship_coords = board.giveCoords('ship')
        miss_coords = board.giveCoords('miss')
        hit_coords = board.giveCoords('hit')

        guess_coord = [request.guess_x, request.guess_y]

        # verifies guess is within board
        if not set(guess_coord).issubset(set(range(1, GRID_SIZE + 1))):
            raise endpoints.BadRequestException("Guess outside of board range")

        # checks if the guess has already been entered
        if guess_coord in miss_coords or guess_coord in hit_coords:
            return board.to_form(message="You've already guessed"
                                         "those coordinates!")

        # if guess is novel, checks for a hit
        if guess_coord in ship_coords:
            board.hit_coord.append('{}_{}'.format(*guess_coord))
            board.put()
            hit_coords = board.giveCoords('hit')

            # in a hit, checks if all ship cells are hit, announces win if so
            if len(ship_coords) == len(hit_coords):
                game.game_over = True
                game.winner = player.user_name
                game.put()

                game.insert_move(player.user_name, guess_coord, 'Win')

                player.games_won = player.games_won + 1
                player.games_played = player.games_played + 1
                player.put()

                opponent.games_played = opponent.games_played + 1
                opponent.put()
                return board.to_form('Congrats, you won!')

            # if not the final hit, notifies user
            game.next_player = opponent.key
            game.put()
            game.insert_move(player.user_name, guess_coord, 'Hit')
            return board.to_form('A hit! Keep going!')

        board.miss_coord.append('{}_{}'.format(*guess_coord))
        board.put()

        game.next_player = opponent.key
        game.put()
        game.insert_move(player.user_name, guess_coord, 'Miss')
        return board.to_form('Sorry, you missed!')

    @endpoints.method(request_message=INSERT_SHIP_REQUEST,
                      response_message=BoardForm,
                      path='board/insert_ship',
                      name='insert_ship',
                      http_method='PUT')
    def insert_ship(self, request):
        '''Adds a new ship to player's board'''
        player = User.query(User.user_name == request.player_name).get()
        opponent = User.query(User.user_name == request.opponent_name).get()
        board = get_by_players(player.key,
                               opponent.key,
                               'Board')

        if not board:
            return BoardForm(message='Board not found.')

        # create the array with all coordinates for new ship
        new_ship = []
        new_ship.append((request.start_x, request.start_y))
        if request.horizontal:
            for i in range(1, request.length):
                new_ship.append((request.start_x + i, request.start_y))
        if not request.horizontal:
            for i in range(1, request.length):
                new_ship.append((request.start_x, request.start_y+i))

        existing_ship_coords = board.giveCoords('ship')
        print existing_ship_coords
        print new_ship
        for coord in new_ship:
            # checks for overlap with existing ships
            if coord in existing_ship_coords:
                return board.to_form('That ship overlaps another. \
                                     Try again!')

            # checks that all coordinates are on the board
            inBounds = True
            if coord[0] > GRID_SIZE or coord[1] > GRID_SIZE:
                inBounds = False
            if coord[0] < 1 or coord[1] < 1:
                inBounds = False
            if not inBounds:
                return board.to_form('That ship goes off the board. \
                                     Try again!')

        board.ship_coord = [('{}_{}').format(*coord) for coord in new_ship]
        board.put()

        return board.to_form(message='Ship added successfully!')

    @endpoints.method(request_message=PLAYER_REQUEST,
                      response_message=PlayerStatsForm,
                      path='player/{user_name}',
                      name='player_stats',
                      http_method='GET')
    def player_stats(self, request):
        '''returns player stat info for a given player'''
        player = User.query(User.user_name == request.user_name).get()
        if not player:
            raise ValueError('Player does not exist!')
        return player.to_form()

    @endpoints.method(response_message=PlayersStatsForm,
                      path='player',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        '''returns player stat info for all players'''
        players = User.query().order(-User.win_pctg)
        return PlayersStatsForm(players=[player.to_form()
                                         for player in players])

    @endpoints.method(request_message=SHIP_COORDS_REQUEST,
                      response_message=CoordsForm,
                      path='board/{player_name}/{opponent_name}/coords',
                      name='get_ship_coords',
                      http_method='GET')
    def get_ship_coords(self, request):
        '''Given a player and opponent name, returns the player's
        list of ships on the game board'''
        player = User.query(User.user_name == request.player_name).get()
        opponent = User.query(User.user_name == request.opponent_name).get()
        board = get_by_players(player.key, opponent.key, 'Board')
        return CoordsForm(coord=[coord for coord in board.ship_coord])

    @endpoints.method(request_message=URLSAFE_GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        '''Returns a list of moves made in game, with player and result'''
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return GameHistoryForm(items=[move for move in game.moves])

    @endpoints.method(request_message=PLAYER_REQUEST,
                      response_message=ActiveGamesForm,
                      path='player/{user_name}/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        '''Returns a list of data for all a player's in-progress games'''
        games = Game.query(ndb.OR(Game.player_1 == request.user_name,
                                  Game.player_2 == request.user_name))
        games = games.filter(Game.game_over == False).fetch()
        return ActiveGamesForm(items=[game.to_form() for game in games])

    @staticmethod
    def _cache_gameCount():
        '''Populates memcount with a number of active games'''
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
        else:
            count = 0
        memcache.set('ACTIVE_GAMES',
                     'There are {} game in play right now.'.format(count))


api = endpoints.api_server([BattleshipApi])
