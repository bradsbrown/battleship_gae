"""utils.py - File for collecting general utility functions."""

import logging
from google.appengine.ext import ndb
import endpoints
from models import Board, Game

def get_by_urlsafe(urlsafe, model):
    """Returns an ndb.Model entity that the urlsafe key points to. Checks
        that the type of entity returned is of the correct kind. Raises an
        error if the key String is malformed or the entity is of the incorrect
        kind
    Args:
        urlsafe: A urlsafe key string
        model: The expected entity kind
    Returns:
        The entity that the urlsafe Key string points to or None if no entity
        exists.
    Raises:
        ValueError:"""
    try:
        key = ndb.Key(urlsafe=urlsafe)
    except TypeError:
        raise endpoints.BadRequestException('Invalid Key')
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise endpoints.BadRequestException('Invalid Key')
        else:
            raise

    entity = key.get()
    if not entity:
        return None
    if not isinstance(entity, model):
        raise ValueError('Incorrect Kind')
    return entity


def get_by_players(p1, p2, model):
    if model == 'Board':
        query = Board.query(Board.player == p1)
        query = query.filter(Board.opponent == p2)
        board = query.get()
        return board

    if model == 'Game':
        query = Game.query(ndb.OR(Game.player_1 == p1, Game.player_2 == p1))
        query = query.filter(ndb.OR(Game.player_1 == p2, Game.player_2 == p2))
        game = query.get()
        return game
