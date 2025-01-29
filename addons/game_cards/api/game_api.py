from odoo import http
from odoo.http import request
import random
import json

class GameApi(http.Controller):

    @http.route('/api/users', type='json', auth='public', methods=['POST'], csrf=False)
    def create_user(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['name', 'email', 'password']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            # Comprobar si el usuario ya existe
            existing_user = request.env['res.users'].sudo().search([('login', '=', data['email'])], limit=1)
            if existing_user:
                return {'error': f"User with email {data['email']} already exists."}

            # Crear el usuario
            user = request.env['game.user'].sudo().create({
                'name': data['name'],
                'email': data['email'],
                'res_user_id': request.env['res.users'].sudo().create({
                    'name': data['name'],
                    'login': data['email'],
                    'password': data['password']
                }).id
            })

            # La colección se deja vacía inicialmente
            return {'success': True, 'user_id': user.id}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/users/add_cards', type='json', auth='public', methods=['POST'], csrf=False)
    def add_cards_to_collection(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['user_id', 'cards']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            user = request.env['game.user'].sudo().browse(data['user_id'])
            if not user.exists():
                return {'error': f"User with ID {data['user_id']} not found."}

            for card_info in data['cards']:
                card_id = card_info.get('card_id')
                quantity = card_info.get('quantity', 1)

                if not card_id or quantity < 1:
                    continue  # Ignorar entradas inválidas

                card = request.env['game.card'].sudo().browse(card_id)
                if not card.exists():
                    continue  # Ignorar cartas inválidas

                collection_entry = request.env['game.collection'].sudo().search([
                    ('user_id', '=', user.id),
                    ('card_id', '=', card.id)
                ], limit=1)

                if collection_entry:
                    collection_entry.sudo().write({'quantity': collection_entry.quantity + quantity})
                else:
                    request.env['game.collection'].sudo().create({
                        'user_id': user.id,
                        'card_id': card.id,
                        'quantity': quantity
                    })

            return {'success': True, 'message': 'Cards added successfully'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/users/disenchant', type='json', auth='public', methods=['POST'], csrf=False)
    def disenchant_card(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['user_id', 'card_id']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            user = request.env['game.user'].sudo().browse(data['user_id'])
            if not user.exists():
                return {'error': f"User with ID {data['user_id']} not found."}

            card = request.env['game.card'].sudo().browse(data['card_id'])
            if not card.exists():
                return {'error': f"Card with ID {data['card_id']} not found."}

            collection_entry = request.env['game.collection'].sudo().search([
                ('user_id', '=', user.id),
                ('card_id', '=', card.id)
            ], limit=1)

            if not collection_entry or collection_entry.quantity < 1:
                return {'error': 'User does not own this card or has no copies left to disenchant.'}

            # Polvo arcano ganado según rareza
            dust_values = {
                'common': 20,
                'rare': 40,
                'epic': 200,
                'legendary': 400
            }
            dust_reward = dust_values.get(card.rarity, 0)

            if dust_reward == 0:
                return {'error': f"Invalid card rarity {card.rarity} for disenchanting."}

            # Reducir la cantidad de la carta en la colección
            if collection_entry.quantity > 1:
                collection_entry.sudo().write({'quantity': collection_entry.quantity - 1})
            else:
                collection_entry.sudo().unlink()  # Eliminar la entrada si solo quedaba una copia

            # Añadir polvo arcano al usuario
            user.sudo().write({'currency_dust': user.currency_dust + dust_reward})

            return {
                'success': True,
                'dust_gained': dust_reward,
                'new_dust_total': user.currency_dust
            }

        except Exception as e:
            return {'error': str(e)}

    
    @http.route('/api/users/open_pack', type='json', auth='public', methods=['POST'], csrf=False)
    def open_pack(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['user_id', 'payment_method']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            user = request.env['game.user'].sudo().browse(data['user_id'])
            if not user.exists():
                return {'error': f"User with ID {data['user_id']} not found."}

            # Costes del sobre
            gold_cost = 100
            dust_cost = 400

            # Verificar fondos del usuario
            if data['payment_method'] == 'gold':
                if user.currency_gold < gold_cost:
                    return {'error': 'Not enough gold to purchase the pack.'}
                user.sudo().write({'currency_gold': user.currency_gold - gold_cost})

            elif data['payment_method'] == 'dust':
                if user.currency_dust < dust_cost:
                    return {'error': 'Not enough arcane dust to purchase the pack.'}
                user.sudo().write({'currency_dust': user.currency_dust - dust_cost})

            else:
                return {'error': 'Invalid payment method. Use "gold" or "dust".'}

            # Nuevas probabilidades sin "rare"
            rarity_chances = [
                [5, 10, 85],   # Cartas 1, 2 y 3 (Antes: 5-10-35-50 -> Ahora: 5-10-85)
                [10, 15, 75],  # Carta 4 (Antes: 10-15-40-35 -> Ahora: 10-15-75)
                [15, 25, 60]   # Carta 5 (Antes: 15-25-50-10 -> Ahora: 15-25-60)
            ]
            rarity_order = ['legendary', 'epic', 'common']  # Eliminamos "rare"

            # Obtener cartas por rareza en listas indexadas
            cards_by_rarity = {
                'common': list(request.env['game.card'].sudo().search([('rarity', '=', 'common')])),
                'epic': list(request.env['game.card'].sudo().search([('rarity', '=', 'epic')])),
                'legendary': list(request.env['game.card'].sudo().search([('rarity', '=', 'legendary')]))
            }

            # Verificar que haya cartas en cada rareza
            for rarity, card_list in cards_by_rarity.items():
                if not card_list:
                    return {'error': f'No available cards found for rarity: {rarity}.'}

            def get_random_card(probabilities):
                """Selecciona una carta generando un índice aleatorio dentro de la rareza elegida."""
                rarity = random.choices(rarity_order, probabilities, k=1)[0]
                card_list = cards_by_rarity[rarity]
                index = random.randint(0, len(card_list) - 1)  # Selección equitativa por índice
                return card_list[index]

            # Generar las 5 cartas del sobre respetando las nuevas probabilidades de rareza
            selected_cards = [
                get_random_card(rarity_chances[0]),
                get_random_card(rarity_chances[0]),
                get_random_card(rarity_chances[0]),
                get_random_card(rarity_chances[1]),
                get_random_card(rarity_chances[2])
            ]

            # Asignar cartas al usuario
            for card in selected_cards:
                if card:
                    collection_entry = request.env['game.collection'].sudo().search([
                        ('user_id', '=', user.id),
                        ('card_id', '=', card.id)
                    ], limit=1)

                    if collection_entry:
                        collection_entry.sudo().write({'quantity': collection_entry.quantity + 1})
                    else:
                        request.env['game.collection'].sudo().create({
                            'user_id': user.id,
                            'card_id': card.id,
                            'quantity': 1
                        })

            return {
                'success': True,
                'cards_obtained': [{'id': card.id, 'name': card.name, 'rarity': card.rarity} for card in selected_cards],
                'new_gold_total': user.currency_gold,
                'new_dust_total': user.currency_dust
            }

        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/users/<int:user_id>/cards', type='http', auth='public', methods=['GET'], csrf=False)
    def get_user_cards(self, user_id):
        try:
            user = request.env['game.user'].sudo().browse(user_id)
            if not user.exists():
                return http.Response(json.dumps({'error': f"User with ID {user_id} not found."}),
                                     content_type='application/json', status=404)

            # Obtener las cartas del usuario desde game_collection
            user_cards = request.env['game.collection'].sudo().search([('user_id', '=', user_id)])

            # Formatear los datos de las cartas
            cards_data = [{
                'id': card.card_id.id,
                'name': card.card_id.name,
                'rarity': card.card_id.rarity,
                'type': card.card_id.type,
                'quantity': card.quantity
            } for card in user_cards]

            response_data = json.dumps({'success': True, 'cards': cards_data})
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(json.dumps({'error': str(e)}),
                                 content_type='application/json', status=500)