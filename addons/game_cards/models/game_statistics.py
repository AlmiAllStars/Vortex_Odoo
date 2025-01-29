# Archivo: models/game_statistics.py
from odoo import models, fields, api

class GameStatistics(models.Model):
    _name = 'game.statistics'
    _description = 'Game Statistics'

    user_id = fields.Many2one('game.user', string='Player', required=True, ondelete='cascade')  # Relación con el usuario
    games_played = fields.Integer(string='Games Played', default=0)
    games_won = fields.Integer(string='Games Won', default=0)
    games_lost = fields.Integer(string='Games Lost', default=0)
    ranking = fields.Integer(string='Global Ranking', default=0)
    win_rate = fields.Float(string='Win Rate', compute='_compute_win_rate', store=True)

    @api.depends('games_played', 'games_won')
    def _compute_win_rate(self):
        for stats in self:
            stats.win_rate = (stats.games_won / stats.games_played * 100) if stats.games_played > 0 else 0
