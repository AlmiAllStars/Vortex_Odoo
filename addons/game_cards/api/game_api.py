from odoo import http
from odoo.http import request
import requests
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

            # Ordenar las cartas por el campo relacionado game_card.id
            sorted_user_cards = sorted(user_cards, key=lambda card: card.card_id.id)

            # Formatear los datos de las cartas
            cards_data = [{
                'id': card.card_id.id,
                'name': card.card_id.name,
                'rarity': card.card_id.rarity,
                'type': card.card_id.type,
                'quantity': card.quantity
            } for card in sorted_user_cards]

            response_data = json.dumps({'success': True, 'cards': cards_data})
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(json.dumps({'error': str(e)}),
                                content_type='application/json', status=500)




    @http.route('/api/users/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_user(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['user_id', 'updates']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            user = request.env['game.user'].sudo().browse(data['user_id'])
            if not user.exists():
                return {'error': f"User with ID {data['user_id']} not found."}

            updates = data['updates']
            valid_user_fields = ['currency_gold', 'currency_dust']
            valid_stats_fields = ['games_played', 'games_won', 'games_lost', 'ranking', 'win_rate']

            updated_fields = {}

            # Actualizar campos en game.user (currency_gold, currency_dust)
            user_updates = {key: value for key, value in updates.items() if key in valid_user_fields}
            if user_updates:
                for field, value in user_updates.items():
                    if isinstance(value, str) and (value.startswith('+') or value.startswith('-')):
                        increment = int(value)
                        current_value = getattr(user, field, 0)
                        user_updates[field] = current_value + increment
                    elif isinstance(value, int):
                        user_updates[field] = value
                    else:
                        return {'error': f"Invalid value for field {field}: {value}"}
                user.sudo().write(user_updates)
                updated_fields.update(user_updates)

            # Actualizar o crear campos en game.statistics (games_won, games_lost, etc.)
            stats_updates = {key: value for key, value in updates.items() if key in valid_stats_fields}
            if stats_updates:
                stats = request.env['game.statistics'].sudo().search([('user_id', '=', user.id)], limit=1)
                if not stats:
                    # Crear un registro de estadísticas si no existe
                    stats = request.env['game.statistics'].sudo().create({
                        'user_id': user.id,
                        'games_played': 0,
                        'games_won': 0,
                        'games_lost': 0,
                        'ranking': 0,
                        'win_rate': 0
                    })

                for field, value in stats_updates.items():
                    if isinstance(value, str) and (value.startswith('+') or value.startswith('-')):
                        increment = int(value)
                        current_value = getattr(stats, field, 0)
                        stats_updates[field] = current_value + increment
                    elif isinstance(value, int):
                        stats_updates[field] = value
                    else:
                        return {'error': f"Invalid value for field {field}: {value}"}
                stats.sudo().write(stats_updates)
                updated_fields.update(stats_updates)

            return {
                "success": True,
                "updated_fields": updated_fields
            }

        except Exception as e:
            return {"error": str(e)}

    @http.route('/api/users/<int:user_id>/decks', type='http', auth='public', methods=['GET'], csrf=False)
    def get_user_decks(self, user_id):
        try:
            user = request.env['game.user'].sudo().browse(user_id)
            if not user.exists():
                return http.Response(json.dumps({'error': f"User with ID {user_id} not found."}),
                                    content_type='application/json', status=404)

            # Obtener los decks del usuario desde game_deck
            user_decks = request.env['game.deck'].sudo().search([('user_id', '=', user_id)])

            # Formatear los datos de los decks
            decks_data = [{
                'id': deck.id,
                'name': deck.name,
                'class': deck.class_id.name if deck.class_id else None,
                'total_mana': deck.total_mana,
            } for deck in user_decks]

            response_data = json.dumps({'success': True, 'decks': decks_data})
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(json.dumps({'error': str(e)}),
                                content_type='application/json', status=500)

    @http.route('/api/users/<int:user_id>/info', type='http', auth='public', methods=['GET'], csrf=False)
    def get_user_info(self, user_id):
        try:
            # Buscar al usuario en la base de datos
            user = request.env['game.user'].sudo().browse(user_id)
            if not user.exists():
                return http.Response(json.dumps({'error': f"User with ID {user_id} not found."}),
                                     content_type='application/json', status=404)

            # Formatear los datos del usuario
            user_info = {
                'id': user.id,
                'name': user.name,
                'gold': user.currency_gold,
                'dust': user.currency_dust,
                'selected_deck': user.selected_deck if user.selected_deck else -1
            }

            response_data = json.dumps({'success': True, 'user_info': user_info})
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(json.dumps({'error': str(e)}),
                                 content_type='application/json', status=500)

    @http.route('/api/users/<int:user_id>/select-deck/<int:deck_option>', type='http', auth='public', methods=['POST'], csrf=False)
    def select_user_deck(self, user_id, deck_option):
        try:
            # Verificar que la opción sea válida (1-6)
            if str(deck_option) not in ['1', '2', '3', '4', '5', '6']:
                return http.Response(json.dumps({'error': 'Invalid deck option. Must be between 1 and 6.'}),
                                     content_type='application/json', status=400)

            # Buscar al usuario
            user = request.env['game.user'].sudo().browse(user_id)
            if not user.exists():
                return http.Response(json.dumps({'error': f"User with ID {user_id} not found."}),
                                     content_type='application/json', status=404)

            # Asignar el valor de selected_deck
            user.sudo().write({'selected_deck': str(deck_option)})

            response_data = json.dumps({'success': True, 'message': f"Deck {deck_option} selected for user {user.name}."})
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(json.dumps({'error': str(e)}),
                                 content_type='application/json', status=500)

    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def user_login(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['db', 'login', 'password']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            # Llamada a la API de autenticación de Odoo
            odoo_auth_url = "http://34.196.147.37:8069/web/session/authenticate"
            auth_payload = {
                "jsonrpc": "2.0",
                "params": {
                    "db": data['db'],
                    "login": data['login'],
                    "password": data['password']
                }
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(odoo_auth_url, json=auth_payload, headers=headers)

            # Verificar si la respuesta de Odoo es exitosa
            if response.status_code != 200:
                return {'error': 'Failed to authenticate with Odoo.'}

            auth_result = response.json()
            if 'result' not in auth_result or not auth_result['result'].get('uid'):
                return {'error': 'Invalid credentials or authentication failed.'}

            # Obtener el nombre del usuario autenticado
            user_name = auth_result['result']['name']

            # Buscar el usuario en game.user por nombre
            user = request.env['game.user'].sudo().search([('name', '=', user_name)], limit=1)
            if not user:
                return {'error': f"User with name {user_name} not found in local database."}

            return {'success': True, 'user_id': user.id}

        except Exception as e:
            return {'error': str(e)}


    @http.route('/api/users/<int:user_id>/create_deck', type='json', auth='public', methods=['POST'], csrf=False)
    def create_deck(self, user_id, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['name', 'class_id', 'cards']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            # Verificar que el usuario existe
            user = request.env['game.user'].sudo().browse(user_id)
            if not user.exists():
                return {'error': f"User with ID {user_id} not found."}

            # Verificar que las cartas no excedan el límite de 20 en total
            if len(data['cards']) > 20:
                return {'error': 'A deck cannot contain more than 20 cards in total.'}

            # Verificar que no haya más de 2 copias de una misma carta
            for card in data['cards']:
                if card.get('quantity', 1) > 3:
                    return {'error': f"Card ID {card['card_id']} exceeds the maximum quantity of 3 per deck."}

            # Verificar que todas las cartas sean válidas
            card_ids = [card['card_id'] for card in data['cards']]
            valid_cards = request.env['game.card'].sudo().search([('id', 'in', card_ids)])
            if len(valid_cards) != len(card_ids):
                return {'error': 'Some card IDs are invalid or do not exist.'}

            # Crear el deck
            deck = request.env['game.deck'].sudo().create({
                'user_id': user_id,
                'name': data['name'],
                'class_id': data['class_id'],
                'cards': [(6, 0, card_ids)]  # Usar la relación Many2many para asociar las cartas
            })

            return {'success': True, 'deck_id': deck.id, 'message': 'Deck created successfully.'}

        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/decks/<int:deck_id>/cards', type='http', auth='public', methods=['GET'], csrf=False)
    def get_deck_cards(self, deck_id):
        try:
            # Verificar que el mazo exista
            deck = request.env['game.deck'].sudo().browse(deck_id)
            if not deck.exists():
                return http.Response(
                    json.dumps({'error': f"Deck with ID {deck_id} not found."}),
                    content_type='application/json',
                    status=404
                )

            # Obtener las cartas y cantidades del mazo desde el modelo intermedio
            cards_data = [{
                'id': rel.game_card_id.id,
                'name': rel.game_card_id.name,
                'rarity': rel.game_card_id.rarity,
                'type': rel.game_card_id.type,
                'mana_class': rel.game_card_id.mana_class,
                'mana_colorless': rel.game_card_id.mana_colorless,
                'quantity': rel.quantity
            } for rel in deck.card_rel_ids]

            # Respuesta con las cartas del mazo
            response_data = json.dumps({
                'success': True,
                'deck_name': deck.name,
                'cards': cards_data
            })
            return http.Response(response_data, content_type='application/json', status=200)

        except Exception as e:
            return http.Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )
        
    @http.route('/api/decks/<int:deck_id>/edit', type='json', auth='public', methods=['POST'], csrf=False)
    def edit_deck(self, deck_id, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            required_fields = ['cards']
            missing = [field for field in required_fields if field not in data]
            if missing:
                return {'error': f"Missing fields: {', '.join(missing)}"}

            # Verificar que el mazo existe
            deck = request.env['game.deck'].sudo().browse(deck_id)
            if not deck.exists():
                return {'error': f"Deck with ID {deck_id} not found."}

            # Verificar que las cartas no excedan el límite de 20 en total
            if len(data['cards']) > 20:
                return {'error': 'A deck cannot contain more than 20 cards in total.'}

            # Verificar que no haya más de 3 copias de una misma carta
            for card in data['cards']:
                if card.get('quantity', 1) > 3:
                    return {'error': f"Card ID {card['card_id']} exceeds the maximum quantity of 3 per deck."}

            # Verificar que todas las cartas sean válidas
            card_ids = [card['card_id'] for card in data['cards']]
            valid_cards = request.env['game.card'].sudo().search([('id', 'in', card_ids)])
            if len(valid_cards) != len(card_ids):
                return {'error': 'Some card IDs are invalid or do not exist.'}

            # Limpiar las cartas actuales del mazo
            deck.card_rel_ids.unlink()

            # Agregar las nuevas cartas al mazo
            for card in data['cards']:
                request.env['game.card.deck.rel'].sudo().create({
                    'game_deck_id': deck_id,
                    'game_card_id': card['card_id'],
                    'quantity': card.get('quantity', 1)
                })

            return {'success': True, 'deck_id': deck.id, 'message': 'Deck updated successfully.'}

        except Exception as e:
            return {'error': str(e)}