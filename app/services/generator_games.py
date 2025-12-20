import random
from typing import List, Dict

class GameGenerator:
    """Генератор игр"""

    GAME_NAMES = [
        "Cyberpunk Adventure", "Space Odyssey", "Dragon's Legacy", "Shadow Warriors",
        "Kingdom of Legends", "Future Combat", "Wild West Saga", "Ocean Explorer",
        "Mystic Forest", "Desert Storm", "Arctic Survival", "Volcano Escape",
        "Space Station Alpha", "Medieval Conquest", "Samurai's Honor", "Viking Raid",
        "Zombie Apocalypse", "Ghost Hunter", "Alien Invasion", "Robot Revolution",
        "Pirate's Treasure", "Ninja Assassin", "Superhero City", "Fantasy Quest",
        "Racing Extreme", "Football Champions", "Basketball Stars", "Tennis Masters",
        "Boxing King", "Golf Paradise", "Ski Adventure", "Snowboard Extreme",
        "Surfing Waves", "Skateboard Park", "Cycling Challenge", "Hiking Journey"
    ]

    PUBLISHERS = [
        "Electronic Arts", "Ubisoft", "Activision", "Rockstar Games", "Valve",
        "CD Projekt Red", "Bethesda", "Square Enix", "Sega", "Capcom",
        "Bandai Namco", "Konami", "2K Games", "Warner Bros", "Microsoft",
        "Sony Interactive", "Nintendo", "Epic Games", "Blizzard", "Riot Games",
        "Paradox Interactive", "Focus Home", "Deep Silver", "THQ Nordic",
        "Devolver Digital", "Team17", "Curve Digital", "505 Games"
    ]

    # РАНДОМ цены в валютах
    PRICE_TIERS = {
        "RUB": [199, 299, 399, 499, 599, 799, 999, 1299, 1599, 1999, 2499, 2999],
        "USD": [2.99, 4.99, 9.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99, 59.99],
        "EUR": [2.49, 4.49, 9.49, 14.49, 19.49, 24.49, 29.49, 39.49, 49.49, 59.49]
    }

    # Изображения-заглушки
    IMAGES = [
        "https://cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/570/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/550/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/620/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/10/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/70/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/80/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/240/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/320/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/340/header.jpg",
        "https://cdn.cloudflare.steamstatic.com/steam/apps/400/header.jpg"
    ]

    @staticmethod
    def generate_game(game_id: int = None, currency: str = "RUB") -> Dict:
        """Генерация одной случайной игры"""
        if game_id is None:
            game_id = random.randint(1000, 9999)

        name = random.choice(GameGenerator.GAME_NAMES)
        publisher = random.choice(GameGenerator.PUBLISHERS)
        image = random.choice(GameGenerator.IMAGES)

        # Генерирует цену со случайной скидкой
        base_price = random.choice(GameGenerator.PRICE_TIERS[currency])

        # С вероятностью 15% делает скидку
        if random.random() < 0.15:
            discount = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75])
            final_price = base_price * (100 - discount) / 100

            if currency == "RUB":
                price = f"<s>{base_price:.0f} руб.</s> {final_price:.0f} руб. (-{discount}%)"
            elif currency == "USD":
                price = f"<s>{base_price:.2f} USD</s> {final_price:.2f} USD (-{discount}%)"
            else:
                price = f"<s>{base_price:.2f} EUR</s> {final_price:.2f} EUR (-{discount}%)"
        else:
            if currency == "RUB":
                price = f"{base_price:.0f} руб."
            elif currency == "USD":
                price = f"{base_price:.2f} USD"
            else:
                price = f"{base_price:.2f} EUR"

        if random.random() < 0.05:
            price = "Бесплатно"

        return {
            "appid": game_id,
            "name": name,
            "publisher": publisher,
            "price": price,
            "image": image,
            "type": "game",
            "currency": currency,
            "generated": True  # Флаг, что игра сгенерирована
        }

    @staticmethod
    def generate_games(count: int = 12, currency: str = "RUB") -> List[Dict]:
        """Генерация списка игр"""
        games = []
        for i in range(count):
            game = GameGenerator.generate_game(10000 + i, currency)
            games.append(game)

        return games

    @staticmethod
    def get_featured_games(count: int = 24, currency: str = "RUB") -> List[Dict]:
        """Получение популярных игр (но через генератор, а не через steam)"""
        games = []

        for i in range(count):
            game_id = 30000 + i
            name = random.choice(GameGenerator.GAME_NAMES)
            publisher = random.choice(GameGenerator.PUBLISHERS)
            image = random.choice(GameGenerator.IMAGES)
            high_tier = GameGenerator.PRICE_TIERS[currency][-5:]
            base_price = random.choice(high_tier)

            if currency == "RUB":
                price = f"{base_price:.0f} руб."
            elif currency == "USD":
                price = f"{base_price:.2f} USD"
            else:
                price = f"{base_price:.2f} EUR"

            games.append({
                "appid": game_id,
                "name": f"{name} - Special Edition",
                "publisher": publisher,
                "price": price,
                "image": image,
                "type": "game",
                "currency": currency,
                "featured": True,
                "generated": True
            })

        return games
