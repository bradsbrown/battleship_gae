import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import BattleshipApi

from models import User, Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        '''Sends a reminder to users who are due to make a move'''
        app_id = app_identity.get_application_id()
        games = Game.query(Game.game_over == False).fetch()
        next_users = []

        for game in games:
            next_users.append(game.next_player)

        for u_key in next_users:
            user = u_key.get()
            if user.email:
                subject = "Your turn!"
                body = "Hello {}, it's your turn to move \
                    on Battleship!".format(user.user_name)
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)


class UpdateActiveGames(webapp2.RequestHandler):
    '''Updates count of active games'''
    def post(self):
        BattleshipApi._cache_gameCount()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('tasks/updateactivegames', UpdateActiveGames),
], debug=True)
