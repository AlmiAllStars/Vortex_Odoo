# Archivo: models/game_card_deck_rel.py
from odoo import models, fields

class GameCardDeckRel(models.Model):
    _name = 'game.card.deck.rel'
    _description = 'Card-Deck Relationship'

    game_card_id = fields.Many2one('game.card', string='Card', required=True, ondelete='cascade')
    game_deck_id = fields.Many2one('game.deck', string='Deck', required=True, ondelete='cascade')
    quantity = fields.Integer(string='Quantity', default=1)

    # Campo relacionado para usar en los gráficos
    mana_class = fields.Integer(related='game_card_id.mana_class', store=True)
    rarity = fields.Selection(related='game_card_id.rarity', store=True)
