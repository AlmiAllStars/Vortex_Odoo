from odoo import models, fields, api

class GameCard(models.Model):
    _name = 'game.card'
    _description = 'Game Card'

    name = fields.Char(string='Card Name', required=True)
    description = fields.Text(string='Description')
    mana_class = fields.Integer(string='Class Mana Cost', default=0)
    mana_colorless = fields.Integer(string='Colorless Mana Cost', default=0)
    attack = fields.Integer(string='Attack', default=0)
    defense = fields.Integer(string='Defense', default=0)
    rarity = fields.Selection([
        ('common', 'Common'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary')
    ], string='Rarity', default='common')
    type = fields.Selection([
        ('creature', 'Creature'),
        ('spell', 'Spell'),
        ('artifact', 'Artifact')
    ], string='Type', default='creature')
    class_restriction = fields.Many2one('game.class', string='Class Restriction')
    image = fields.Binary(string='Card Image')
    card_effects = fields.One2many('game.card.effect', 'card_id', string='Card Effects')
    expansion_id = fields.Many2one('game.expansion', string='Expansion')