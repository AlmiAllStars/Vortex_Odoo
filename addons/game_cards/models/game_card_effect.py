# Archivo: models/game_card_effect.py
from odoo import models, fields, api

class GameCardEffect(models.Model):
    _name = 'game.card.effect'
    _description = 'Card Effect'

    card_id = fields.Many2one('game.card', string='Card', required=True, ondelete='cascade')  # Relación con la carta
    effect_id = fields.Many2one('game.effect', string='Effect', required=True)  # Relación con el efecto
    effect_value = fields.Integer(string='Effect Value', default=0)  # Valor asociado al efecto (opcional)
