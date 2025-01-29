# Archivo: models/game_expansion.py
from odoo import models, fields, api

class GameExpansion(models.Model):
    _name = 'game.expansion'
    _description = 'Game Expansion'

    name = fields.Char(string='Expansion Name', required=True)
    release_date = fields.Date(string='Release Date')
    description = fields.Text(string='Description')
