from odoo import models, fields, api

class GameStatistics(models.Model):
    _name = 'game.statistics'
    _description = 'Game Statistics'

    user_id = fields.Many2one('game.user', string='Player', required=True, ondelete='cascade')
    games_played = fields.Integer(string='Games Played', compute='_compute_games_played', store=True)
    games_won = fields.Integer(string='Games Won', default=0)
    games_lost = fields.Integer(string='Games Lost', default=0)
    ranking = fields.Integer(string='Global Ranking', compute='_compute_ranking', store=True)
    win_rate = fields.Float(string='Win Rate', compute='_compute_win_rate', store=True)

    @api.depends('games_won', 'games_lost')
    def _compute_games_played(self):
        for stats in self:
            stats.games_played = stats.games_won + stats.games_lost

    @api.depends('games_played', 'games_won')
    def _compute_win_rate(self):
        for stats in self:
            stats.win_rate = (stats.games_won / stats.games_played * 100) if stats.games_played > 0 else 0

    @api.depends('games_won', 'games_lost')
    def _compute_ranking(self):
        all_stats = self.search([])  # Obtener todas las estadísticas de jugadores
        rankings = sorted(all_stats, key=lambda s: s.games_won - s.games_lost, reverse=True)

        for index, stats in enumerate(rankings, start=1):
            stats.ranking = index
