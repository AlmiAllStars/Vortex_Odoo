# Archivo: models/game_collection.py
from odoo import models, fields, api

class GameCollection(models.Model):
    _name = 'game.collection'
    _description = 'Game Collection'

    user_id = fields.Many2one('game.user', string='Player', required=True)  # Relación con el jugador
    card_id = fields.Many2one('game.card', string='Card', required=True)  # Relación con la carta
    quantity = fields.Integer(string='Quantity', default=1)  # Número de copias que posee
