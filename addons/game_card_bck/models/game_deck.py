# Archivo: models/game_deck.py
from odoo import models, fields, api

class GameDeck(models.Model):
    _name = 'game.deck'
    _description = 'Game Deck'

    name = fields.Char(string='Deck Name', required=True)
    user_id = fields.Many2one('game.user', string='Player', required=True)  # Relación con el jugador
    cards = fields.Many2many('game.card', string='Cards')  # Relación con las cartas del mazo
    class_id = fields.Many2one('game.class', string='Class')  # Clase asociada al mazo
    total_mana = fields.Integer(string='Total Mana Cost', compute='_compute_total_mana', store=True)  # Costo total de maná del mazo

    @api.depends('cards')
    def _compute_total_mana(self):
        for deck in self:
            deck.total_mana = sum(card.mana_class + card.mana_colorless for card in deck.cards)
