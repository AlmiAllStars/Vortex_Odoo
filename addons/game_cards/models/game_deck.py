# Archivo: models/game_deck.py
from odoo import models, fields, api

class GameDeck(models.Model):
    _name = 'game.deck'
    _description = 'Game Deck'

    name = fields.Char(string='Deck Name', required=True)
    user_id = fields.Many2one('game.user', string='Player', required=True)  # Relación con el jugador
    class_id = fields.Many2one('game.class', string='Class')  # Clase asociada al mazo
    total_mana = fields.Integer(string='Total Mana Cost', compute='_compute_total_mana', store=True)  # Costo total de maná del mazo

    # Relación con el modelo intermedio
    card_rel_ids = fields.One2many('game.card.deck.rel', 'game_deck_id', string='Cards in Deck')

    @api.depends('card_rel_ids.game_card_id', 'card_rel_ids.game_card_id.mana_class', 'card_rel_ids.game_card_id.mana_colorless')
    def _compute_total_mana(self):
        for deck in self:
            deck.total_mana = sum(rel.game_card_id.mana_class + rel.game_card_id.mana_colorless for rel in deck.card_rel_ids)

    def open_statistics(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deck Statistics',
            'res_model': 'game.card.deck.rel',
            'view_mode': 'graph',
            'view_id': self.env.ref('game_cards.view_game_deck_graph').id,
            'target': 'current',
            'domain': [('game_deck_id', '=', self.id)],
        }

