from odoo import models, fields, api

class GameUser(models.Model):
    _name = 'game.user'
    _description = 'Game User'

    name = fields.Char(string='Username', required=True)
    email = fields.Char(string='Email', required=True)
    res_user_id = fields.Many2one('res.users', string='Linked Odoo User')  # Relación con res.users
    collection_ids = fields.One2many('game.collection', 'user_id', string='Collection')
    deck_ids = fields.One2many('game.deck', 'user_id', string='Decks')
    currency_gold = fields.Integer(string='Gold', default=0)
    currency_dust = fields.Integer(string='Arcane Dust', default=0)
    statistics_id = fields.Many2one('game.statistics', string='Statistics')

