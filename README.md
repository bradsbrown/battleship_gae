# Battleship API


## Set-Up Instructions
1. Edit app.yaml to match the app ID you created in App Engine for this service.

1. In AppEngineLauncher, choose 'Add Existing Project' and select this directory.

1. Check the port number listed in AppEngine for this project (default is 8080). You can test the APIs by running the app locally through AppEngine, then directing your browser to `localhost:<port>/_ah/api/explorer`.

1. Once you have explored the API locally, you should deploy the app via AppEngineLauncher.


## Game Description
Battleship is a standard game played on a 10x10 grid, where each user sets up ships on their own board, then tries to guess the locations of their opponent's ships. Each guess contains an 'x' coordinate and a 'y' coordinate, corresponding to the left/right and up/down position on the board, respectively. Cell x1/y1 is the top left cell of the grid, 10/10 is the bottom right, 10/1 is the top right, 1/10 the bottom left. Each guess will either be a hit, or miss, and the board tracks a running count of each, as well as un-hit ship cells remaining. The game is over when one player hits all the cells on the opponent's board that contain a ship.

## Scoring
Battleship does not keep an in-game 'score'. The end record of a game is simply a winner - defined by the first player to hit all cells containing the other's ships. So, while there is no in-game score, we can keep a player ranking defined by win percentage - calculated by number of wins, divided by number of games played (then multiplied by 100). Players who haven't yet played a game will be assigned a win percentage of 0 until they have played at least one game.


## Steps to Play
1. If users are not already registered, they will need to `create_user`.

1. Then, you will start a `new_game` using the two usernames. Make sure to save the urlsafe_game_key returned when the game is created.

1. Each user will `insert_ship` for each ship on the board. You should determine in your app how many ships each user should have, and define the `length:` property for them so both users have a similarly designed board with equal number of ship cells.

1. Once ships are placed, users will take turns with the `make_guess` function to attempt to hit a cell on the opponent's board.

1. When one user has hit all ship cells to end the game, you will be returned a GameForm with game_over = True, and a winner passed in.

## Files Included
- **api.py**: main game engine, handles all game logic
- **app.yaml**: configuration for AppEngine
- **main.py**: handles taskqueue actions
- **models.py**: defines the classes for tracking game details, helper methods, and the various messages and input forms used in the game
- **utils.py**: two helper functions for retrieving items by either urlsafe_key or by using the two players
- **cron.yaml**: handles a cronjob to send hourly reminder email to the next player in each game.


## Endpoints Included
 - **create_user**
  - Path: 'user'
  - Method: POST
  - Parameters: user_name, email (optional)
  - Returns: Message confirming creation of the User.
  - Description: Creates a new User. user_name provided must be unique. Will raise a ConflictException if a User with that user_name already exists.

- **list_active_games**
  - Path: 'game/list'
  - Method: GET
  - Parameters: none
  - Returns: ActiveGamesForm
  - Description: Returns a list of games for which game_over is False.

- **new_game**
  - Path: 'game/new'
  - Method: POST
  - parameters: p1_username, p2_username
  - Returns: GameForm
  - Description: Checks that both users exist and aren't already in an active game together (raises an error if either is true). Then creates the game, and returns GameForm including urlsafe_game_key. Also adds a taskqueue to update the number of active games in memcache.

- **cancel_game**
  - Path: 'game/<urlsafe_game_key>/cancel'
  - Method: PUT
  - parameters: none
  - Returns: StringMessage confirming game is cancelled.

- **make_guess**
  - Path: 'game/<urlsafe_game_key>'
  - Method: PUT
  - parameters: player_name, guess_x, guess_y
  - Checks that player has the current turn (returns GameForm with message if not), then validates the guess against the ship cells. Checks that guess is both within the board and hasn't been previously guessed. If hit or miss, notifies player of this. If a hit ends the game, notifies player and marks game as over, updates both players' stats.

- **insert_ship**
  - Path: 'board/insert_ship'
  - Method: PUT
  - parameters: player_name, opponent_name, horizontal (boolean), start_x, start_y, length
  - Generates a ship with described characteristics on player board. Validates that the ship is entirely on the board (doesn't run over), that the ship doesn't overlap other ships, then inserts it onto the player board.

- **player_stats**
  - Path: 'player/<user_name>'
  - Method: GET
  - parameters: none
  - Description: Returns PlayerStatsForm

- **get_user_rankings**
  - Path: 'player'
  - Method: GET
  - parameters: none
  - Description: Returns PlayersStatsForm ranking all users by win percentage

- **get_ship_coords**
  - Path:'board/<player_name>/<opponent_name>/coords'
  - Method: GET
  - parameters: none
  - Description: returns CoordsForm listing ship cells from player's board.

- **get_game_history**
  - Path: 'game/<urlsafe_game_key>/history'
  - Method: GET
  - parameters: none
  - Description: returns a list of each player's moves and the result throughout the game.

- **get_user_games**
  - Path: 'player/<player_name>/games'
  - Method: GET
  - parameters: none
  - Description: returns a list of all a player's active games.


## Models Included
- **User**
  - stores unique user_name and optional email address
- **Game**
  - Stores unique game state. Associated with User model via KeyProperty
- **Board**
  - stores unique player board information (ship locations, guess locations, etc.). Associated with User model via KeyProperty


## Forms Included
- **GameForm**
  - Represents game information - player names, game_over flag, next player, winner, message.
- **BoardForm**
  - represents board information - hit cells, missed shots, remaining ship cells, message, and a urlsafe game key.
- **NewGameForm**
  - Inputs information required to start a new game - usernames for both players.
- **ActiveGamesForm**
  - Returns a GameForm-style listing of all games not yet completed.
- **InsertShipForm**
  - Inputs information required to insert a ship on player board - player and opponent name, ship length, start cell (x and y), orientation.
- **MakeGuessForm**
  - Inputs information required to test a player's guess againt opponent board - player name, guess (x and y) - game urlsafe key is passed in via the URL.
- **GetCoordsForm**
  - Inputs a player and opponent name to return the list of ship cells on player's board.
- **CoordsForm**
  - Represents a list of coordinates.
- **PlayerStatsForm**
  - Represents player's all-time stats - name, games won, games played.
- **PlayersStatsForm**
  - Represents player stats for all registered players.
- **GameHistoryForm**
  - Represents a list of moves and results for a single game.
- **StringMessage**
  - generic text message container.
