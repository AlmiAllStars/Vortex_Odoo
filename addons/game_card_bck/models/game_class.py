# Archivo: models/game_class.py
from odoo import models, fields, api

class GameClass(models.Model):
    _name = 'game.class'
    _description = 'Game Class'

    name = fields.Char(string='Class Name', required=True)
    description = fields.Text(string='Description')
    icon = fields.Binary(string='Class Icon')  # Para una imagen representativa
