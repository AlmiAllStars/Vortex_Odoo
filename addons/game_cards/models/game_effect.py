# Archivo: models/game_effect.py
from odoo import models, fields, api

class GameEffect(models.Model):
    _name = 'game.effect'
    _description = 'Game Effect'

    name = fields.Char(string='Effect Name', required=True)
    effect_code = fields.Char(string='Effect Code', required=True)  # Código técnico para Unity
    description = fields.Text(string='Description')  # Explicación legible para humanos
