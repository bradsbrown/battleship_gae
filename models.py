from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    '''User profile'''
    user_name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    games_played = ndb.IntegerProperty(required=True, default=0)
    games_won = ndb.IntegerProperty(required=True, default=0)
    win_pctg = ndb.ComputedProperty(lambda self: 0 if self.games_played == 0
                                    else 100*(self.games_won / self.games_played))

    def to_form(self):
        form = PlayerStatsForm()
        form.user_name = self.user_name
        form.games_played = self.games_played
        form.games_won = self.games_won
        form.win_pctg = self.win_pctg

        return form


class Game(ndb.Model):
    '''Game tracker for players and game state'''
    player_1 = ndb.KeyProperty(required=True, kind='User')
    player_2 = ndb.KeyProperty(required=True, kind='User')
    game_over = ndb.BooleanProperty(required=True, default=False)
    next_player = ndb.KeyProperty(kind='User')
    winner = ndb.StringProperty(default=None)
    moves = ndb.StringProperty(repeated=True)

    @classmethod
    def new_game(cls, p1, p2):
        '''Initiates new game'''
        game = Game(player_1=p1, player_2=p2, next_player=p1)
        game.put()
        return game

    def end_game(self, winner):
        self.game_over = True
        self.winner = winner
        self.put()

    def insert_move(self, player_name, guess_coord, result):
        guess_coord = '{}_{}'.format(guess_coord)
        self.move = '[name:{}, coord:{}, result:{}]'.format(player_name,
                                                            guess_coord,
                                                            result)
        self.put()

    def to_form(self, message=''):
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.p1_name = self.player_1.get().user_name
        form.p2_name = self.player_2.get().user_name
        form.next_player = self.next_player.get().user_name
        form.game_over = self.game_over
        if self.winner:
            form.winner = self.winner
        else:
            form.winner = None
        form.message = message
        return form


class Board(ndb.Model):
    '''Tracks each player's board, keeps a list of ship coordinates'''
    urlsafe_game_key = ndb.StringProperty(required=True)
    player = ndb.KeyProperty(required=True, kind='User')
    opponent = ndb.KeyProperty(required=True, kind='User')
    ship_coord = ndb.StringProperty(repeated=True)
    hit_coord = ndb.StringProperty(repeated=True)
    miss_coord = ndb.StringProperty(repeated=True)

    def to_form(self, message=''):
        '''Returns board data in BoardForm'''
        form = BoardForm()
        form.urlsafe_key = self.urlsafe_game_key
        form.hits = len(self.hit_coord)
        form.misses = len(self.miss_coord)

        ship_cells = len(self.ship_coord)
        remaining = ship_cells - form.hits
        form.remaining = remaining
        form.message = message

        return form

    def giveCoords(self, nature):
        if nature == 'ship':
            q = self.ship_coord
        elif nature == 'hit':
            q = self.hit_coord
        elif nature == 'miss':
            q = self.miss_coord
        coords = []
        for item in q:
            x = int(item.split('_')[0])
            y = int(item.split('_')[1])
            coord = [x, y]
            coords.append(coord)

        return coords

    def coordsToForm(self, nature):
        coords = self.giveCoords(nature)
        return CoordsForm(coord=[coord for coord in coords])


class BoardForm(messages.Message):
    '''Board information for outbound board status'''
    urlsafe_key = messages.StringField(1, required=True)
    hits = messages.IntegerField(2, required=True)
    misses = messages.IntegerField(3, required=True)
    remaining = messages.IntegerField(4, required=True)
    message = messages.StringField(5)


class NewGameForm(messages.Message):
    '''Used to start a new game'''
    p1_username = messages.StringField(1, required=True)
    p2_username = messages.StringField(2, required=True)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    p1_name = messages.StringField(2, required=True)
    p2_name = messages.StringField(3, required=True)
    next_player = messages.StringField(4)
    game_over = messages.BooleanField(5, required=True)
    winner = messages.StringField(6)
    message = messages.StringField(7)


class GameHistoryForm(messages.Message):
    items = messages.StringField(1, repeated=True)


class ActiveGamesForm(messages.Message):
    items = messages.MessageField(GameForm, 1, repeated=True)


class InsertShipForm(messages.Message):
    '''Used to add a new ship to player board'''
    player_name = messages.StringField(1, required=True)
    opponent_name = messages.StringField(2, required=True)
    start_x = messages.IntegerField(3, required=True)
    start_y = messages.IntegerField(4, required=True)
    length = messages.IntegerField(5, required=True)
    horizontal = messages.BooleanField(6, required=True)


class MakeGuessForm(messages.Message):
    '''Inputs a player guess'''
    guess_x = messages.IntegerField(1, required=True)
    guess_y = messages.IntegerField(2, required=True)
    player_name = messages.StringField(3, required=True)


class GetCoordsForm(messages.Message):
    '''Take a player and opponent name to return player ship coords'''
    player_name = messages.StringField(1, required=True)
    opponent_name = messages.StringField(2, required=True)


class CoordsForm(messages.Message):
    '''Returns a coord pair'''
    coord = messages.StringField(1, repeated=True)


class PlayerStatsForm(messages.Message):
    '''returns outbound Player all-time wins vs. games played'''
    user_name = messages.StringField(1, required=True)
    games_played = messages.IntegerField(2, required=True)
    games_won = messages.IntegerField(3, required=True)
    win_pctg = messages.FloatField(4, required=True)


class PlayersStatsForm(messages.Message):
    '''return multiple outbound player stats'''
    players = messages.MessageField(PlayerStatsForm, 1, repeated=True)


class StringMessage(messages.Message):
    '''Outbound single message'''
    message = messages.StringField(1, required=True)
