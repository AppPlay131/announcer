import discord
from discord.ext import tasks
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
API_URL = os.getenv("BLOG_API_URL")
BLOG_URL = "https://app.realmnodes.space/blog" 
CHECK_INTERVAL_MINUTES = 5 
LAST_POST_ID_FILE = 'data/last_post_id.txt'

bot = discord.Bot()

def read_last_post_id():
    try:
        with open(LAST_POST_ID_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_last_post_id(post_id):
    os.makedirs(os.path.dirname(LAST_POST_ID_FILE), exist_ok=True)
    with open(LAST_POST_ID_FILE, 'w') as f:
        f.write(str(post_id))

@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def check_for_new_post():
    print("\n--- Новая проверка ---")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        posts = response.json()

        if not posts:
            print("API не вернул постов.")
            return

        latest_post = posts[0]
        new_post_id = latest_post['id']
        last_post_id = read_last_post_id()

        print(f"С сайта получен ID последнего поста: {new_post_id}")
        print(f"Из файла прочитан ID: {last_post_id}")

        if new_post_id != last_post_id:
            print(f"ID отличаются. Обнаружен новый пост: {new_post_id}")

            if last_post_id is None:
                print("Первый запуск. Просто запоминаю последний пост, чтобы не спамить.")
                write_last_post_id(new_post_id)
                return

            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                soup = BeautifulSoup(latest_post['content'], 'lxml')
                preview_text = soup.get_text().strip()
                
                if len(preview_text) > 250:
                    preview_text = preview_text[:250] + "..."

                embed = discord.Embed(
                    title=f"📰 {latest_post['title']}",
                    description=preview_text,
                    url=f"{BLOG_URL}#{new_post_id}",
                    color=discord.Color.purple()
                )
                embed.set_author(name="AppPlay опубликовал новый пост!")
                embed.add_field(name="", value=f"[**Читать далее →**]({BLOG_URL}#{new_post_id})")
                embed.set_footer(text=f"Дата публикации: {latest_post['date']}")

                await channel.send(embed=embed)
                
                write_last_post_id(new_post_id)
                print("Анонс успешно отправлен.")
            else:
                print(f"Ошибка: Не удалось найти канал с ID {CHANNEL_ID}")
        else:
            print("ID совпадают. Новых постов нет.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен и готов к работе!")
    check_for_new_post.start()

@check_for_new_post.before_loop
async def before_check():
    await bot.wait_until_ready()

bot.run(TOKEN)
