from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import json
from datetime import datetime
import time
from tabulate import tabulate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def format_price(price):
    """Форматирование цены"""
    if isinstance(price, (int, float)):
        return f"{price:,.0f} руб.".replace(",", " ")
    return str(price)

def parse_litres_books(response_data):
    """Парсинг книг с Litres"""
    books = []
    
    if 'payload' in response_data and 'data' in response_data['payload']:
        for book in response_data['payload']['data']:
            # Основная информация о книге
            title = book.get('title', 'Нет названия')
            authors = [person['full_name'] for person in book.get('persons', []) if person.get('role') == 'author']
            author_names = ", ".join(authors) if authors else "Автор не указан"
            price = book.get('prices', {}).get('final_price', 0)
            book_type = "Аудиокнига" if book.get('art_type') == 1 else "Книга"
            
            # Рейтинг
            rating_data = book.get('rating', {})
            rating = rating_data.get('rated_avg', 0)
            rating_count = rating_data.get('rated_total_count', 0)
            
            # Метки
            labels = book.get('labels', {})
            tags = []
            if labels.get('is_new'): tags.append("🆕")
            if labels.get('is_bestseller'): tags.append("🔥")
            if labels.get('is_litres_exclusive'): tags.append("⭐")
            
            books.append({
                'source': '📚 Litres',
                'title': title,
                'author': author_names,
                'type': book_type,
                'price': price,
                'rating': rating,
                'rating_count': rating_count,
                'tags': ' '.join(tags),
                'url': f"https://www.litres.ru{book.get('url', '')}",
                'id': book.get('id', '')
            })
    
    return books

def parse_chitai_gorod_books(response_data):
    """Парсинг книг с Читай-город"""
    books = []
    
    if 'data' in response_data:
        for item in response_data['data']:
            attributes = item.get('attributes', {})
            
            # Основная информация о книге
            title = attributes.get('title', 'Нет названия')
            
            # Авторы
            authors_data = attributes.get('authors', [])
            authors = []
            for author in authors_data:
                name_parts = []
                if author.get('firstName'): name_parts.append(author['firstName'])
                if author.get('lastName'): name_parts.append(author['lastName'])
                if name_parts:
                    authors.append(' '.join(name_parts))
            author_names = ", ".join(authors) if authors else "Автор не указан"
            
            # Цены
            old_price = attributes.get('oldPrice', 0)
            price = attributes.get('price', 0)
            discount = attributes.get('discount', '0')
            
            # Рейтинг
            rating_data = attributes.get('rating', {})
            rating = float(rating_data.get('count', 0)) if rating_data.get('count') else 0
            rating_count = rating_data.get('votes', 0)
            
            # Метки
            tags = []
            if attributes.get('bestseller'): tags.append("🔥")
            if attributes.get('new'): tags.append("🆕")
            if attributes.get('recommended'): tags.append("👍")
            if discount and discount != '0': tags.append(f"-{discount}%")
            
            books.append({
                'source': '🏪 Читай-город',
                'title': title,
                'author': author_names,
                'type': 'Книга',
                'price': price,
                'old_price': old_price,
                'rating': rating,
                'rating_count': rating_count,
                'tags': ' '.join(tags),
                'url': f"https://www.chitai-gorod.ru{attributes.get('url', '')}",
                'id': attributes.get('id', '')
            })
    
    return books

