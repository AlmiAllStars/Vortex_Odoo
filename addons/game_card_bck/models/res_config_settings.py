from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_game_cards = fields.Boolean(string='Enable Game Cards Module')