def print_books_table(books, source_name):
    """Вывод книг в виде таблицы"""
    if not books:
        print(f"\n📭 В {source_name} не найдено книг")
        return
    
    print(f"\n{'='*80}")
    print(f"📖 {source_name} - НАЙДЕНО КНИГ: {len(books)}")
    print(f"{'='*80}")
    
    # Подготовка данных для таблицы
    table_data = []
    for i, book in enumerate(books, 1):
        #цена
        price_str = format_price(book['price'])
        if book.get('old_price') and book['old_price'] > book['price']:
            price_str = f"{format_price(book['old_price'])} → {price_str}"
        
        #рейтинг
        rating_str = ""
        if book['rating'] > 0:
            rating_str = f"{book['rating']:.1f} ⭐ ({book['rating_count']})"
        
        table_data.append([
            i,
            book['source'],
            book['title'][:50] + "..." if len(book['title']) > 50 else book['title'],
            book['author'][:30] + "..." if len(book['author']) > 30 else book['author'],
            book['type'],
            price_str,
            rating_str,
            book['tags']
        ])
    
    # Вывод в консоль
    headers = ["№", "Источник", "Название", "Автор", "Тип", "Цена", "Рейтинг", "Метки"]
    print(tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[4, 8, 25, 20, 8, 15, 15, 10]))
    
    total_price = sum(book['price'] for book in books if isinstance(book['price'], (int, float)))
    avg_rating = sum(book['rating'] for book in books if book['rating'] > 0) / len([b for b in books if b['rating'] > 0]) if any(b['rating'] > 0 for b in books) else 0
    
    print(f"\n• Статистика {source_name}:")
    print(f"   • Средняя цена: {format_price(total_price / len(books))}")
    print(f"   • Средний рейтинг: {avg_rating:.2f} ⭐")
    print(f"   • Всего оценок: {sum(book['rating_count'] for book in books)}")

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@router.post("/search", response_class=HTMLResponse)
async def search_products(request: Request):
    all_books = []
    
    try:
        print("Парсинг LITRES")
        
        cookies_litres = {
            '__ddg1_': 'TXnS03cZihP1eOR04ij3',
            'advcake_session_id': '362b82d2-f8c3-0c45-84f6-e36c8e27beec',
            'advcake_utm_webmaster': '17341477619',
            'advcake_click_id': '',
            '_gcl_au': '1.1.832687977.1760278576',
            'advcake_utm_partner': 'mixed_brand_search%2B559380598%257Cspecial%257C45195153',
            '_ym_uid': '1760278606625637029',
            '_ym_d': '1760278606',
            'adrcid': 'AQhaRjDJkVGR-FW2TelMNyA',
            'acs_3': '%7B%22hash%22%3A%221aa3f9523ee6c2690cb34fc702d4143056487c0d%22%2C%22nst%22%3A1760365006348%2C%22sl%22%3A%7B%22224%22%3A1760278606348%2C%221228%22%3A1760278606348%7D%7D',
            'tmr_lvid': 'e4ef598a70e7a94b25330b5a89f0cbce',
            'tmr_lvidTS': '1760278607091',
            'uxs_uid': '166d5990-a776-11f0-89e5-e968a94fbe9b',
            'mindboxDeviceUUID': '0887677e-ff39-43ac-ab97-93a8f8b985b8',
            'directCrm-session': '%7B%22deviceGuid%22%3A%220887677e-ff39-43ac-ab97-93a8f8b985b8%22%7D',
            'advcake_track_id': 'b29d798f-a42d-a2ed-eab2-861dc1a11741',
            'tj4rxr_track_id': 'b29d798f-a42d-a2ed-eab2-861dc1a11741',
            'advcake_track_url': 'https%3A%2F%2Fwww.litres.ru%2Fcollections%2Ftop-50-knig-v-litres%2F%3Futm_medium%3Dcpc%26utm_source%3Dyandex%26utm_campaign%3Dmixed_brand_search%2B559380598%257Cspecial%257C45195153%26utm_term%3D---autotargeting%257C52811194682%26utm_content%3D17341477619%26yclid%3D142926222998896639%26lfrom_processed%3D559380598%26genre_id%3D5004',
            'tj4rxr_track_url': 'https%3A%2F%2Fwww.litres.ru%2Fcollections%2Ftop-50-knig-v-litres%2F%3Futm_medium%3Dcpc%26utm_source%3Dyandex%26utm_campaign%3Dmixed_brand_search%2B559380598%257Cspecial%257C45195153%26utm_term%3D---autotargeting%257C52811194682%26utm_content%3D17341477619%26yclid%3D142926222998896639%26lfrom_processed%3D559380598%26genre_id%3D5004',
            'adrdel': '1760351421737',
            '_ym_isad': '2',
            '__ddg9_': '90.154.74.104',
            '__ddg10_': '1760356463',
            '__ddg8_': 'm0yQkEK6c9pKhoWP',
        }

        headers_litres = {
            'authority': 'api.litres.ru',
            'ab-tests-flags': '[{"v":"true","t":"flag","n":"paper_lk_web_pda"},{"v":"false","t":"flag","n":"acqn_l_reactivation"},{"v":"true","t":"flag","n":"all_new"},{"v":"true","t":"flag","n":"audio_web_2321"},{"v":"false","t":"flag","n":"progressive_discount"},{"v":"false","t":"flag","n":"all_arts_series"}]',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru,en;q=0.9',
            'accept-version': '2',
            'app-id': '115',
            'baggage': 'sentry-environment=prod,sentry-release=6.845.234,sentry-public_key=66365c10274f4724819f92df56571b8b,sentry-trace_id=2d85d2a7b1a943ecbedbc417fb35bc9f,sentry-sample_rate=0.4,sentry-transaction=%2F,sentry-sampled=false',
            'client-host': 'www.litres.ru',
            # 'cookie': '__ddg1_=TXnS03cZihP1eOR04ij3; advcake_session_id=362b82d2-f8c3-0c45-84f6-e36c8e27beec; advcake_utm_webmaster=17341477619; advcake_click_id=; _gcl_au=1.1.832687977.1760278576; advcake_utm_partner=mixed_brand_search%2B559380598%257Cspecial%257C45195153; _ym_uid=1760278606625637029; _ym_d=1760278606; adrcid=AQhaRjDJkVGR-FW2TelMNyA; acs_3=%7B%22hash%22%3A%221aa3f9523ee6c2690cb34fc702d4143056487c0d%22%2C%22nst%22%3A1760365006348%2C%22sl%22%3A%7B%22224%22%3A1760278606348%2C%221228%22%3A1760278606348%7D%7D; tmr_lvid=e4ef598a70e7a94b25330b5a89f0cbce; tmr_lvidTS=1760278607091; uxs_uid=166d5990-a776-11f0-89e5-e968a94fbe9b; mindboxDeviceUUID=0887677e-ff39-43ac-ab97-93a8f8b985b8; directCrm-session=%7B%22deviceGuid%22%3A%220887677e-ff39-43ac-ab97-93a8f8b985b8%22%7D; advcake_track_id=b29d798f-a42d-a2ed-eab2-861dc1a11741; tj4rxr_track_id=b29d798f-a42d-a2ed-eab2-861dc1a11741; advcake_track_url=https%3A%2F%2Fwww.litres.ru%2Fcollections%2Ftop-50-knig-v-litres%2F%3Futm_medium%3Dcpc%26utm_source%3Dyandex%26utm_campaign%3Dmixed_brand_search%2B559380598%257Cspecial%257C45195153%26utm_term%3D---autotargeting%257C52811194682%26utm_content%3D17341477619%26yclid%3D142926222998896639%26lfrom_processed%3D559380598%26genre_id%3D5004; tj4rxr_track_url=https%3A%2F%2Fwww.litres.ru%2Fcollections%2Ftop-50-knig-v-litres%2F%3Futm_medium%3Dcpc%26utm_source%3Dyandex%26utm_campaign%3Dmixed_brand_search%2B559380598%257Cspecial%257C45195153%26utm_term%3D---autotargeting%257C52811194682%26utm_content%3D17341477619%26yclid%3D142926222998896639%26lfrom_processed%3D559380598%26genre_id%3D5004; adrdel=1760351421737; _ym_isad=2; __ddg9_=90.154.74.104; __ddg10_=1760356463; __ddg8_=m0yQkEK6c9pKhoWP',
            'origin': 'https://www.litres.ru',
            'referer': 'https://www.litres.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sentry-trace': '2d85d2a7b1a943ecbedbc417fb35bc9f-b74a923bc90f1929-0',
            'session-id': '6h2b895eec2abx4kbq6c85555ldyd8fn',
            'ui-currency': 'RUB',
            'ui-language-code': 'ru',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 YaBrowser/23.1.2.1028 Yowser/2.5 Safari/537.36',
            'x-request-id': '77b21d8a5944aaad1e9aa4e402328acb',
        }

        params_litres = {
            'collection_id': '26905',
            'only_safe_content': 'true',
            'limit': '20',
        }
        
        response_litres = requests.get(
            'https://api.litres.ru/foundation/api/homepage/arts', 
            params=params_litres, 
            cookies=cookies_litres, 
            headers=headers_litres,
            timeout=10
        )

        if response_litres.status_code == 200:
            data_litres = response_litres.json()
            litres_books = parse_litres_books(data_litres)
            all_books.extend(litres_books)
            print_books_table(litres_books, "LITRES")
        else:
            print(f"Ошибка Litres: {response_litres.status_code}")
            
        # === ПАРСИНГ ЧИТАЙ-ГОРОД ===
        print("Парсинг ЧИТАЙ-ГОРОД")
        
        cookies_chitai = {
            '__ddg9_': '90.154.74.104',
            '__ddg1_': 'Qdurlmzv1bYRLVJtIi4C',
            'access-token': 'Bearer%20eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjA1MjM3NjksImlhdCI6MTc2MDM1NTc2OSwiaXNzIjoiL2FwaS92MS9hdXRoL2Fub255bW91cyIsInN1YiI6IjM4ODczZTg1NmJlNjkxZjI0MWE4ZTJhOTNhMzQ5OGUzNGM0OTA2NTJlNTBhMzMzNzhmMWJmM2U4Y2U2ZjlmYmUiLCJ0eXBlIjoxMH0.n5lvPwEvxEQkGgHWTnTUTIwd-lTAAH8ZO9IIUkVwwC0',
            '_ymab_param': 'MXs8OZieKHle9LFkRz3YXv437nD6cFY491X90q2-VlnNLmXBYRYD89Dz7VE6GvOOvpF4TUPrQ-kQETlHwtSTs1UEKSI',
            'tid-back-to': '%7B%22fullPath%22%3A%22%2F%3Fysclid%3Dmgp2cgiywq999178911%22%2C%22hash%22%3A%22%22%2C%22query%22%3A%7B%22ysclid%22%3A%22mgp2cgiywq999178911%22%7D%2C%22name%22%3A%22index%22%2C%22path%22%3A%22%2F%22%2C%22params%22%3A%7B%7D%2C%22meta%22%3A%7B%7D%7D',
            'utm_custom_source': 'default',
            '_ym_uid': '1760355724400822782',
            '_ym_d': '1760355724',
            '_ym_isad': '2',
            'tid-state': 'f52441b8-4285-41c4-95af-45ae3d4aa7a0',
            'tid-redirect-uri': 'https%3A%2F%2Fwww.chitai-gorod.ru%2Fauth%2Ft-id-next',
            '_ym_visorc': 'w',
            'chg_visitor_id': '583801ad-b3f0-4feb-a1f8-6970b170087a',
            'tmr_lvid': '02a4fbc6722d3f3a5090953db0a7a5d9',
            'tmr_lvidTS': '1760355725781',
            'gdeslon.ru.__arc_domain': 'gdeslon.ru',
            'gdeslon.ru.user_id': '19bb2d6e-aec5-4948-b692-4ec02a9125f8',
            '__P__wuid': 'f7529d18f7efd1815c1acf8374d9a5fd',
            'stDeIdU': 'f7529d18f7efd1815c1acf8374d9a5fd',
            'vIdUid': '1d404b2f-d0c1-47f1-94a4-a2897530d9b3',
            'stLaEvTi': '1760355726294',
            'stSeStTi': '1760355726293',
            'popmechanic_sbjs_migrations': 'popmechanic_1418474375998%3D1%7C%7C%7C1471519752600%3D1%7C%7C%7C1471519752605%3D1',
            'analytic_id': '1760355726968954',
            'adrdel': '1760355727026',
            'adrcid': 'AmHcQafYSaO0mW66BflyQww',
            'acs_3': '%7B%22hash%22%3A%221aa3f9523ee6c2690cb34fc702d4143056487c0d%22%2C%22nst%22%3A1760442127204%2C%22sl%22%3A%7B%22224%22%3A1760355727204%2C%221228%22%3A1760355727204%7D%7D',
            'mindboxDeviceUUID': 'f70738bc-60ff-4d06-b58a-ec7900465f7a',
            'directCrm-session': '%7B%22deviceGuid%22%3A%22f70738bc-60ff-4d06-b58a-ec7900465f7a%22%7D',
            '__ddg8_': 'uhmuRCistRmbMUgV',
            '__ddg10_': '1760355879',
        }

        headers_chitai = {
            'authority': 'web-agr.chitai-gorod.ru',
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjA1MjM3NjksImlhdCI6MTc2MDM1NTc2OSwiaXNzIjoiL2FwaS92MS9hdXRoL2Fub255bW91cyIsInN1YiI6IjM4ODczZTg1NmJlNjkxZjI0MWE4ZTJhOTNhMzQ5OGUzNGM0OTA2NTJlNTBhMzMzNzhmMWJmM2U4Y2U2ZjlmYmUiLCJ0eXBlIjoxMH0.n5lvPwEvxEQkGgHWTnTUTIwd-lTAAH8ZO9IIUkVwwC0',
            'origin': 'https://www.chitai-gorod.ru',
            'referer': 'https://www.chitai-gorod.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 YaBrowser/23.1.2.1028 Yowser/2.5 Safari/537.36',
            'x-forwarded-for': '',
        }

        params_chitai = {
            'filters[tags]': '31',
            'filters[onlyAvailableForSale]': '1',
            'filters[onlyWithImage]': '1',
            'topCount': '200',
            'resultCount': '24',
            'include': 'productTexts,publisher,publisherBrand,publisherSeries,dates,literatureWorkCycle,rating',
        }
        
        response_chitai = requests.get(
            'https://web-agr.chitai-gorod.ru/web/api/v2/products-top',
            params=params_chitai,
            cookies=cookies_chitai,
            headers=headers_chitai,
            timeout=10
        )

        if response_chitai.status_code == 200:
            data_chitai = response_chitai.json()
            chitai_books = parse_chitai_gorod_books(data_chitai)
            all_books.extend(chitai_books)
            print_books_table(chitai_books, "ЧИТАЙ-ГОРОД")
        else:
            print(f"Ошибка Читай-город: {response_chitai.status_code}")

        # === ОБЩАЯ СТАТИСТИКА ===
        if all_books:
            print("ОБЩАЯ СТАТИСТИКА ПО ВСЕМ МАГАЗИНАМ")
            
            total_books = len(all_books)
            litres_count = len([b for b in all_books if b['source'] == '📚 Litres'])
            chitai_count = len([b for b in all_books if b['source'] == '🏪 Читай-город'])
            
            total_price = sum(book['price'] for book in all_books if isinstance(book['price'], (int, float)))
            avg_price = total_price / total_books if total_books > 0 else 0
            
            books_with_rating = [b for b in all_books if b['rating'] > 0]
            avg_rating = sum(b['rating'] for b in books_with_rating) / len(books_with_rating) if books_with_rating else 0
            
            print(f"Всего книг: {total_books}")
            print(f"Litres: {litres_count}")
            print(f"Читай-город: {chitai_count}")
            print(f"Средняя цена: {format_price(avg_price)}")
            print(f"Средний рейтинг: {avg_rating:.2f}")
          
            
        else:
            print("\nНе удалось получить данные ни с одного магазина")

    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
    
    return templates.TemplateResponse("search.html", {
        "request": request,
    })